package chat.oldy;
import android.content.*;import android.content.pm.*;import android.net.Uri;import java.util.*;

/** A real browser Custom Tab retains Google sign-in without exposing credentials to Oldi. */
final class YouTubeBrowser {
 static final String SERVICE="android.support.customtabs.action.CustomTabsService";
 static String validBrowser(Context c,String packageName){if(packageName==null||!packageName.matches("[a-zA-Z0-9_.]{3,150}")||packageName.equals(c.getPackageName()))return "";try{List<ResolveInfo> services=c.getPackageManager().queryIntentServices(new Intent(SERVICE).setPackage(packageName),0);return services.isEmpty()?"":packageName;}catch(Exception e){return "";}}
 static String preferred(Context c){Intent view=new Intent(Intent.ACTION_VIEW,Uri.parse("https://m.youtube.com/")).addCategory(Intent.CATEGORY_BROWSABLE);ResolveInfo normal=c.getPackageManager().resolveActivity(view,PackageManager.MATCH_DEFAULT_ONLY);if(normal!=null&&normal.activityInfo!=null){String chosen=validBrowser(c,normal.activityInfo.packageName);if(!chosen.isEmpty())return chosen;}for(String name:new String[]{"com.android.chrome","com.chrome.beta","org.mozilla.firefox","com.microsoft.emmx","com.sec.android.app.sbrowser"}){String p=validBrowser(c,name);if(!p.isEmpty())return p;}for(ResolveInfo info:c.getPackageManager().queryIntentServices(new Intent(SERVICE),0)){if(info.serviceInfo!=null)return info.serviceInfo.packageName;}return "";}
 static boolean url(String raw){try{Uri u=Uri.parse(raw);String h=u.getHost();return "https".equals(u.getScheme())&&u.getUserInfo()==null&&h!=null&&(h.equals("youtube.com")||h.endsWith(".youtube.com")||h.equals("youtu.be"));}catch(Exception e){return false;}}
 static boolean account(android.app.Activity activity,String url){
  String browser=preferred(activity);if(browser.isEmpty()||!url(url))return false;
  android.content.Intent player=new Intent(activity,OldiYouTubePlayer.class).putExtra("youtube_url",url);
  android.app.PendingIntent pending=android.app.PendingIntent.getActivity(activity,735,player,android.app.PendingIntent.FLAG_UPDATE_CURRENT|android.app.PendingIntent.FLAG_MUTABLE);
  androidx.browser.customtabs.CustomTabsIntent tab=new androidx.browser.customtabs.CustomTabsIntent.Builder()
   .setDefaultColorSchemeParams(new androidx.browser.customtabs.CustomTabColorSchemeParams.Builder().setToolbarColor(0xff1b2a40).build())
   .setShowTitle(true).addMenuItem(I18n.t("Смотреть в плеере Oldi"),pending).build();
  tab.intent.setPackage(browser);
  try{tab.launchUrl(activity,Uri.parse(url));return true;}catch(android.content.ActivityNotFoundException e){return false;}
 }
 static void open(Context c,String url){if(!url(url))url="https://m.youtube.com/";c.startActivity(new Intent(c,YouTubeHubActivity.class).putExtra("url",url));}
}
