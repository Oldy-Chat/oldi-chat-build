"""Run on the NEW VPS only, with a JSON package on stdin over pinned SSH.
Creates an independent service; no chat files, chat database or existing services are changed.
"""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HOST='2.56.174.123'
FILES={'media_service.py','sticker_generation.py','sticker_collection.py'}

def run(*args):return subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=300)
def main():
 if os.geteuid()!=0:raise RuntimeError('MEDIA_SETUP_REQUIRES_ROOT')
 addresses=subprocess.check_output(['hostname','-I'],text=True).split()
 if HOST not in addresses:raise RuntimeError('WRONG_VPS_ABORTED')
 package=json.load(sys.stdin);revision=package.get('revision','')
 if not re.fullmatch('[a-f0-9]{40}',revision) or set(package.get('files',{}))!=FILES:raise RuntimeError('INVALID_MEDIA_PACKAGE')
 root=Path('/opt/oldi-media');release=root/'releases'/revision;config=Path('/etc/oldi-media');data=Path('/var/lib/oldi-media')
 for path in (root,release,config,data):path.mkdir(parents=True,exist_ok=True)
 config.chmod(0o700)
 for name,text in package['files'].items():
  target=release/name
  if target.exists() and target.read_text()!=text:raise RuntimeError('EXISTING_RELEASE_DIFFERS')
  if not target.exists():target.write_text(text)
 run('apt-get','update','-qq');run('apt-get','install','-y','python3-venv','openssl')
 if subprocess.run(['id','oldi-media'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  run('useradd','--system','--home-dir','/var/lib/oldi-media','--shell','/usr/sbin/nologin','oldi-media')
 env=root/'venv'
 if not (env/'bin/python').exists():run('python3','-m','venv',str(env))
 run(str(env/'bin/python'),'-m','pip','install','Pillow>=11,<13','cryptography>=44,<47')
 key=config/'tls.key';cert=config/'tls.crt'
 if key.exists()!=cert.exists():raise RuntimeError('INCOMPLETE_TLS_PAIR_RESTORE_EXISTING_FILES')
 if not key.exists():
  run('openssl','req','-x509','-newkey','rsa:3072','-nodes','-days','3650','-keyout',str(key),'-out',str(cert),'-subj','/CN='+HOST,'-addext','subjectAltName=IP:'+HOST)
  key.chmod(0o600)
 provider=config/'provider.env';api_key=package.get('openai_key','').strip()
 if api_key:
  if any(c in api_key for c in '\r\n\x00') or len(api_key)>1024:raise RuntimeError('INVALID_PROVIDER_KEY')
  # Secret stays outside code, command arguments and logs.
  temporary=config/'provider.env.next'
  with temporary.open('w') as out:os.chmod(temporary,0o600);out.write('OLDY_STICKER_OPENAI_KEY='+api_key+'\nOLDY_STICKER_USERS=*\nOLDY_STICKER_MODEL=gpt-image-1-mini\n')
  temporary.replace(provider)
 elif not provider.exists():
  provider.write_text('OLDY_STICKER_USERS=*\nOLDY_STICKER_MODEL=gpt-image-1-mini\n');provider.chmod(0o600)
 run('chown','-R','oldi-media:oldi-media',str(data));run('chown','oldi-media:oldi-media',str(config),str(key),str(cert))
 unit=Path('/etc/systemd/system/oldi-media.service')
 content='''[Unit]
Description=Oldi separate YouTube and sticker service
After=network-online.target
Wants=network-online.target
[Service]
User=oldi-media
Group=oldi-media
EnvironmentFile=/etc/oldi-media/provider.env
Environment=PYTHONDONTWRITEBYTECODE=1
WorkingDirectory='''+str(release)+'''
ExecStart=/opt/oldi-media/venv/bin/python '''+str(release/'media_service.py')+''' --cert /etc/oldi-media/tls.crt --key /etc/oldi-media/tls.key
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/oldi-media
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
[Install]
WantedBy=multi-user.target
'''
 if unit.exists() and 'Oldi separate YouTube and sticker service' not in unit.read_text():raise RuntimeError('UNRELATED_SERVICE_EXISTS')
 unit.write_text(content);run('systemctl','daemon-reload');run('systemctl','enable','oldi-media.service');run('systemctl','restart','oldi-media.service')
 # Only the new media port is added if UFW is already active; existing rules remain.
 if subprocess.run(['sh','-c','command -v ufw'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
  status=subprocess.check_output(['ufw','status'],text=True)
  if 'Status: active' in status:run('ufw','allow','9443/tcp')
 der=subprocess.check_output(['openssl','x509','-in',str(cert),'-outform','DER'])
 for _ in range(20):
  try:
   import ssl,urllib.request
   context=ssl.create_default_context(cafile=str(cert))
   with urllib.request.urlopen('https://'+HOST+':9443/health',context=context,timeout=3) as response:health=json.load(response)
   if health.get('service')=='oldi-media':break
  except Exception:time.sleep(.5)
 else:raise RuntimeError('MEDIA_HEALTH_FAILED')
 print(json.dumps({'service':'oldi-media','revision':revision,'certificate_sha256':hashlib.sha256(der).hexdigest(),'health':health,'provider_key_supplied':bool(api_key),'old_chat_changed':False}))

if __name__=='__main__':
 try:main()
 except Exception as error:
  # No provider secret or input package is included in error output.
  print('MEDIA_DEPLOY_FAILED: '+(str(error) if isinstance(error,RuntimeError) else type(error).__name__))
  sys.exit(1)
