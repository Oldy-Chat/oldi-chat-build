package chat.oldy;

import android.content.Context;
import android.net.Network;
import android.net.VpnService;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.cert.*;
import javax.net.ssl.*;
import org.json.*;

/** Separate pinned Aeza endpoint. Chat credentials never go to YouTube or a proxy chosen by content. */
final class MediaService {
 static final String HOST="2.56.174.123";static final int PORT=9443;
 static JSONObject config(Context c)throws Exception{try(InputStream in=c.getAssets().open("media-service.json")){return new JSONObject(Api.read(in,4096));}}
 static String pin(Context c)throws Exception{String value=config(c).optString("certificate_sha256").toLowerCase(java.util.Locale.ROOT);if(!value.matches("[a-f0-9]{64}"))throw new Api.Failure(503,"STICKER_GENERATOR_NOT_CONFIGURED");return value;}
 static boolean configured(Context c){try{pin(c);return true;}catch(Exception e){return false;}}
 static SSLSocketFactory factory(Context c)throws Exception{
  final String expected=pin(c);TrustManager[] managers={new X509TrustManager(){
   public X509Certificate[] getAcceptedIssuers(){return new X509Certificate[0];}
   public void checkClientTrusted(X509Certificate[] chain,String type)throws CertificateException{throw new CertificateException();}
   public void checkServerTrusted(X509Certificate[] chain,String type)throws CertificateException{try{if(chain.length==0)throw new CertificateException();chain[0].checkValidity();String actual=Crypto.hex(MessageDigest.getInstance("SHA-256").digest(chain[0].getEncoded())).toLowerCase(java.util.Locale.ROOT);if(!MessageDigest.isEqual(expected.getBytes(StandardCharsets.US_ASCII),actual.getBytes(StandardCharsets.US_ASCII)))throw new CertificateException();}catch(Exception error){throw new CertificateException("MEDIA_CERTIFICATE",error);}}
  }};SSLContext tls=SSLContext.getInstance("TLS");tls.init(null,managers,new SecureRandom());return tls.getSocketFactory();
 }
 static JSONObject call(Context c,String path,JSONObject body,String token)throws Exception{
  if(!path.equals("/health")&&(!path.matches("/(stickers|youtube|assistant)/[A-Za-z0-9/_-]+")||token.isEmpty()))throw new IOException("MEDIA_REQUEST");
  HttpsURLConnection connection=(HttpsURLConnection)new URL("https://"+HOST+":"+PORT+path).openConnection(Proxy.NO_PROXY);
  connection.setSSLSocketFactory(factory(c));connection.setConnectTimeout(15000);connection.setReadTimeout(40000);connection.setInstanceFollowRedirects(false);
  connection.setRequestProperty("Authorization","Bearer "+token);connection.setRequestProperty("Accept","application/json");
  try{
   if(body!=null){byte[] raw=body.toString().getBytes(StandardCharsets.UTF_8);connection.setRequestMethod("POST");connection.setDoOutput(true);connection.setRequestProperty("Content-Type","application/json");connection.setFixedLengthStreamingMode(raw.length);try(OutputStream out=connection.getOutputStream()){out.write(raw);}}
   int status=connection.getResponseCode();JSONObject response=new JSONObject(Api.read(status>=400?connection.getErrorStream():connection.getInputStream(),2000000));if(status!=200)throw new Api.Failure(status,response.optString("error","MEDIA_UNAVAILABLE"));return response;
  }finally{connection.disconnect();}
 }
 static final class Pipe implements Closeable {
  final Socket socket;Pipe(Socket socket){this.socket=socket;}
  InputStream getInputStream()throws IOException{return socket.getInputStream();}
  OutputStream getOutputStream()throws IOException{return socket.getOutputStream();}
  public void close()throws IOException{socket.close();}
 }
 static Pipe connect(LocalTunnelService service,Network network,String host)throws Exception{
  if(!YouTubeDomainRules.allowed(host))throw new IOException("DOMAIN_DENIED");
  Socket transport=new Socket();SSLSocket tls=null;
  try{
   // Allocate the OS file descriptor before protect(); an unbound Java Socket has none.
   transport.bind(new InetSocketAddress(0));
   if(!service.protect(transport))throw new IOException("PROTECT_FAILED");network.bindSocket(transport);
   transport.connect(new InetSocketAddress(HOST,PORT),10000);
   tls=(SSLSocket)factory(service).createSocket(transport,HOST,PORT,true);tls.setSoTimeout(15000);tls.startHandshake();
   // The service is pinned before account authentication is transmitted.
   String token=service.credential;if(token.isEmpty()||token.indexOf('\r')>=0||token.indexOf('\n')>=0)throw new IOException("ACCOUNT_REQUIRED");
   String request="CONNECT "+host+":443 HTTP/1.1\r\nHost: "+host+":443\r\nProxy-Authorization: Bearer "+token+"\r\n\r\n";
   tls.getOutputStream().write(request.getBytes(StandardCharsets.US_ASCII));tls.getOutputStream().flush();
   ByteArrayOutputStream response=new ByteArrayOutputStream();int tail=0;while(response.size()<8192){int b=tls.getInputStream().read();if(b<0)throw new EOFException();response.write(b);tail=(tail<<8)|b;if(tail==0x0d0a0d0a)break;}
   String header=response.toString("US-ASCII");
   if(tail!=0x0d0a0d0a)throw new IOException("MEDIA_PROXY_HEADER");
   if(header.startsWith("HTTP/1.1 401 "))throw new IOException("ACCOUNT_REQUIRED");
   if(header.startsWith("HTTP/1.1 429 "))throw new IOException("MEDIA_BUSY");
   if(!header.startsWith("HTTP/1.1 200 "))throw new IOException("MEDIA_PROXY_UNAVAILABLE");
   tls.setSoTimeout(120000);return new Pipe(tls);
  }catch(Exception error){if(tls!=null)tls.close();else transport.close();throw error;}
 }
 // A real HTTPS response inside CONNECT: validates account, relay, DNS and YouTube TLS.
 static void verifyRoute(LocalTunnelService service,Network network)throws Exception{
  String host="m.youtube.com";
  try(Pipe pipe=connect(service,network,host)){
   try(SSLSocket youtube=(SSLSocket)((SSLSocketFactory)SSLSocketFactory.getDefault()).createSocket(pipe.socket,host,443,true)){
    SSLParameters parameters=youtube.getSSLParameters();parameters.setEndpointIdentificationAlgorithm("HTTPS");youtube.setSSLParameters(parameters);youtube.setSoTimeout(15000);youtube.startHandshake();
    youtube.getOutputStream().write(("HEAD / HTTP/1.1\r\nHost: "+host+"\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));youtube.getOutputStream().flush();
    ByteArrayOutputStream line=new ByteArrayOutputStream();for(int n=0;n<512;n++){int b=youtube.getInputStream().read();if(b<0)throw new EOFException();if(b==10)break;line.write(b);}
    if(!line.toString("US-ASCII").matches("HTTP/1\\.[01] [23][0-9]{2} .*\\r?"))throw new IOException("YOUTUBE_RESPONSE_FAILED");
   }
  }
 }
 static String connectionError(Throwable error){
  for(Throwable e=error;e!=null;e=e.getCause())if(e instanceof SSLException)return "MEDIA_TLS_FAILED";
  if(error instanceof SocketTimeoutException)return "MEDIA_TIMEOUT";
  String code=error.getMessage();return code!=null&&code.matches("ACCOUNT_REQUIRED|MEDIA_BUSY|MEDIA_PROXY_UNAVAILABLE|MEDIA_PROXY_HEADER|YOUTUBE_RESPONSE_FAILED|PROTECT_FAILED|NO_NETWORK|MEDIA_NOT_CONFIGURED")?code:"MEDIA_CONNECTION_FAILED";
 }
}
