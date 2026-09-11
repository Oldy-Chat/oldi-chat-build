"""Separate Aeza media service: authenticated YouTube CONNECT and owned stickers.
Never imports the chat server or opens its database. Account validation is GET /me only.
"""
import collections
import hashlib
import hmac
import http.client
import http.server
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import socket
import sqlite3
import ssl
import threading
import time
from types import SimpleNamespace
import sticker_generation
import sticker_collection

ROOTS=('youtube.com','youtube-nocookie.com','youtu.be','googlevideo.com','ytimg.com',
       'youtubei.googleapis.com','youtube.googleapis.com','ggpht.com','accounts.google.com',
       'accounts.google.ru','oauth2.googleapis.com','gstatic.com','googleusercontent.com')
CHAT_HOST='5.42.102.11'
CHAT_PIN='a84186ad26b22e7d69f23d1838a9db5a2b277a6d567d6e49249c7714153e5d4a'

class Problem(Exception):
 def __init__(self,status,code):self.status=status;self.code=code

def destination(authority):
 if not re.fullmatch(r'[a-zA-Z0-9.-]{1,253}:443',authority):raise Problem(403,'DESTINATION_DENIED')
 host=authority[:-4].lower()
 if '..' in host or not any(host==r or host.endswith('.'+r) for r in ROOTS):raise Problem(403,'DESTINATION_DENIED')
 return host

def addresses(host):
 result=[]
 for family,kind,proto,_,address in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
  if not ipaddress.ip_address(address[0]).is_global:raise Problem(403,'DESTINATION_DENIED')
  result.append((family,kind,proto,address))
 if not result:raise Problem(502,'YOUTUBE_UNAVAILABLE')
 return result

