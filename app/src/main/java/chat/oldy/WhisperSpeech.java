package chat.oldy;
import android.content.Context;import java.io.*;import java.nio.*;import java.security.*;import org.json.*;

/** Multilingual Whisper Small Q4 runs locally. The signed APK contains model and native code. */
final class WhisperSpeech {
 static volatile boolean loaded;
 static synchronized void load(){if(!loaded){System.loadLibrary("oldi_whisper");loaded=true;}}
 static native String transcribe(String model,float[] samples,String language,int threads);
 static native void abort();static native int progress();
 static void cancel(){if(loaded)abort();}
 static File model(Context c,SpeechModels.Progress progress)throws Exception{
  JSONObject spec;try(InputStream in=c.getAssets().open("whisper-model.json")){spec=new JSONObject(Api.read(in,8000));}File folder=new File(c.getNoBackupFilesDir(),"whisper");folder.mkdirs();File model=new File(folder,"small-q4.bin"),ready=new File(folder,"verified.txt");String hash=spec.getString("sha256");long expected=spec.getLong("size");if(model.length()==expected&&ready.isFile()&&new String(java.nio.file.Files.readAllBytes(ready.toPath()),java.nio.charset.StandardCharsets.UTF_8).equals(hash))return model;
  File staging=new File(folder,"small-q4.part");MessageDigest digest=MessageDigest.getInstance("SHA-256");boolean saved=false;try(InputStream in=c.getAssets().open("speech/whisper-small-q4.bin");FileOutputStream out=new FileOutputStream(staging)){byte[] block=new byte[65536];long total=0;int n;while((n=in.read(block))!=-1){if(progress.cancelled())throw new java.util.concurrent.CancellationException();total+=n;if(total>expected||total>200000000)throw new IOException("Неверный размер модели");out.write(block,0,n);digest.update(block,0,n);progress.status("Подготавливаем распознавание · "+total*100/expected+"%");}out.getFD().sync();if(total!=expected||!Crypto.hex(digest.digest()).equalsIgnoreCase(hash))throw new IOException("Проверка модели не пройдена");if(!staging.renameTo(model))throw new IOException("Не удалось сохранить модель");java.nio.file.Files.write(ready.toPath(),hash.getBytes(java.nio.charset.StandardCharsets.UTF_8));saved=true;}finally{if(!saved)staging.delete();}return model;
 }
 static String recognize(Context c,byte[] audio,String language,SpeechModels.Progress task)throws Exception{
  load();File file=model(c,task);task.status("Подготавливаем звук…");FloatBuffer pcm=FloatBuffer.allocate(SpeechDecoder.RATE*SpeechDecoder.MAX_SECONDS);
  SpeechDecoder.decode(audio,new SpeechDecoder.Consumer(){public boolean cancelled(){return task.cancelled();}public void accept(byte[] bytes,int n,double seconds){for(int i=0;i<n;i+=2)pcm.put((short)((bytes[i]&255)|(bytes[i+1]<<8))/32768f);}});
  if(task.cancelled())throw new java.util.concurrent.CancellationException();float[] samples=new float[pcm.position()];pcm.flip();pcm.get(samples);task.status("Распознаём речь на телефоне…");try{return transcribe(file.getAbsolutePath(),samples,language,Math.max(1,Math.min(4,Runtime.getRuntime().availableProcessors()-1))).trim();}finally{java.util.Arrays.fill(samples,0);java.util.Arrays.fill(pcm.array(),0);}
 }
}
