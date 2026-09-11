package chat.oldy;
import org.json.JSONObject;
import android.graphics.Bitmap;
import java.net.URLEncoder;

/** YouTube previews use the same separate Aeza endpoint as viewing. */
final class YouTubePreviewProvider {
 static final android.util.LruCache<String,JSONObject> cache=new android.util.LruCache<>(100);
 static JSONObject describe(YouTubeLinkDetector.Target t){JSONObject j=new JSONObject();try{j.put("url",t.url()).put("site","YouTube").put("video",t.videoId).put("playlist",t.playlistId).put("title",I18n.t(t.videoId.isEmpty()?"Плейлист YouTube":"Видео на YouTube"));}catch(Exception ignored){}return j;}
 static JSONObject metadata(android.content.Context c,String id)throws Exception{if(!YouTubeLinkDetector.video(id))return new JSONObject();JSONObject found=cache.get(id);if(found!=null)return found;JSONObject result=MediaService.call(c,"/youtube/metadata/"+id,null,ChatService.vault(c).token());cache.put(id,result);return result;}
 static Bitmap thumbnail(android.content.Context c,String id)throws Exception{if(!YouTubeLinkDetector.video(id))return null;JSONObject result=MediaService.call(c,"/youtube/thumbnail/"+id,null,ChatService.vault(c).token());byte[] image=Crypto.un64(result.getString("image"));if(image.length>350000)return null;return android.graphics.BitmapFactory.decodeByteArray(image,0,image.length);}
}