class AccountVerifier:
 def __init__(self):self.cache={};self.lock=threading.Lock()
 def __call__(self,token):
  if not re.fullmatch(r'[A-Za-z0-9_\-+=/.]{16,512}',token):raise Problem(401,'AUTH_REQUIRED')
  digest=hashlib.sha256(token.encode()).digest()
  with self.lock:cached=self.cache.get(digest)
  if cached and cached[1]>time.monotonic():return cached[0]
  # Explicit certificate pin is checked BEFORE transmitting the bearer credential.
  context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
  connection=http.client.HTTPSConnection(CHAT_HOST,443,timeout=8,context=context)
  try:
   connection.connect()
   if not hmac.compare_digest(hashlib.sha256(connection.sock.getpeercert(binary_form=True)).hexdigest(),CHAT_PIN):raise Problem(502,'ACCOUNT_SERVICE_UNAVAILABLE')
   connection.request('GET','/me',headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
   response=connection.getresponse()
   if response.status in (401,403):raise Problem(401,'AUTH_REQUIRED')
   if response.status!=200:raise Problem(502,'ACCOUNT_SERVICE_UNAVAILABLE')
   raw=response.read(262145)
   if len(raw)>262144:raise Problem(502,'ACCOUNT_SERVICE_UNAVAILABLE')
   nick=json.loads(raw).get('nick','')
   if not re.fullmatch('[a-z0-9_]{3,24}',nick):raise Problem(502,'ACCOUNT_SERVICE_UNAVAILABLE')
  except Problem:raise
  except Exception:raise Problem(502,'ACCOUNT_SERVICE_UNAVAILABLE') from None
  finally:connection.close()
  with self.lock:
   if len(self.cache)>=5000:self.cache={k:v for k,v in self.cache.items() if v[1]>time.monotonic()}
   if len(self.cache)<5000:self.cache[digest]=(nick,time.monotonic()+30)
  return nick

class Limits:
 def __init__(self):self.lock=threading.Lock();self.events={}
 def __call__(self,key,count,seconds):
  now=time.monotonic()
  with self.lock:
   if len(self.events)>10000:self.events={k:v for k,v in self.events.items() if v and now-v[-1]<3600}
   queue=self.events.setdefault(key,collections.deque())
   while queue and now-queue[0]>seconds:queue.popleft()
   if len(queue)>=count:raise Problem(429,'PLEASE_RETRY_LATER')
   queue.append(now)

class MediaServer(http.server.ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,address,state,verify=None):
  super().__init__(address,Handler);self.state=state;self.verify=verify or AccountVerifier()
  self.connections=threading.BoundedSemaphore(120);self.proxy_lock=threading.Lock();self.proxy_users={}
 def get_request(self):
  sock,address=super().get_request();sock.settimeout(12)
  return sock,address
 def process_request(self,request,address):
  if not self.connections.acquire(False):request.close();return
  try:super().process_request(request,address)
  except BaseException:self.connections.release();raise
 def process_request_thread(self,request,address):
  try:super().process_request_thread(request,address)
  finally:self.connections.release()
 def handle_error(self,*args):pass

class Handler(http.server.BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1';server_version='OldiMedia';rbufsize=0
 def log_message(self,*args):pass
 def json(self,status,payload):
  raw=json.dumps(payload,separators=(',',':')).encode();self.send_response(status)
  self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
  self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();self.wfile.write(raw);self.close_connection=True
 def account(self,proxy=False):
  name='Proxy-Authorization' if proxy else 'Authorization'
  header=self.headers.get(name,'')
  if not header.startswith('Bearer '):raise Problem(401,'AUTH_REQUIRED')
  return self.server.verify(header[7:])
 def do_GET(self):self.api(False)
 def do_POST(self):self.api(True)
 def api(self,post):
  try:
   if self.path=='/health' and not post:return self.json(200,{'service':'oldi-media','version':1,'youtube_proxy':True})
   owner=self.account();self.server.state.rate(('media-api',owner),180,60)
   if self.headers.get('Transfer-Encoding'):raise Problem(400,'BODY_INVALID')
   try:length=int(self.headers.get('Content-Length','0'))
   except ValueError:raise Problem(400,'BODY_INVALID')
   if length<0 or length>1600000:raise Problem(413,'BODY_TOO_LARGE')
   data={}
   if post:
    try:
     raw=self.rfile.read(length)
     if len(raw)!=length:raise ValueError()
     data=json.loads(raw)
     if not isinstance(data,dict):raise ValueError()
    except Exception:raise Problem(400,'BODY_INVALID')
   result=sticker_collection.api(self.server.state,self.path,post,data,owner)
   if result is None:result=sticker_generation.api(self.server.state,self.path,post,data,owner)
   if result is None:raise Problem(404,'NOT_FOUND')
   self.json(200,result)
  except Problem as error:self.json(error.status,{'error':error.code})
  except Exception:self.json(503,{'error':'MEDIA_UNAVAILABLE'})
 def do_CONNECT(self):
  remote=None;owner=None;acquired=False;connected=False
  try:
   host=destination(self.path);owner=self.account(True)
   if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Length','0')!='0':raise Problem(400,'BODY_INVALID')
   self.server.state.rate(('youtube-connect',owner),240,60)
   with self.server.proxy_lock:
    count=self.server.proxy_users.get(owner,0)
    if count>=32:raise Problem(429,'TOO_MANY_CONNECTIONS')
    self.server.proxy_users[owner]=count+1;acquired=True
   for family,kind,proto,address in addresses(host):
    candidate=socket.socket(family,kind,proto);candidate.settimeout(8)
    try:candidate.connect(address);remote=candidate;break
    except OSError:candidate.close()
   if remote is None:raise Problem(502,'YOUTUBE_UNAVAILABLE')
   self.send_response(200,'Connection Established');self.end_headers();self.wfile.flush();connected=True
   self.connection.settimeout(30);remote.settimeout(30);began=last=time.monotonic()
   while time.monotonic()-began<10800 and time.monotonic()-last<120:
    ready,_,_=select.select([self.connection,remote],[],[],5)
    if isinstance(self.connection,ssl.SSLSocket) and self.connection.pending() and self.connection not in ready:ready.append(self.connection)
    for source in ready:
     raw=source.recv(32768)
     if not raw:return
     (remote if source is self.connection else self.connection).sendall(raw);last=time.monotonic()
  except Problem as error:
   if not connected:self.json(error.status,{'error':error.code})
  except Exception:
   if not connected:self.json(502,{'error':'YOUTUBE_UNAVAILABLE'})
  finally:
   self.close_connection=True
   if remote:remote.close()
   if acquired:
    with self.server.proxy_lock:
     count=self.server.proxy_users.get(owner,1)-1
     if count:self.server.proxy_users[owner]=count
     else:self.server.proxy_users.pop(owner,None)

def state(directory):
 directory=Path(directory);directory.mkdir(mode=0o700,parents=True,exist_ok=True)
 key=directory/'storage.key'
 if not key.exists():
  if (directory/'media.sqlite3').exists():raise RuntimeError('Restore the existing media storage key')
  with key.open('xb') as out:os.chmod(key,0o600);out.write(os.urandom(32))
 secret=key.read_bytes()
 if len(secret)!=32:raise RuntimeError('Invalid media storage key')
 db=sqlite3.connect(directory/'media.sqlite3',check_same_thread=False);db.execute('PRAGMA journal_mode=WAL')
 s=SimpleNamespace(DB=db,LOCK=threading.RLock(),CHANNEL_KEY=secret,Problem=Problem,rate=Limits())
 sticker_generation.init(s);sticker_collection.init(s);return s

def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--host',default='0.0.0.0');parser.add_argument('--port',type=int,default=9443)
 parser.add_argument('--data',default='/var/lib/oldi-media');parser.add_argument('--cert',required=True);parser.add_argument('--key',required=True);args=parser.parse_args()
 s=state(args.data);server=MediaServer((args.host,args.port),s)
 context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(args.cert,args.key)
 # Wrap accepted sockets in each bounded worker, so slow TLS handshakes cannot block accept().
 original=server.finish_request
 def finish(sock,address):
  try:
   with context.wrap_socket(sock,server_side=True) as secure:original(secure,address)
  except (ssl.SSLError,OSError):pass
 server.finish_request=finish
 threading.Thread(target=sticker_generation.maintenance,args=(s,),daemon=True).start();server.serve_forever()

if __name__=='__main__':main()
