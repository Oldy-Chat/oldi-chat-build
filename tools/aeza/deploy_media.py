"""Upload only the media package to the known new VPS via strict host-key verification."""
import json
import hashlib
import hmac
import http.client
import ssl
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

HOST='2.56.174.123'
ROOT=Path(__file__).resolve().parents[2]

def main():
 key=os.environ.get('AEZA_SSH_PRIVATE_KEY','').strip();known=os.environ.get('AEZA_SSH_KNOWN_HOSTS','').strip();user=os.environ.get('AEZA_SSH_USER','').strip()
 if not key or not known or not re.fullmatch('[a-z_][a-z0-9_-]{0,31}',user):raise RuntimeError('SSH_SETUP_REQUIRED')
 if len(known.split())!=3 or known.split()[:2]!=[HOST,'ssh-ed25519']:raise RuntimeError('HOST_KEY_REQUIRED')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 package={'revision':revision,'files':{name:(ROOT/'server'/name).read_text() for name in ('media_service.py','sticker_generation.py','sticker_collection.py','assistant_text.py')},'openai_key':os.environ.get('OLDY_STICKER_OPENAI_KEY','')}
 env={k:v for k,v in os.environ.items() if not k.startswith(('AEZA_','OLDY_'))}
 with tempfile.TemporaryDirectory(prefix='oldi-media-deploy-') as folder:
  folder=Path(folder);identity=folder/'identity';identity.write_text(key+'\n');identity.chmod(0o600)
  hosts=folder/'hosts';hosts.write_text(known+'\n');hosts.chmod(0o600)
  ask=folder/'askpass';ask.write_text('#!/bin/sh\nprintf \'%s\' "$AEZA_SSH_KEY_PASSPHRASE"\n');ask.chmod(0o700)
  agent=subprocess.run(['ssh-agent','-s'],capture_output=True,text=True,env=env,check=True)
  values=dict(re.findall(r'(SSH_AUTH_SOCK|SSH_AGENT_PID)=([^;\n]+);',agent.stdout));env.update(values)
  try:
   loaded=subprocess.run(['ssh-add',str(identity)],input=b'',capture_output=True,timeout=15,env=dict(env,DISPLAY='oldi:0',SSH_ASKPASS=str(ask),SSH_ASKPASS_REQUIRE='force',AEZA_SSH_KEY_PASSPHRASE=os.environ.get('AEZA_SSH_KEY_PASSPHRASE','')))
   if loaded.returncode:raise RuntimeError('SSH_KEY_FAILED')
   command='python3 -c '+shlex.quote((ROOT/'tools/aeza/install_media.py').read_text())
   result=subprocess.run(['ssh','-F','/dev/null','-T','-i',str(identity),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(hosts),'-o','GlobalKnownHostsFile=/dev/null','-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=15',user+'@'+HOST,command],input=json.dumps(package).encode(),env=env,check=True,timeout=900,capture_output=True)
   report=json.loads(result.stdout.decode().strip().splitlines()[-1])
   # Verify the Android-facing port from the external runner, not only from the VPS.
   context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
   public=http.client.HTTPSConnection(HOST,9443,context=context,timeout=15)
   try:
    public.connect()
    if not hmac.compare_digest(hashlib.sha256(public.sock.getpeercert(binary_form=True)).hexdigest(),report['certificate_sha256']):raise RuntimeError('EXTERNAL_MEDIA_CERTIFICATE_FAILED')
    public.request('GET','/health');response=public.getresponse();health=json.loads(response.read(4096))
    if response.status!=200 or health.get('service')!='oldi-media' or health.get('code_sha256')!=hashlib.sha256(package['files']['media_service.py'].encode()).hexdigest():raise RuntimeError('EXTERNAL_MEDIA_HEALTH_FAILED')
    report['external_health_verified']=True
   finally:public.close()
   if report.get('live_generation',{}).get('success'):
    # This is the original diagnostic cat, never an account's photo or sticker.
    sample=subprocess.run(['ssh','-F','/dev/null','-T','-i',str(identity),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(hosts),'-o','GlobalKnownHostsFile=/dev/null','-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=15',user+'@'+HOST,'cat /var/lib/oldi-media/service-check.webp'],env=env,check=True,timeout=30,capture_output=True).stdout
    if len(sample)>350000 or hashlib.sha256(sample).hexdigest()!=report['live_generation']['sha256']:raise RuntimeError('DIAGNOSTIC_CHECKSUM_FAILED')
    output=ROOT/'build';output.mkdir(exist_ok=True);(output/'media-check.webp').write_bytes(sample)
   print(json.dumps(report))
  finally:subprocess.run(['ssh-agent','-k'],env=env,capture_output=True,timeout=10)

if __name__=='__main__':
 try:main()
 except subprocess.CalledProcessError as error:
  if isinstance(error.stdout,bytes):
   for line in error.stdout.decode(errors="replace").splitlines():
    if line.startswith("MEDIA_DEPLOY_FAILED:"):print(line[:200])
  print("MEDIA_REMOTE_EXIT:",error.returncode);sys.exit(1)
 except Exception as error:
  print('MEDIA_DEPLOY_FAILED: '+(str(error) if isinstance(error,RuntimeError) else type(error).__name__));sys.exit(1)
