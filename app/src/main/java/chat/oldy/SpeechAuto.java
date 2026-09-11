package chat.oldy;
import java.io.*;
import org.json.*;
/** Optional text is created on the sender's phone and travels inside the encrypted attachment. */
final class SpeechAuto {
 static void annotate(MainActivity a,Vault owner,File audio,JSONObject metadata){annotate(a,()->owner!=a.vault,audio,metadata);}
 static void annotate(android.content.Context a,java.util.function.BooleanSupplier accountChanged,File audio,JSONObject metadata){if(!Notices.prefs(a).getBoolean("voice_auto_text",true)||metadata.has("transcript"))return;String language=I18n.language().equals("en")?"en":"ru";SpeechModels.Progress progress=new SpeechModels.Progress(){public boolean cancelled(){return accountChanged.getAsBoolean()||Thread.currentThread().isInterrupted();}public void status(String message){}};try{if(progress.cancelled())return;File model=SpeechModels.ensure(a,language,progress);byte[] bytes=java.nio.file.Files.readAllBytes(audio.toPath());String text=SpeechNotes.recognize(model,bytes,progress);if(!progress.cancelled()&&!text.isEmpty()&&text.length()<=12000)metadata.put("transcript",text).put("transcript_language",language);}catch(Exception ignored){/* The voice message remains sendable if no intelligible text is found. */}}
}
