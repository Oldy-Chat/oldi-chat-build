package chat.oldy;

import android.app.Dialog;
import android.text.InputType;
import android.widget.*;
import org.json.*;
import java.util.UUID;

/** Author-signed edits are separate durable messages; original envelopes stay immutable. */
final class MessageEdits {
 static boolean editable(JSONObject m){return m!=null&&(m.optString("kind").equals("text")||m.optString("kind").equals("file"))&&!m.has("mini")&&!m.has("mini_update")&&!m.has("watch")&&!m.optBoolean("custom_sticker");}
 static boolean canEdit(JSONObject m){return editable(m)&&m.optBoolean("out");}
 static JSONObject payload(JSONObject m,String text)throws Exception{
  if(!canEdit(m))throw new SecurityException("Редактировать можно только своё сообщение");
  validateText(m,text);
  return new JSONObject().put("kind","control").put("op","edit").put("mid",m.getString("id")).put("text",text)
   .put("edit_version",Math.max(System.currentTimeMillis(),m.optLong("edited_at")+1)).put("edit_id",UUID.randomUUID().toString());
 }
 static void validateText(JSONObject m,String text){
  if(Crypto.bytes(text).length>10000||m!=null&&m.optString("kind").equals("text")&&text.trim().isEmpty())throw new IllegalArgumentException("Введите текст сообщения, не больше 10 000 байт");
 }
 static void apply(Vault vault,String peer,String sender,JSONObject p,long time)throws Exception{
  if(!(p.opt("text") instanceof String)||(!(p.opt("edit_version") instanceof Long)&&!(p.opt("edit_version") instanceof Integer))||!p.optString("edit_id").matches("[a-f0-9-]{36}"))throw new SecurityException("Неверная правка");
  long version=p.optLong("edit_version");if(version<1||version>time+300000)throw new SecurityException("Неверное время правки");
  validateText(null,p.getString("text"));
  JSONArray messages=vault.data.getJSONArray("messages");
  for(int i=0;i<messages.length();i++){
   JSONObject m=messages.getJSONObject(i);if(!m.optString("id").equals(p.optString("mid")))continue;
   String author=m.optBoolean("out")?vault.nick():m.optString("from");
   if(!m.optString("peer").equals(peer)||!author.equals(sender)||!editable(m))throw new SecurityException("Изменить сообщение может только его автор");
   validateText(m,p.getString("text"));
   if(version<m.optLong("edited_at")||version==m.optLong("edited_at")&&p.optString("edit_id").compareTo(m.optString("edit_id"))<=0)return;
   if(!m.has("edit_original")){JSONObject original=new JSONObject().put("text",m.optString("text"));if(m.has("link"))original.put("link",m.get("link"));m.put("edit_original",original);}
   m.put("text",p.getString("text")).put("edited_at",version).put("edit_id",p.getString("edit_id"));m.remove("link");
   return;
  }
  // The signed control stays in the normal history and is replayed when its original arrives.
 }
 static void replay(Vault vault,JSONObject original)throws Exception{
  if(!editable(original))return;String author=original.optBoolean("out")?vault.nick():original.optString("from");
  JSONArray messages=vault.data.getJSONArray("messages");
  for(int i=0;i<messages.length();i++){
   JSONObject m=messages.getJSONObject(i),p=m.optJSONObject("control");
   if(p==null||!p.optString("op").equals("edit")||!p.optString("mid").equals(original.optString("id"))||!m.optString("peer").equals(original.optString("peer")))continue;
   String sender=m.optBoolean("out")?vault.nick():m.optString("from");if(!sender.equals(author))continue;
   try{apply(vault,m.getString("peer"),sender,p,m.getLong("time"));}catch(SecurityException|IllegalArgumentException invalid){/* An invalid old edit must not hide the original. */}
  }
 }
 static void show(MainActivity a,JSONObject message){
  if(!canEdit(message))return;
  final Vault account=a.vault;String peer=message.optString("peer"),mid=message.optString("id");
  LinearLayout body=a.col();a.pad(body,16);EditText input=a.field(body,"Текст сообщения",false);
  input.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE|InputType.TYPE_TEXT_FLAG_CAP_SENTENCES|InputType.TYPE_TEXT_FLAG_AUTO_CORRECT);
  input.setMinLines(2);input.setMaxLines(8);input.setText(message.optString("text"));input.setSelection(input.length());
  Dialog dialog=a.panel("Редактировать сообщение",body);TextView save=a.button("Сохранить",true,()->{
   String text=input.getText().toString().trim();try{validateText(message,text);}catch(Exception e){a.error(e.getMessage());return;}
   a.task(()->{
    if(a.vault!=account)throw new SecurityException("Аккаунт изменился");
    JSONObject current=account.message(mid);if(!canEdit(current)||!peer.equals(current.optString("peer")))throw new SecurityException("Сообщение уже недоступно");
    if(!current.optString("text").equals(text)){account.queuePayload(peer,payload(current,text),null);}
    a.runOnUiThread(()->{dialog.dismiss();if(a.vault==account&&peer.equals(a.chat))a.renderMessages();});
   });
  });body.addView(save);body.addView(a.button("Отмена",false,dialog::dismiss));dialog.show();if(dialog.getWindow()!=null)dialog.getWindow().setLayout(-1,-2);
 }
}
