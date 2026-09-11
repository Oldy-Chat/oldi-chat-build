from pathlib import Path
import hashlib,json,tarfile,shutil,os,re,subprocess,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1];build=root/'build';apk=build/'OldyChat-beta.apk'
if not apk.exists():raise SystemExit('Build the APK first')
# Never package a disposable CI-signed or unsigned APK as an existing-app update.
signer=os.environ.get('OLDI_APKSIGNER_JAR','')
command=['java','-jar',signer] if signer else ['apksigner']
try:verified=subprocess.run(command+['verify','--verbose','--print-certs',str(apk)],capture_output=True,text=True,check=True)
except (OSError,subprocess.CalledProcessError):raise SystemExit('APK signature verification failed; provide apksigner or OLDI_APKSIGNER_JAR') from None
certificate=re.search(r'Signer #1 certificate SHA-256 digest: ([a-fA-F0-9]+)',verified.stdout)
if not certificate or certificate.group(1).lower()!='c431f53f373f72eef0a013d61cfe0017255a986d22abb81f3dab4e5ce9720ec2':raise SystemExit('The APK does not use the original Oldi signing certificate')
release=build/'release';release.mkdir(exist_ok=True)
for name in ('server.py','account_features.py','install.sh','configure-mail.py','disk_storage.py','configure-disk.py','legal_service.py','legal_texts.json','configure-legal.py','retention.py','sticker_generation.py','configure-stickers.py','sticker_diagnostics.py'):shutil.copyfile(root/'server'/name,release/name)
shutil.copyfile(apk,release/'OldyChat-latest.apk')
android='{http://schemas.android.com/apk/res/android}';app=ET.parse(root/'app/src/main/AndroidManifest.xml').getroot()
manifest={'package':app.get('package','chat.oldy'),'version_code':int(app.get(android+'versionCode')),'version_name':app.get(android+'versionName'),'size':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'notes':"Oldi 0.6.7: YouTube внутри приложения через Aéza, исправлен приём фото для стикеров, новое меню, напоминания и совместные инструменты."}
(release/'release.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
with tarfile.open(build/'OldyChat-0.6.7-server.tar.gz','w:gz') as t:
 for f in sorted(release.iterdir()):t.add(f,arcname=f.name)
print(json.dumps({'archive':str(build/'OldyChat-0.6.7-server.tar.gz'),'apk_sha256':manifest['sha256']}))
