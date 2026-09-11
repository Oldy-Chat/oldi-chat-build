import base64
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
import uuid
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import media_service as media
import sticker_generation as generation
import sticker_collection as collection
from sticker_fixture import sheet

class MediaTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.state=media.state(self.temp.name)
  self.env=patch.dict(os.environ,{'OLDY_STICKER_OPENAI_KEY':'fixture-only','OLDY_STICKER_USERS':'*'});self.env.start()
  def verify(token):
   if token not in ('alice-fixture','bobby-fixture'):raise media.Problem(401,'AUTH_REQUIRED')
   return token.split('-')[0]
  self.server=media.MediaServer(('127.0.0.1',0),self.state,verify);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join();self.state.DB.close();self.env.stop();self.temp.cleanup()
 def request(self,path,body=None,token='alice-fixture'):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  try:
   c.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
   r=c.getresponse();return r.status,json.loads(r.read())
  finally:c.close()
 def generate(self,owner='alice',description='A waving orange cat'):
  id=str(uuid.uuid4());body={'id':id,'description':description,'action':'wave','consent_version':1}
  status,result=self.request('/stickers/generate',body,owner+'-fixture');self.assertEqual(status,200,result)
  until=time.monotonic()+8
  while time.monotonic()<until:
   status,result=self.request('/stickers/generation/'+id,token=owner+'-fixture')
   if result['state']!='generating':return id,result
   time.sleep(.03)
  self.fail('Generation did not finish')
 def test_text_generation_save_reload_expiry_and_account_isolation(self):
  with patch.object(generation,'render_sheet',return_value=sheet()) as provider:
   id,result=self.generate();self.assertEqual(result['state'],'ready');self.assertIsNone(provider.call_args.args[0]);self.assertEqual(provider.call_args.args[2],'A waving orange cat')
  status,item=self.request('/stickers/collection/save',{'id':id,'title':'My cat'});self.assertEqual(status,200,item)
  duplicate=self.request('/stickers/collection/save',{'id':id,'title':'My cat'});self.assertEqual(duplicate,(status,item))
  self.state.DB.execute('UPDATE sticker_jobs SET expires=0');self.state.DB.commit();generation.cleanup(self.state)
  self.assertEqual(self.request('/stickers/collection/'+id),(200,item))
  self.assertEqual(self.request('/stickers/collection',token='bobby-fixture')[1]['stickers'],[])
  self.assertEqual(self.request('/stickers/collection/'+id,token='bobby-fixture')[0],404)
  self.assertEqual(self.request('/stickers/collection/save',{'id':id},'bobby-fixture')[0],404)
  encrypted=self.state.DB.execute('SELECT payload FROM sticker_collection').fetchone()[0];self.assertNotIn(base64.b64decode(item['image']),encrypted)
  restored=media.state(self.temp.name)
  try:self.assertEqual(collection.item(restored,'alice',id),item)
  finally:restored.DB.close()
 def test_exact_generated_sticker_is_not_issued_to_another_creator(self):
  with patch.object(generation,'render_sheet',return_value=sheet()):
   id,first=self.generate();_,second=self.generate('bobby')
  self.assertEqual(first['state'],'ready');self.assertEqual(second['state'],'failed');self.assertEqual(second['error'],'STICKER_NOT_UNIQUE')
  self.assertNotIn('image',second)
 def test_input_validation_and_unauthenticated_requests(self):
  with patch.object(generation,'render_sheet') as provider:
   for changes in ({'description':''},{'description':'x'*601},{'description':'cat','image':'AAAA'},{'description':{'url':'https://example.com'}}):
    body=dict(id=str(uuid.uuid4()),action='wave',consent_version=1,**changes)
    self.assertEqual(self.request('/stickers/generate',body)[0],400)
   self.assertEqual(self.request('/stickers/collection',token='bad')[0],401);provider.assert_not_called()
  self.assertEqual(self.request('/health',token='')[1]['service'],'oldi-media')
 def test_photo_upload_arriving_in_separate_network_packets(self):
  photo=io.BytesIO()
  generation.Image.new('RGB',(512,512),(110,80,65)).save(photo,format='JPEG')
  body=json.dumps({'id':str(uuid.uuid4()),'image':base64.b64encode(photo.getvalue()).decode(),'action':'wave','consent_version':1}).encode()
  with patch.object(generation,'render_sheet',return_value=sheet()):
   with socket.create_connection(('127.0.0.1',self.server.server_port),5) as c:
    c.sendall(('POST /stickers/generate HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer alice-fixture\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body))+'\r\n\r\n').encode())
    c.sendall(body[:200]);time.sleep(.15)
    try:c.sendall(body[200:])
    except BrokenPipeError:pass
    response=http.client.HTTPResponse(c);response.begin();value=json.loads(response.read())
    self.assertEqual(response.status,200,value)
   deadline=time.monotonic()+8
   while time.monotonic()<deadline:
    with self.state.LOCK:active=self.state.DB.execute("SELECT count(*) FROM sticker_jobs WHERE state='generating'").fetchone()[0]
    if not active:break
    time.sleep(.05)
 def test_description_uses_official_generation_endpoint_without_photo_or_retry(self):
  response=json.dumps({'data':[{'b64_json':base64.b64encode(b'fixture').decode()}]}).encode()
  with patch.object(generation.urllib.request,'build_opener') as opener:
   opener.return_value.open.return_value=io.BytesIO(response)
   self.assertEqual(generation.render_sheet(None,'laugh','A fluffy dog'),b'fixture')
   request=opener.return_value.open.call_args.args[0];payload=json.loads(request.data)
   self.assertEqual(request.full_url,'https://api.openai.com/v1/images/generations');self.assertNotIn('image',payload)
   self.assertEqual(payload['background'],'transparent');self.assertEqual(payload['n'],1);self.assertIn('A fluffy dog',payload['prompt']);opener.return_value.open.assert_called_once()
 def test_proxy_rejects_unrelated_private_and_spoofed_destinations(self):
  for value in ('youtube.com.evil.test:443','youtube.com:22','127.0.0.1:443','youtube.com@127.0.0.1:443','[::1]:443','foo..youtube.com:443','example.com:443'):
   with self.assertRaises(media.Problem):media.destination(value)
  for ip in ('127.0.0.1','10.0.0.1','169.254.169.254','::1','fd00::1'):
   with patch.object(media.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,0,'',(ip,443))]):
    with self.assertRaises(media.Problem):media.addresses('www.youtube.com')
  self.assertEqual(media.destination('www.youtube.com:443'),'www.youtube.com')
 def test_authenticated_connect_relays_opaque_bytes(self):
  echo=socket.socket();echo.bind(('127.0.0.1',0));echo.listen(1);echo.settimeout(5)
  def worker():
   connection,_=echo.accept()
   with connection:connection.sendall(connection.recv(64))
  thread=threading.Thread(target=worker);thread.start()
  try:
   with patch.object(media,'addresses',return_value=[(socket.AF_INET,socket.SOCK_STREAM,0,echo.getsockname())]):
    c=socket.create_connection(('127.0.0.1',self.server.server_port),5)
    with c:
     c.sendall(b'CONNECT www.youtube.com:443 HTTP/1.1\r\nHost: www.youtube.com:443\r\nProxy-Authorization: Bearer alice-fixture\r\n\r\n')
     header=b''
     while not header.endswith(b'\r\n\r\n'):header+=c.recv(1)
     self.assertIn(b' 200 ',header);payload=b'\x16\x03\x03opaque-test-tls';c.sendall(payload);self.assertEqual(c.recv(64),payload)
  finally:thread.join(5);echo.close()
 def test_preview_url_is_fixed_and_credentials_are_not_forwarded(self):
  with patch.object(media.http.client,'HTTPSConnection') as constructor:
   response=constructor.return_value.getresponse.return_value;response.status=200;response.read.return_value=b'{"title":"A video"}'
   status,payload=self.request('/youtube/metadata/dQw4w9WgXcQ')
   self.assertEqual((status,payload),(200,{'title':'A video'}));self.assertEqual(constructor.call_args.args[0],'www.youtube.com')
   self.assertNotIn('Authorization',constructor.return_value.request.call_args.kwargs['headers'])
  self.assertEqual(self.request('/youtube/metadata/../../etc/passwd')[0],404)
 def test_account_pin_is_checked_before_transmitting_the_token(self):
  with patch.object(media.http.client,'HTTPSConnection') as constructor:
   constructor.return_value.sock.getpeercert.return_value=b'wrong-certificate'
   with self.assertRaises(media.Problem):media.AccountVerifier()('alice-token-fixture')
   constructor.return_value.request.assert_not_called()
 def test_missing_encryption_key_cannot_replace_existing_collection_key(self):
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'media.sqlite3').write_bytes(b'fixture-existing')
   with self.assertRaises(RuntimeError):media.state(folder)
   self.assertFalse(Path(folder,'storage.key').exists())

if __name__=='__main__':unittest.main()
