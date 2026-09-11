package chat.oldy;
import android.content.*;import android.widget.*;import org.json.JSONObject;

final class YouTubeSettings {
 static void show(MainActivity a){
  LinearLayout body=SettingsHome.page(a,"YouTube в Oldi","network");SettingsHome.section(a,body,"ПРОСМОТР");
  SettingsHome.row(a,body,"▶","YouTube","Поиск, рекомендации и ваш аккаунт",0xffc63748,()->YouTubeBrowser.open(a,"https://m.youtube.com/"));
  SettingsHome.row(a,body,"▷","Смотреть в плеере","Открыть видео по ссылке",0xffc63748,()->{EditText link=new EditText(a);link.setHint("https://youtu.be/…");a.dialog().setTitle(I18n.t("Ссылка на видео")).setView(link).setPositiveButton(I18n.t("Открыть"),(d,w)->{YouTubeLinkDetector.Target target=YouTubeLinkDetector.parse(link.getText().toString());if(target==null)a.error(I18n.t("Добавьте ссылку на видео YouTube"));else OldiYouTubePlayer.open(a,target,"YouTube");}).setNegativeButton(I18n.t("Отмена"),null).show();});
  a.space(body,14);a.paragraph(body,I18n.t("YouTube подключается через отдельный сервер Oldi. Аккаунт сохраняется во вкладке браузера. Переписка использует прежнее подключение."));
  TextView status=a.label("",14,a.TEXT);body.addView(status);TextView check=a.button(I18n.t("Проверить соединение"),true,()->{});body.addView(check);
  check.setOnClickListener(v->{check.setEnabled(false);status.setText(I18n.t("Проверяем соединение…"));a.work.execute(()->{String text;try{JSONObject result=MediaService.call(a,"/health",null,"");if(!result.optString("service").equals("oldi-media"))throw new Exception();text=I18n.t("Сервер доступен. Откройте видео для проверки воспроизведения.");}catch(Exception e){text=I18n.t("Подключение пока недоступно. Попробуйте позже.");}String ready=text;a.runOnUiThread(()->{status.setText(ready);check.setEnabled(true);});});});
  a.space(body,12);body.addView(a.button(I18n.t("Отключить соединение YouTube"),false,()->{LocalTunnelService.stop(a);status.setText(I18n.t("Соединение отключено"));}));
 }
 static String format(JSONObject report){return "Oldi YouTube · Aeza\nConnection: "+report.optString("local_tunnel","OFF")+"\nNetwork: "+report.optString("network")+"\nYouTube through route: "+report.optString("youtube_via_local","not checked")+"\nWeb connections: "+report.optLong("webview_connections")+"\nReceived bytes: "+report.optLong("webview_received")+"\nLast error: "+report.optString("last_error","—");}
}
