package chat.oldy;
import android.content.Context;import android.graphics.*;import android.graphics.drawable.*;import android.os.Build;import android.view.View;import android.widget.ImageView;import java.nio.ByteBuffer;

/** Animated WebP is decoded locally; playback stops when detached or reduced motion is enabled. */
final class StickerImageView extends ImageView {
 StickerImageView(Context c){super(c);setScaleType(ScaleType.FIT_CENTER);}
 @androidx.annotation.WorkerThread
 static Drawable decode(android.content.res.Resources resources,byte[] value)throws Exception{
  if(android.os.Looper.myLooper()==android.os.Looper.getMainLooper())throw new IllegalStateException("Decode stickers on a worker thread");
  if(value==null||value.length<16||value.length>AnimatedStickerCodec.LIMIT)throw new IllegalArgumentException();
  if(Build.VERSION.SDK_INT>=28)return ImageDecoder.decodeDrawable(ImageDecoder.createSource(ByteBuffer.wrap(value)),(d,i,source)->{if(i.getSize().getWidth()>512||i.getSize().getHeight()>512)throw new IllegalArgumentException();});
  BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;BitmapFactory.decodeByteArray(value,0,value.length,bounds);
  if(bounds.outWidth<1||bounds.outHeight<1||bounds.outWidth>512||bounds.outHeight>512)throw new IllegalArgumentException();
  Bitmap bitmap=BitmapFactory.decodeByteArray(value,0,value.length);if(bitmap==null)throw new IllegalArgumentException();return new BitmapDrawable(resources,bitmap);
 }
 @androidx.annotation.UiThread
 void decoded(Drawable value){Drawable old=getDrawable();if(old instanceof Animatable)((Animatable)old).stop();setImageDrawable(value);play();}
 void play(){Drawable d=getDrawable();if(d instanceof Animatable){boolean on=isAttachedToWindow()&&getWindowVisibility()==View.VISIBLE&&Notices.prefs(getContext()).getBoolean("animations",true);if(on)((Animatable)d).start();else ((Animatable)d).stop();}}
 protected void onAttachedToWindow(){super.onAttachedToWindow();play();}protected void onDetachedFromWindow(){Drawable d=getDrawable();if(d instanceof Animatable)((Animatable)d).stop();super.onDetachedFromWindow();}protected void onWindowVisibilityChanged(int v){super.onWindowVisibilityChanged(v);play();}
}
