package chat.oldy;
import android.app.*;import android.content.*;import android.graphics.*;import android.os.*;import android.webkit.*;import org.json.*;import java.io.*;import java.net.*;import java.util.concurrent.*;

/** Dedicated disposable emulator: direct TCP/UDP 443 blocked by CI.
 * Authenticated SSH carries the unchanged pinned media connection to a loopback
 * copy of the production handler on Aeza. No existing chat account is accessed. */
public class MediaRouteInstrumentation extends Release066Instrumentation {
 String credential;
 public void onCreate(Bundle args){credential=args.getString("token","");start();}
 String js(WebView web,String expression)throws Exception{CountDownLatch done=new CountDownLatch(1);String[] value={""};runOnMainSync(()->web.evaluateJavascript(expression,r->{value[0]=r;done.countDown();}));check(done.await(8,TimeUnit.SECONDS),"WebView script timed out");return value[0];}
 void awaitSticker(StickerEditorActivity editor)throws Exception{long until=SystemClock.elapsedRealtime()+270000;while(SystemClock.elapsedRealtime()<until){if(editor.animation!=null)return;if(!editor.busy){String[] message={""};runOnMainSync(()->message[0]=editor.status.getText().toString());throw new AssertionError("Sticker editor stopped: "+message[0]);}Thread.sleep(250);}throw new AssertionError("Sticker generation deadline");}
 public void onStart(){Bundle result=new Bundle();YouTubeHubActivity hub=null;try{
  Context c=getTargetContext();I18n.init(c);new Api(c).configure("https://127.0.0.1:9",new String(new char[64]).replace('\0','0'));
  Vault vault=ChatService.vault(c);JSONObject identity=vault.identity();vault.account(new JSONObject().put("token",credential).put("user",new JSONObject().put("nick","alice").put("name","CI Alice").put("enc",identity.getString("enc")).put("sig",identity.getString("sig")).put("accepted_policy","fixture")));
  // Negative control proves a successful WebView cannot be using direct YouTube.
  boolean directBlocked=false;try(Socket direct=new Socket()){direct.connect(new InetSocketAddress("142.250.184.206",443),2500);}catch(IOException expected){directBlocked=true;}check(directBlocked,"Direct YouTube TLS was not blocked");mark("direct-443-blocked");
  String youtubeFailure="";boolean videoPlayed=false;long until;
  try{
  hub=(YouTubeHubActivity)launch(new Intent(c,YouTubeHubActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),YouTubeHubActivity.class);
  until=SystemClock.elapsedRealtime()+70000;while(!TunnelStateRepository.on()&&SystemClock.elapsedRealtime()<until)Thread.sleep(150);
  check(TunnelStateRepository.on(),"Aeza preflight failed: "+TunnelStateRepository.lastError(c));mark("aeza-connect-and-youtube-tls-verified");
  YouTubeHubActivity view=hub;String page="";until=SystemClock.elapsedRealtime()+65000;
  // The tunnel runs in a separate process and publishes counters every 1.5 seconds.
  // A page title can arrive before that snapshot; await both independent evidence sources.
  while(SystemClock.elapsedRealtime()<until){page=js(view.web,"JSON.stringify({url:location.href,title:document.title,body:document.body?document.body.innerText.slice(0,1000):''})");TunnelStateRepository.refresh();if(page.contains("YouTube")&&!page.contains("ERR_")&&TunnelStateRepository.webConnections>0&&TunnelStateRepository.webRx>10000)break;Thread.sleep(500);}
  TunnelStateRepository.refresh();shot("067-youtube-through-aeza");mark("youtube-route-counters: connections="+TunnelStateRepository.webConnections+", received="+TunnelStateRepository.webRx+", rejected="+TunnelStateRepository.webRejected+", error="+TunnelStateRepository.webError);
  check(page.contains("YouTube")&&!page.contains("ERR_"),"YouTube page failed: "+page);check(TunnelStateRepository.webConnections>0&&TunnelStateRepository.webRx>10000,"WebView did not receive bytes through Aeza: "+page);check(!view.browserActive,"Viewing opened external Chrome");mark("webview-youtube-page-through-aeza");
  // Load a public video through the same web route, then inspect actual playback state.
  runOnMainSync(()->view.navigate("https://m.youtube.com/watch?v=jNQXAC9IVRw"));Thread.sleep(12000);
  // A real touch must hit the player; fixed screen coordinates can hit YouTube's header.
  String playback="";long playbackDeadline=SystemClock.elapsedRealtime()+90000;
  while(SystemClock.elapsedRealtime()<playbackDeadline){
   js(view.web,"(()=>{let b=[...document.querySelectorAll('button')].find(x=>/Reject all|Отклонить все/.test(x.innerText));if(b)b.click();return true})()");
   playback=js(view.web,"JSON.stringify([...document.querySelectorAll('video')].map(v=>({time:v.currentTime,ready:v.readyState,paused:v.paused,error:v.error?v.error.code:0})))");
   Object snapshot=new JSONTokener(playback).nextValue();boolean playingNow=false;if(snapshot instanceof String){JSONArray videos=new JSONArray((String)snapshot);for(int n=0;n<videos.length();n++){JSONObject state=videos.getJSONObject(n);if(state.optDouble("time")>2&&state.optInt("ready")>=2&&!state.optBoolean("paused")&&state.optInt("error")==0)playingNow=true;}}
   if(playingNow)break;
   String targetPoint=js(view.web,"JSON.stringify((()=>{const candidates=[...document.querySelectorAll('.ytp-large-play-button,video')];const r=candidates.map(x=>x.getBoundingClientRect()).find(r=>r.width>20&&r.height>20);return {x:r?r.left+r.width/2:innerWidth/2,y:r?r.top+r.height/2:innerHeight*.32,width:innerWidth,height:innerHeight}})())");
   JSONObject point=new JSONObject((String)new JSONTokener(targetPoint).nextValue());int[] location=new int[2],dimensions=new int[2];runOnMainSync(()->{view.web.getLocationOnScreen(location);dimensions[0]=view.web.getWidth();dimensions[1]=view.web.getHeight();});float x=location[0]+(float)(point.optDouble("x")*dimensions[0]/point.optDouble("width",1)),y=location[1]+(float)(point.optDouble("y")*dimensions[1]/point.optDouble("height",1));long now=SystemClock.uptimeMillis();getUiAutomation().injectInputEvent(android.view.MotionEvent.obtain(now,now,0,x,y,0),true);getUiAutomation().injectInputEvent(android.view.MotionEvent.obtain(now,now+80,1,x,y,0),true);
   js(view.web,"(()=>{let v=document.querySelector('video');if(v){v.muted=true;v.play().catch(()=>{});}return true})()");Thread.sleep(3000);
  }
  mark("youtube-dom: "+js(view.web,"JSON.stringify({title:document.title,body:document.body.innerText.slice(0,1600),videos:[...document.querySelectorAll('video')].map(v=>({width:v.getBoundingClientRect().width,height:v.getBoundingClientRect().height,network:v.networkState}))})"));
  mark("playback-state: "+playback);shot("067-youtube-video");
  // Do not turn a failed player into a successful result. Keep evidence for diagnosis.
  Object raw=new JSONTokener(playback).nextValue();if(raw instanceof String){JSONArray states=new JSONArray((String)raw);for(int n=0;n<states.length();n++){JSONObject state=states.getJSONObject(n);if(state.optDouble("time")>2&&state.optInt("ready")>=2&&!state.optBoolean("paused")&&state.optInt("error")==0)videoPlayed=true;}}
  // Exercise guest controls on the real player; network transport between two phones is a separate acceptance check.
  JSONObject watch=new JSONObject().put("id",java.util.UUID.randomUUID().toString()).put("video","jNQXAC9IVRw");YouTubeTogether.Session guest=new YouTubeTogether.Session(view,vault,"bobby",watch,false);JSONObject pausedState=new JSONObject().put("action","state").put("position",2).put("playing",false).put("seq",1);runOnMainSync(()->guest.receive(pausedState));Thread.sleep(1200);String synchronizedPause=js(view.web,"JSON.stringify({time:document.querySelector('video').currentTime,paused:document.querySelector('video').paused})");JSONObject paused=new JSONObject((String)new JSONTokener(synchronizedPause).nextValue());check(paused.optBoolean("paused")&&Math.abs(paused.optDouble("time")-2)<3,"Watch-together pause/seek did not apply");JSONObject playingState=new JSONObject().put("action","state").put("position",2).put("playing",true).put("seq",2);runOnMainSync(()->guest.receive(playingState));Thread.sleep(2200);String synchronizedPlay=js(view.web,"JSON.stringify({time:document.querySelector('video').currentTime,paused:document.querySelector('video').paused})");JSONObject playing=new JSONObject((String)new JSONTokener(synchronizedPlay).nextValue());check(!playing.optBoolean("paused")&&playing.optDouble("time")>paused.optDouble("time"),"Watch-together resume did not play");mark("watch-together-guest-controls-verified-on-aeza-player");
  runOnMainSync(view::finish);
  }catch(Throwable routeError){youtubeFailure=routeError.getMessage();mark("youtube-check-failed: "+youtubeFailure);}
  YouTubeHubActivity opened=hub;if(opened!=null)runOnMainSync(opened::finish);LocalTunnelService.stop(c);Thread.sleep(2000);
  // Photo edit endpoint, Android decode, preview, account collection save and reload.
  File reference=new File(c.getFilesDir(),"route-reference.jpg");check(reference.isFile(),"Missing diagnostic reference");JSONObject attachment=MediaFiles.importFile(c,android.net.Uri.fromFile(reference),"image/jpeg","diagnostic-reference.jpg");String photoMessage=java.util.UUID.randomUUID().toString();attachment.put("id",photoMessage).put("peer","bobby").put("from","bobby").put("out",false).put("time",System.currentTimeMillis()).put("status","received");synchronized(vault){vault.data.getJSONArray("messages").put(attachment);vault.save();}
  StickerEditorActivity editor=(StickerEditorActivity)launch(new Intent(c,StickerEditorActivity.class).putExtra("source_mid",photoMessage).putExtra("source_account","alice").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),StickerEditorActivity.class);
  runOnMainSync(()->{});Thread.sleep(300);awaitSticker(editor);check(AnimatedStickerCodec.animated(editor.animation),"Photo result is not animated");shot("067-photo-sticker-ready");String id=editor.pending;
  runOnMainSync(()->editor.save(false));until=SystemClock.elapsedRealtime()+30000;while(!editor.isFinishing()&&SystemClock.elapsedRealtime()<until)Thread.sleep(150);check(editor.isFinishing(),"Photo sticker save failed");
  PersonalStickerStore store=new PersonalStickerStore(c,"alice");JSONObject saved=store.read(id);check(saved.getString("owner").equals("alice"),"Wrong sticker owner");check(MediaService.call(c,"/stickers/collection/"+id,null,credential).getString("id").equals(id),"Server collection lost sticker");mark("chat-photo-one-tap-sticker-created-saved-and-reloaded");
  StickerEditorActivity text=(StickerEditorActivity)launch(new Intent(c,StickerEditorActivity.class).putExtra("text_mode",true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),StickerEditorActivity.class);
  runOnMainSync(()->{text.description.setText("A small cheerful blue penguin with an orange scarf waving one flipper");text.generate();});awaitSticker(text);shot("067-description-sticker-ready");runOnMainSync(text::finish);mark("description-sticker-created");
  JSONObject assistant=MediaService.call(c,"/assistant/text",new JSONObject().put("text","Аня отправит макет завтра. Борис проверит текст в пятницу.").put("operation","tasks").put("language","ru"),credential);check(!assistant.optString("text").trim().isEmpty(),"Aeza selected-text generation returned no result");mark("selected-text-processed-through-aeza");
  check(youtubeFailure.isEmpty(),youtubeFailure);check(videoPlayed,"YouTube page loaded through Aeza but playback was not confirmed");
  result.putString("stream","OLDI_MEDIA_ROUTE_PASS: blocked direct 443; YouTube page and playback through Aeza; real photo and text generation; Android preview; account save and reload; selected-text AI through Aeza\n");finish(-1,result);
 }catch(Throwable error){result.putString("stream","OLDI_MEDIA_ROUTE_FAIL: "+android.util.Log.getStackTraceString(error));finish(0,result);}finally{LocalTunnelService.stop(getTargetContext());}}
}
