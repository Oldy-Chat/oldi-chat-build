package chat.oldy;
import android.app.*;import android.content.*;import android.graphics.*;import android.os.*;import android.view.*;import android.widget.*;import org.json.*;import java.io.*;

/** Local emulator fixtures only. Never registers an account or contacts production. */
public class Release066Instrumentation extends Instrumentation {
 public void onCreate(Bundle args){start();}
 volatile Activity resumed;
 public void callActivityOnResume(Activity a){super.callActivityOnResume(a);resumed=a;}
 void mark(String step){Bundle b=new Bundle();b.putString("stream","OLDI_066_STEP: "+step+"\n");sendStatus(1,b);}
 Activity launch(Intent intent,Class<?> kind)throws Exception{resumed=null;runOnMainSync(()->getTargetContext().startActivity(intent));long until=SystemClock.elapsedRealtime()+15000;while(SystemClock.elapsedRealtime()<until){Activity a=resumed;if(a!=null&&kind.isInstance(a))return a;Thread.sleep(80);}throw new AssertionError("Activity did not resume: "+kind.getSimpleName());}
 void check(boolean condition,String message){if(!condition)throw new AssertionError(message);}
 boolean contains(View view,String text){if(view instanceof TextView&&((TextView)view).getText().toString().contains(text))return true;if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)if(contains(((ViewGroup)view).getChildAt(i),text))return true;return false;}
 void shot(String name)throws Exception{mark(name);runOnMainSync(()->{});Thread.sleep(800);Bitmap image=getUiAutomation().takeScreenshot();File folder=new File(getTargetContext().getExternalFilesDir(null),"review");folder.mkdirs();try(FileOutputStream out=new FileOutputStream(new File(folder,name+".png"))){image.compress(Bitmap.CompressFormat.PNG,100,out);}image.recycle();}
 public void onStart(){Bundle result=new Bundle();try{
  mark("local-fixture");Context c=getTargetContext();I18n.init(c);new Api(c).configure("https://127.0.0.1:9",new String(new char[64]).replace('\0','0'));
  Vault vault=ChatService.vault(c);JSONObject identity=vault.identity();JSONObject user=new JSONObject().put("nick","alice").put("name","Алиса").put("enc",identity.getString("enc")).put("sig",identity.getString("sig")).put("accepted_policy","fixture");vault.account(new JSONObject().put("user",user).put("token","offline-fixture-only"));JSONObject bob=Crypto.identity().put("nick","bobby").put("name","Борис");vault.pin(bob);vault.queue("bobby","Проверяем новый чат и стикеры");
  mark("launch-main");MainActivity activity=(MainActivity)launch(new Intent(c,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),MainActivity.class);Thread.sleep(1200);
  for(String theme:new String[]{"light","dark","cyber"}){runOnMainSync(()->{Notices.prefs(c).edit().putString("theme",theme).putBoolean("animations",true).commit();activity.chats();});shot("066-main-"+theme);runOnMainSync(()->{View bar=activity.root.findViewWithTag("primary-navigation");check(bar!=null&&bar.getHeight()>=activity.dp(70),"Navigation too small");});}
  runOnMainSync(activity::profileMenu);shot("066-menu");runOnMainSync(()->{View menu=activity.activeSheet.getWindow().getDecorView();check(contains(menu,"Мои стикеры")&&contains(menu,"Создать канал")&&contains(menu,"Капсула дня"),"Main menu lost features");activity.activeSheet.dismiss();activity.openChat("bobby");EmojiTray.show(activity);});shot("066-emoji");runOnMainSync(()->{check(contains(activity.emojiPanel,"Стикеры"),"Sticker tab is not visible");check(!contains(activity.emojiPanel,"Живые"),"Old animation picker remains");EmojiTray.fill(activity,5);});shot("066-sticker-panel");runOnMainSync(()->{check(contains(activity.emojiPanel,"Создать из фото")&&contains(activity.emojiPanel,"Создать по описанию"),"Sticker creation modes missing");});
  mark("launch-editor");StickerEditorActivity editor=(StickerEditorActivity)launch(new Intent(c,StickerEditorActivity.class).putExtra("text_mode",true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),StickerEditorActivity.class);runOnMainSync(()->{editor.description.setText("Рыжий кот в синей толстовке");check(editor.textMode&&editor.description.getParent()!=null,"Description editor missing");check(!contains(editor.body,"ИИ-сервис")&&!contains(editor.body,"OpenAI"),"Technical copy in creation flow");});shot("066-description-editor");runOnMainSync(editor::finish);
  check(new Vault(c).nick().equals("alice"),"Account lost");check(new Vault(c).copy().getJSONArray("messages").length()>0,"Messages lost");
  result.putString("stream","OLDI_066_UI_PASS: three themes, larger navigation, complete menu, emoji/sticker tabs, description editor, local account persistence\n");finish(-1,result);
 }catch(Throwable error){result.putString("stream","OLDI_066_UI_FAIL: "+android.util.Log.getStackTraceString(error));finish(0,result);}}
}
