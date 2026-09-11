package chat.oldy;

import android.view.*;
import android.widget.*;
import org.json.*;
import java.util.*;

/** Account-owned views over existing messages. Filtering never moves or deletes attachments. */
final class PersonalHub {
 static LinearLayout page(MainActivity a,String title){return page(a,title,()->SettingsHome.own(a));}
 static LinearLayout page(MainActivity a,String title,Runnable back){a.base("personal");a.title(title,back);ScrollView scroll=new RefreshScrollView(a);LinearLayout b=a.col();scroll.addView(b);a.root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));SideNavigation.navigation(a,3);return b;}
 static boolean link(JSONObject m){return m.has("link")||android.util.Patterns.WEB_URL.matcher(m.optString("text")).find();}
 static String category(JSONObject m){if(m.optString("kind").equals("file"))return m.optString("mime").startsWith("image/")?"photos":"files";return link(m)?"links":"important";}
 static void open(MainActivity a,JSONObject m){a.openChat(m.optString("peer"));a.ui.postDelayed(()->a.jump(m.optString("id")),180);}
 static void browse(MainActivity a,String filter,boolean onlySaved){if(filter.equals("reminders")){PersonalReminders.show(a);return;}try{String title=filter.equals("media")?"Мои файлы и медиа":filter.equals("links")?"Сохранённые ссылки":"Избранное";LinearLayout b=page(a,title);if(onlySaved&&!filter.equals("links")){HorizontalScrollView scroll=new HorizontalScrollView(a);scroll.setHorizontalScrollBarEnabled(false);LinearLayout tabs=a.row();String[] ids={"all","links","photos","files","important","reminders"},names={"Всё","Ссылки","Фото","Файлы","Важное","Напоминания"};for(int i=0;i<ids.length;i++){String id=ids[i];tabs.addView(a.button(names[i],id.equals(filter),()->browse(a,id,true)),new LinearLayout.LayoutParams(-2,a.dp(44)));}scroll.addView(tabs);b.addView(scroll);a.space(b,12);}JSONArray messages=a.vault.copy().getJSONArray("messages");int count=0;for(int i=messages.length()-1;i>=0;i--){JSONObject m=messages.getJSONObject(i);if(m.optString("kind").equals("control")||onlySaved&&!a.vault.saved(m.optString("id")))continue;String kind=category(m);if(filter.equals("media")&&!m.optString("kind").equals("file")||!filter.equals("media")&&!filter.equals("all")&&!filter.equals(kind))continue;count++;String preview=Payload.preview(m);TextView card=a.button(preview+"\n"+PersonalReminders.format(m.optLong("time")),false,()->open(a,m));card.setGravity(Gravity.START|Gravity.CENTER_VERTICAL);card.setMaxLines(4);b.addView(card);a.space(b,8);}if(count==0)a.paragraph(b,onlySaved?"Сохраните сообщение в избранное — оно появится в подходящем разделе.":"Здесь появятся ваши фото, видео, голосовые и файлы из чатов.");}catch(Exception e){a.error(Api.message(e));}}
}
