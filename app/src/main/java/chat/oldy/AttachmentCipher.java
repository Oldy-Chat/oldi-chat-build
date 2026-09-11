package chat.oldy;

import java.io.*;
import java.nio.ByteBuffer;
import javax.crypto.Cipher;
import javax.crypto.spec.*;

/** Independent authenticated records keep both encryption and verification memory bounded. */
final class AttachmentCipher {
 static final String FORMAT="aes-gcm-records-v1";
 static final int BLOCK=32768;
 static final long MAX=400L*1024*1024;
 interface Sink {void put(byte[] plain)throws Exception;}
 static long encryptedSize(long plain)throws IOException{if(plain<1||plain>MAX)throw new IOException("Лимит файла — 400 МБ");return plain+((plain+BLOCK-1)/BLOCK)*20;}
 static byte[] crypt(int mode,byte[] key,byte[] prefix,long total,int sequence,byte[] bytes)throws Exception{
  if(key.length!=32||prefix.length!=8)throw new IOException("Неверный ключ вложения");
  byte[] iv=ByteBuffer.allocate(12).put(prefix).putInt(sequence).array();Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(mode,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,iv));cipher.updateAAD(ByteBuffer.allocate(16).putInt(0x4f4c4431).putLong(total).putInt(sequence).array());return cipher.doFinal(bytes);
 }
 static void encrypt(InputStream in,OutputStream destination,long total,byte[] key,byte[] prefix)throws Exception{
  encryptedSize(total);DataOutputStream out=new DataOutputStream(destination);long count=0;int seq=0;
  while(count<total){int n=(int)Math.min(BLOCK,total-count);byte[] plain=new byte[n];new DataInputStream(in).readFully(plain);byte[] encrypted;try{encrypted=crypt(Cipher.ENCRYPT_MODE,key,prefix,total,seq++,plain);}finally{java.util.Arrays.fill(plain,(byte)0);}out.writeInt(encrypted.length);out.write(encrypted);count+=n;}
  if(in.read()!=-1)throw new IOException("Размер файла изменился");out.flush();
 }
 static void decrypt(InputStream source,long total,byte[] key,byte[] prefix,Sink sink)throws Exception{
  encryptedSize(total);DataInputStream in=new DataInputStream(source);long count=0;int seq=0;
  while(count<total){int size=(int)Math.min(BLOCK,total-count),n=in.readInt();if(n!=size+16)throw new IOException("Неверный блок вложения");byte[] encrypted=new byte[n];in.readFully(encrypted);byte[] plain=crypt(Cipher.DECRYPT_MODE,key,prefix,total,seq++,encrypted);try{sink.put(plain);}finally{java.util.Arrays.fill(plain,(byte)0);}count+=size;}
  if(in.read()!=-1)throw new IOException("Лишние данные вложения");
 }
}
