package chat.oldy;
import android.content.*;import android.os.Build;

/** Restarts message delivery after first unlock/boot and after an in-place APK update. */
public final class BootConnection extends BroadcastReceiver {
 public void onReceive(Context c,Intent event){String action=event.getAction();if(!Intent.ACTION_BOOT_COMPLETED.equals(action)&&!Intent.ACTION_MY_PACKAGE_REPLACED.equals(action))return;final PendingResult result=goAsync();new Thread(()->{try{Vault account=ChatService.vault(c);if(!account.token().isEmpty()){Intent service=new Intent(c,ChatService.class);if(Build.VERSION.SDK_INT>=26)c.startForegroundService(service);else c.startService(service);PersonalReminders.restore(c);}}catch(Exception unavailable){/* Android may require unlocking the device or enabling manufacturer autostart. */}finally{result.finish();}},"oldi-boot").start();}
}
