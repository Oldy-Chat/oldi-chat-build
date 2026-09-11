package chat.oldy;
import android.content.*;
public class CallActionReceiver extends BroadcastReceiver {public void onReceive(Context c,Intent i){ConferenceCall.Session video=ConferenceCall.current;if(video!=null&&video.id.equals(i.getStringExtra("cid")))video.end("Видеозвонок завершён",true);LiveCall.Session call=LiveCall.current;if(call!=null&&call.sid.equals(i.getStringExtra("sid")))call.end(call.accepted?I18n.t("Звонок завершён"):I18n.t("Звонок отклонён"),true);}}
