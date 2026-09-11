"""Ephemeral, loopback-only CI service. Never opens production accounts or databases.
Executed through authenticated SSH. Same media handler and TLS certificate as the app.
It has its own random test bearer, temporary collection, fixed lifetime and no public port.
"""
import hmac
import io
import json
import os
from pathlib import Path
import socket
import ssl
import sys
import tempfile
import threading
import types

package=json.loads(sys.stdin.readline())
if '2.56.174.123' not in __import__('subprocess').check_output(['hostname','-I'],text=True).split():raise RuntimeError('WRONG_HOST')
for name in ('sticker_generation','sticker_collection','media_service'):
 module=types.ModuleType(name);sys.modules[name]=module
 exec(compile(package['files'][name],'<ci-'+name+'>','exec'),module.__dict__)
media=sys.modules['media_service']
for line in Path('/etc/oldi-media/provider.env').read_text().splitlines():
 if '=' in line:
  key,value=line.split('=',1)
  if key.startswith('OLDY_STICKER_'):os.environ[key]=value
# Check the existing account endpoint using a deliberately invalid credential:
# only an authenticated TLS GET, never account creation or database access.
try:media.AccountVerifier()('ci-invalid-no-real-account')
except media.Problem as error:
 if error.status!=401:raise RuntimeError('ACCOUNT_ENDPOINT_UNAVAILABLE') from None
else:raise RuntimeError('INVALID_CREDENTIAL_ACCEPTED')
with tempfile.TemporaryDirectory(prefix='oldi-media-ci-') as folder:
 state=media.state(folder)
 def verify(token):
  if not hmac.compare_digest(token,package['token']):raise media.Problem(401,'AUTH_REQUIRED')
  return 'alice'
 server=media.MediaServer(('127.0.0.1',29443),state,verify)
 context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
 context.load_cert_chain('/etc/oldi-media/tls.crt','/etc/oldi-media/tls.key')
 original=server.finish_request
 def finish(sock,address):
  try:
   with context.wrap_socket(sock,server_side=True) as secure:original(secure,address)
  except (ssl.SSLError,OSError):pass
 server.finish_request=finish
 # Reuse a synthetic diagnostic cat as a reference photo. Never read a user's image.
 from PIL import Image
 with Image.open('/var/lib/oldi-media/service-check.webp') as source:
  source.seek(0);reference=Image.new('RGB',source.size,'white');reference.paste(source,mask=source.getchannel('A'))
  output=io.BytesIO();reference.save(output,format='JPEG',quality=90)
 import base64
 print(json.dumps({'ready':True,'reference':base64.b64encode(output.getvalue()).decode()}),flush=True)
 threading.Timer(900,lambda:os._exit(0)).start()
 threading.Thread(target=server.serve_forever,daemon=True).start()
 # Parent closing SSH stdin ends the fixture. No temporary service survives CI.
 sys.stdin.read();server.shutdown();server.server_close()
 state.DB.close()
