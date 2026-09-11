package chat.oldy;

import android.content.*;import android.database.Cursor;import android.net.Uri;import android.provider.OpenableColumns;import android.widget.Toast;
import org.json.*;import java.io.*;

/** Generic files use the system document picker and stream to/from account encrypted storage. */
final class FileAttachments {
 static String pendingId="",pendingAccount="";
 static void attach(MainActivity a,Uri uri,String target,String caption)throws Exception{
  String name="Файл";long size=-1;try(Cursor c=a.getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE},null,null,null)){if(c!=null&&c.moveToFirst()){int n=c.getColumnIndex(OpenableColumns.DISPLAY_NAME),s=c.getColumnIndex(OpenableColumns.SIZE);if(n>=0)name=c.getString(n);if(s>=0&&!c.isNull(s))size=c.getLong(s);}}
  if(size>AttachmentCipher.MAX)throw new IOException("Лимит файла — 400 МБ");if(size==0)throw new IOException("Пустой файл");
  if(name==null||name.trim().isEmpty())name="Файл";name=name.replaceAll("[\\r\\n/\\\\]","_");if(name.length()>120)name=name.substring(0,120);
  String mime=a.getContentResolver().getType(uri);if(mime==null||!mime.matches("[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+"))mime="application/octet-stream";
  CloudMedia.attach(a,uri,mime,name,target,caption,new JSONObject().put("document",true));
 }
 static void open(MainActivity a,JSONObject message){final Vault owner=a.vault;final String mid=message.optString("id");a.task(()->{JSONObject m=owner.message(mid);if(m==null)throw new IOException("Файл недоступен");if(!m.has("local"))CloudMedia.download(a,owner,m);a.runOnUiThread(()->{if(a.vault!=owner)return;try{JSONObject saved=owner.message(mid);pendingId=mid;pendingAccount=owner.nick();a.startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType(saved.optString("mime","application/octet-stream")).addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,saved.optString("name","Файл")),42);}catch(Exception e){a.error(Api.message(e));}});});}
 static void saveSelected(MainActivity a,Uri destination){final Vault owner=a.vault;String mid=pendingId,account=pendingAccount;pendingId="";pendingAccount="";if(!owner.nick().equals(account)||mid.isEmpty()){a.error("Выберите файл заново");return;}a.task(()->{JSONObject m=owner.message(mid);if(m==null)throw new IOException("Файл недоступен");try(InputStream in=MediaFiles.open(a,m.getString("local"));OutputStream out=a.getContentResolver().openOutputStream(destination,"w")){if(out==null)throw new IOException("Не удалось открыть папку");byte[] block=new byte[32768];int n;long count=0;while((n=in.read(block))!=-1){if(owner!=a.vault)throw new IOException("Аккаунт изменился");out.write(block,0,n);count+=n;}if(count!=m.optLong("size"))throw new IOException("Размер не совпал");}a.runOnUiThread(()->{Toast.makeText(a,"Файл сохранён",Toast.LENGTH_SHORT).show();EventExpiry.notify(a,m,"open");});});}
}
