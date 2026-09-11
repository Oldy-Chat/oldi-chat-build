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
FILES={'media_service.py','sticker_generation.py','sticker_collection.py','assistant_text.py'}

def run(*args):
 try:return subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=300)
 except subprocess.CalledProcessError:raise RuntimeError('SETUP_COMMAND_FAILED: '+Path(args[0]).name) from None
def main():
 if os.geteuid()!=0:raise RuntimeError('MEDIA_SETUP_REQUIRES_ROOT')
 addresses=subprocess.check_output(['hostname','-I'],text=True).split()
 if HOST not in addresses:raise RuntimeError('WRONG_VPS_ABORTED')
 package=json.load(sys.stdin);revision=package.get('revision','')
 if not re.fullmatch('[a-f0-9]{40}',revision) or set(package.get('files',{}))!=FILES:raise RuntimeError('INVALID_MEDIA_PACKAGE')
 for name,source in package['files'].items():compile(source,name,'exec')
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
 provider=config/'provider.env';previous_provider=provider.read_bytes() if provider.exists() else None;api_key=package.get('openai_key','').strip()
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
 previous_unit=unit.read_text() if unit.exists() else None
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
   if health.get('service')=='oldi-media' and health.get('code_sha256')==hashlib.sha256(package['files']['media_service.py'].encode()).hexdigest():break
  except Exception:time.sleep(.5)
 else:
  if previous_unit is not None:
   unit.write_text(previous_unit)
   if previous_provider is not None:provider.write_bytes(previous_provider);provider.chmod(0o600)
   run('systemctl','daemon-reload');run('systemctl','restart','oldi-media.service')
  raise RuntimeError('MEDIA_HEALTH_FAILED_PREVIOUS_RELEASE_RESTORED' if previous_unit is not None else 'MEDIA_HEALTH_FAILED')
 # Use the service virtual environment for the one bounded provider check.
 check_code="import json,os,sys,time,hashlib\nfrom pathlib import Path\nrelease,data,provider=map(Path,sys.argv[1:])\ndiagnostic=data/'service-check.json';live={}\nif diagnostic.exists():\n try:live=json.loads(diagnostic.read_text())\n except Exception:pass\nif not live:\n for line in provider.read_text().splitlines():\n  if '=' in line:\n   name,value=line.split('=',1)\n   if name.startswith('OLDY_STICKER_'):os.environ[name]=value\n sys.path.insert(0,str(release));import sticker_generation as generation\n began=time.monotonic()\n try:\n  from PIL import Image\n  import io\n  rendered=generation.render_sheet(None,'wave','An original cheerful ginger cat in a blue hoodie, waving one front paw. No text.')\n  animation=generation.animation(rendered)\n  with Image.open(io.BytesIO(animation)) as image:\n   live={'success':True,'frames':image.n_frames,'width':image.width,'height':image.height,'bytes':len(animation),'seconds':round(time.monotonic()-began,1),'sha256':hashlib.sha256(animation).hexdigest()}\n  (data/'service-check.webp').write_bytes(animation)\n  diagnostic.write_text(json.dumps(live))\n except generation.GenerationError as error:live={'success':False,'error':error.code,'seconds':round(time.monotonic()-began,1)}\n except Exception:live={'success':False,'error':'GENERATION_CHECK_FAILED'}\n diagnostic.write_text(json.dumps(live))\nprint(json.dumps(live))\n"
 checked=subprocess.run([str(env/'bin/python'),'-c',check_code,str(release),str(data),str(provider)],check=True,capture_output=True,text=True,timeout=240)
 live=json.loads(checked.stdout.strip().splitlines()[-1])
 print(json.dumps({'service':'oldi-media','revision':revision,'certificate_sha256':hashlib.sha256(der).hexdigest(),'health':health,'provider_key_supplied':bool(api_key),'live_generation':live,'old_chat_changed':False}))

if __name__=='__main__':
 try:main()
 except Exception as error:
  # No provider secret or input package is included in error output.
  print('MEDIA_DEPLOY_FAILED: '+(str(error) if isinstance(error,RuntimeError) else type(error).__name__))
  sys.exit(1)
