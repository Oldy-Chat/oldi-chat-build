"""Run real WebView and sticker API tests via the new VPS; block direct YouTube.
The SSH forward reaches a private disposable fixture, never replaces live service.
"""
import base64
import json
import os
from pathlib import Path
import re
import secrets
import select
import shlex
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
HOST='2.56.174.123'
def adb(*args,check=True):return subprocess.run(['adb',*args],check=check,capture_output=True,text=True,timeout=40)
def main():
 key=os.environ.get('AEZA_SSH_PRIVATE_KEY','').strip();known=os.environ.get('AEZA_SSH_KNOWN_HOSTS','').strip();user=os.environ.get('AEZA_SSH_USER','').strip()
 if not key or len(known.split())!=3 or known.split()[:2]!=[HOST,'ssh-ed25519'] or not re.fullmatch('[a-z_][a-z0-9_-]{0,31}',user):raise RuntimeError('SSH_SETUP_REQUIRED')
 env={k:v for k,v in os.environ.items() if not k.startswith(('AEZA_','OLDY_'))}
 token=secrets.token_urlsafe(32);print('::add-mask::'+token,flush=True)
 with tempfile.TemporaryDirectory(prefix='oldi-route-ci-') as directory:
  directory=Path(directory);identity=directory/'identity';identity.write_text(key+'\n');identity.chmod(0o600)
  hosts=directory/'hosts';hosts.write_text(known+'\n');hosts.chmod(0o600)
  ask=directory/'askpass';ask.write_text('#!/bin/sh\nprintf \'%s\' "$AEZA_SSH_KEY_PASSPHRASE"\n');ask.chmod(0o700)
  agent=subprocess.run(['ssh-agent','-s'],capture_output=True,text=True,check=True,env=env)
  env.update(dict(re.findall(r'(SSH_AUTH_SOCK|SSH_AGENT_PID)=([^;\n]+);',agent.stdout)))
  ssh=None
  try:
   loaded=subprocess.run(['ssh-add',str(identity)],input=b'',capture_output=True,timeout=15,env=dict(env,DISPLAY='oldi:0',SSH_ASKPASS=str(ask),SSH_ASKPASS_REQUIRE='force',AEZA_SSH_KEY_PASSPHRASE=os.environ.get('AEZA_SSH_KEY_PASSPHRASE','')))
   if loaded.returncode:raise RuntimeError('SSH_KEY_FAILED')
   command='/opt/oldi-media/venv/bin/python -u -c '+shlex.quote((ROOT/'tools/aeza/route_fixture.py').read_text())
   ssh=subprocess.Popen(['ssh','-F','/dev/null','-T','-i',str(identity),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(hosts),'-o','GlobalKnownHostsFile=/dev/null','-o','ForwardAgent=no','-o','ExitOnForwardFailure=yes','-o','ConnectTimeout=15','-L','127.0.0.1:29443:127.0.0.1:29443',user+'@'+HOST,command],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
   payload={'token':token,'files':{name:(ROOT/'server'/(name+'.py')).read_text() for name in ('media_service','sticker_generation','sticker_collection')}}
   ssh.stdin.write(json.dumps(payload).encode()+b'\n');ssh.stdin.flush()
   if not select.select([ssh.stdout],[],[],30)[0]:raise RuntimeError('VPS_FIXTURE_TIMEOUT')
   line=ssh.stdout.readline()
   if not line:raise RuntimeError('VPS_FIXTURE_FAILED')
   report=json.loads(line)
   if not report.get('ready'):raise RuntimeError('VPS_FIXTURE_FAILED')
   (directory/'reference.jpg').write_bytes(base64.b64decode(report['reference']))
   adb('root');adb('wait-for-device')
   adb('push',str(directory/'reference.jpg'),'/sdcard/Android/data/chat.oldy/files/reference.jpg')
   adb('shell','appops','set','chat.oldy','ACTIVATE_VPN','allow')
   # DNAT only the existing pinned destination into the authenticated SSH forward.
   # Both public YouTube IPv4/IPv6 and QUIC are blocked on this disposable emulator.
   adb('shell','iptables -t nat -I OUTPUT -d 2.56.174.123 -p tcp --dport 9443 -j DNAT --to-destination 10.0.2.2:29443')
   for binary in ('iptables','ip6tables'):
    for protocol in ('tcp','udp'):adb('shell',binary+' -I OUTPUT -p '+protocol+' --dport 443 -j REJECT')
   result=subprocess.run(['adb','shell','am','instrument','-w','-e','token',token,'chat.oldy.tests/chat.oldy.MediaRouteInstrumentation'],capture_output=True,text=True,timeout=600)
   output=result.stdout.replace(token,'[masked]')
   destination=ROOT/'build/ui-report';destination.mkdir(parents=True,exist_ok=True)
   (destination/'media-route.txt').write_text(output)
   print(output,flush=True)
   if result.returncode or 'OLDI_MEDIA_ROUTE_PASS' not in output:raise RuntimeError('ANDROID_MEDIA_ROUTE_FAILED')
  finally:
   if ssh:
    if ssh.stdin: ssh.stdin.close()
    try:ssh.wait(timeout=10)
    except subprocess.TimeoutExpired:ssh.terminate()
   subprocess.run(['ssh-agent','-k'],env=env,capture_output=True,timeout=10)
if __name__=='__main__':
 try:main()
 except Exception as error:
  print('ROUTE_CHECK_FAILED: '+(str(error) if isinstance(error,RuntimeError) else type(error).__name__));sys.exit(1)
