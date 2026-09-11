package chat.oldy;
import android.content.*;import android.os.*;import org.json.*;import java.io.*;import java.util.*;

/** Independent identities; encrypted delivery, delayed history and forged-edit rejection. */
public class MessageEditsInstrumentation extends FeatureInstrumentation {
 Vault account(String folder,String nick,JSONObject identity)throws Exception{
  Vault v=new Vault(isolated(folder));if(identity!=null)v.data.put("identity",identity);
  JSONObject user=Crypto.publicPart(v.identity()).put("nick",nick).put("name",nick).put("protocol",5);
  v.account(new JSONObject().put("user",user).put("token","local-edit-test"));return v;
 }
 JSONObject user(Vault v)throws Exception{return Crypto.publicPart(v.identity()).put("nick",v.nick()).put("name",v.nick()).put("protocol",5);}
 void deliver(Vault from,Vault to,String mid)throws Exception{to.receive(from.message(mid).getJSONObject("envelopes").getJSONObject(to.nick()),user(from));}
 public void onStart(){Bundle result=new Bundle();try{
  String run="edit-"+UUID.randomUUID();Vault a=account(run+"-a","sender",null),b=account(run+"-b","receiver",null);
  a.pin(user(b));b.pin(user(a));String mid=a.queuePayload("receiver",new JSONObject().put("kind","text").put("text","До исправления").put("link",new JSONObject().put("url","https://example.test/old")),null);
  JSONObject archivedOriginal=a.archiveEnvelope(a.message(mid));deliver(a,b,mid);b.bookmark(mid);
  String edit=a.queuePayload("receiver",MessageEdits.payload(a.message(mid),"После исправления"),null);deliver(a,b,edit);
  check(a.message(mid).optString("text").equals("После исправления")&&b.message(mid).optString("text").equals("После исправления"),"Edit did not reach both sides");
  check(b.message(mid).optLong("edited_at")>0&&!b.message(mid).has("link")&&b.saved(mid),"Edit marker, stale link or bookmark incorrect");
  boolean rejected=false;try{MessageEdits.payload(b.message(mid),"Чужой текст");}catch(SecurityException expected){rejected=true;}check(rejected,"Recipient got edit permission");
  JSONObject forged=new JSONObject(a.message(edit).getJSONObject("control").toString()).put("text","Forged");rejected=false;
  try{a.receive(Crypto.encrypt("receiver","sender",Payload.wire(forged),UUID.randomUUID().toString(),System.currentTimeMillis(),b.identity(),a.identity()),user(b));}catch(SecurityException expected){rejected=true;}check(rejected,"Valid signature of a different author changed the message");
  String newer=a.queuePayload("receiver",MessageEdits.payload(a.message(mid),"Последняя версия"),null);deliver(a,b,newer);
  b.applyControl("sender","sender",a.message(edit).getJSONObject("control"),a.message(edit).getLong("time"));check(b.message(mid).getString("text").equals("Последняя версия"),"Reordered edit rolled text back");
  Vault delayed=account(run+"-delayed","receiver",b.identity());delayed.pin(user(a));deliver(a,delayed,newer);deliver(a,delayed,edit);deliver(a,delayed,mid);
  check(delayed.message(mid).optString("text").equals("Последняя версия"),"Edits arriving before original were lost");
  Vault restored=account(run+"-restored","sender",a.identity());restored.restoreSnapshot(a.archiveEnvelope(a.message(newer)));restored.restoreSnapshot(a.archiveEnvelope(a.message(edit)));restored.restoreSnapshot(archivedOriginal);
  check(restored.message(mid).optString("text").equals("Последняя версия"),"Encrypted history restore lost latest edit");
  check(new Vault(isolated(run+"-restored")).message(mid).optString("text").equals("Последняя версия"),"Edit was not persisted to account storage");
  String file=a.queuePayload("receiver",new JSONObject().put("kind","file").put("text","Подпись").put("mime","image/jpeg").put("size",42).put("sha256",String.join("",Collections.nCopies(64,"a"))),null);deliver(a,b,file);
  String caption=a.queuePayload("receiver",MessageEdits.payload(a.message(file),""),null);deliver(a,b,caption);check(b.message(file).getString("text").isEmpty()&&b.message(file).getLong("size")==42,"Caption edit replaced the attachment");
  String rid=UUID.randomUUID().toString();JSONObject room=new JSONObject().put("id",rid).put("kind","channel").put("owner","sender").put("title","Edit history").put("members",new JSONArray().put("sender").put("receiver"));a.putRoom(room);b.putRoom(room);
  String post=a.queuePayload("room:"+rid,new JSONObject().put("kind","text").put("text","Исходная публикация"),null);JSONObject published=ChannelHistory.signed(a,a.message(post));
  String postEdit=a.queuePayload("room:"+rid,MessageEdits.payload(a.message(post),"Исправленная публикация"),null);JSONObject signedEdit=ChannelHistory.signed(a,a.message(postEdit));
  check(ChannelHistory.signed(a,a.message(post)).getString("record").equals(published.getString("record")),"Editing changed immutable original channel record");
  ChannelHistory.accept(b,signedEdit,user(a),rid);ChannelHistory.accept(b,published,user(a),rid);check(b.message(post).getString("text").equals("Исправленная публикация"),"Late subscriber missed channel edit");
  String thread="thread:"+rid+":"+post;String comment=b.queuePayload(thread,new JSONObject().put("kind","text").put("text","Комментарий"),null);deliver(b,a,comment);
  String commentEdit=b.queuePayload(thread,MessageEdits.payload(b.message(comment),"Исправленный комментарий"),null);deliver(b,a,commentEdit);check(a.message(comment).getString("text").equals("Исправленный комментарий"),"Comment edit lost thread routing");
  a.deletion(new JSONObject().put("kind","post").put("mid",mid).put("room",""));a.restoreSnapshot(archivedOriginal);check(!a.has(mid),"Edited deleted message resurrected");
  result.putString("stream","OLDI_EDITS_PASS: encrypted sender/recipient delivery; forged author rejected; stable IDs and attachments; reordered controls; restore before original; channel signatures and comments; deletion preserved\n");finish(-1,result);
 }catch(Throwable e){result.putString("stream","OLDI_EDITS_FAIL: "+android.util.Log.getStackTraceString(e));finish(0,result);}}
}
