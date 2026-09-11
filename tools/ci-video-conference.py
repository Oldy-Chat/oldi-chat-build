"""Local TLS chat fixture and independent media peers. No production traffic or credentials."""
from pathlib import Path
import os,subprocess,time,json,http.client,ssl
root=Path(__file__).resolve().parents[1];out=root/'build/ui-report';out.mkdir(parents=True,exist_ok=True)
env={k:v for k,v in os.environ.items() if not k.startswith(('OLDY_','AEZA_'))}
log=(out/'conference-server.txt').open('w')
server=subprocess.Popen(['python3','tests/device-server.py'],cwd=root,env=env,stdout=log,stderr=log)
try:
 pin=root/'build/device-server/pin.txt';deadline=time.monotonic()+25
 while not pin.exists():
  if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Local video fixture failed to start')
  time.sleep(.2)
 time.sleep(1)
 for permission in ('CAMERA','RECORD_AUDIO','POST_NOTIFICATIONS'):subprocess.run(['adb','shell','pm','grant','chat.oldy','android.permission.'+permission],check=True)
 result=subprocess.run(['adb','shell','am','instrument','-w','-e','pin',pin.read_text().strip(),'chat.oldy.tests/chat.oldy.VideoConferenceInstrumentation'],capture_output=True,text=True,timeout=240)
 (out/'conference.txt').write_text(result.stdout);print(result.stdout,flush=True)
 conference_ok='OLDI_CONFERENCE_PASS' in result.stdout
 def boot_polls():
  connection=http.client.HTTPSConnection('127.0.0.1',8444,context=ssl.create_default_context(cafile=str(root/'build/device-server/server.crt')),timeout=5)
  try:
   connection.request('GET','/test-boot/status');return json.load(connection.getresponse())['polls']
  finally:connection.close()
 before=boot_polls()
 subprocess.run(['adb','reboot'],check=True);subprocess.run(['adb','wait-for-device'],check=True,timeout=75)
 deadline=time.monotonic()+75
 while time.monotonic()<deadline:
  if subprocess.check_output(['adb','shell','getprop','sys.boot_completed'],text=True).strip()=='1':break
  time.sleep(1)
 else:raise RuntimeError('Emulator did not reboot')
 subprocess.run(['adb','shell','input','keyevent','82'],check=True)
 deadline=time.monotonic()+35
 while time.monotonic()<deadline:
  services=subprocess.check_output(['adb','shell','dumpsys','activity','services','chat.oldy/.ChatService'],text=True)
  if 'ServiceRecord' in services and 'isForeground=true' in services and boot_polls()>before:break
  time.sleep(1)
 else:raise RuntimeError('No authenticated message polling after boot without opening an activity')
 proof='OLDI_BOOT_PASS: foreground message service and authenticated polling resumed after real reboot without opening the app\n'
 (out/'boot.txt').write_text(proof);print(proof,flush=True)
 if not conference_ok:raise RuntimeError('Video check failed; reboot delivery was checked independently')

finally:
 server.terminate()
 try:server.wait(timeout=8)
 except subprocess.TimeoutExpired:server.kill();server.wait()
 log.close()
