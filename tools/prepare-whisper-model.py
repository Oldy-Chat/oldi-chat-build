"""Verify the upstream model before deterministic local quantization; never upload audio."""
from pathlib import Path
import hashlib,json,subprocess,urllib.request
root=Path(__file__).resolve().parents[1]
cache=root/'build/whisper-model';cache.mkdir(parents=True,exist_ok=True)
original=cache/'ggml-small.bin'
if not original.exists():
 with urllib.request.urlopen('https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin',timeout=180) as response,original.open('wb') as out:
  count=0
  while block:=response.read(262144):
   count+=len(block)
   if count>500000000:raise RuntimeError('Unexpected model size')
   out.write(block)
def digest(path,algorithm):
 h=hashlib.new(algorithm)
 with path.open('rb') as stream:
  while block:=stream.read(262144):h.update(block)
 return h.hexdigest()
if digest(original,'sha1')!='55356645c2b361a969dfd0ef2c5a50d530afd8d5':raise RuntimeError('Upstream model checksum differs')
destination=root/'app/src/main/assets/speech/whisper-small-q4.bin';destination.parent.mkdir(parents=True,exist_ok=True)
subprocess.run([str(root/'build/whisper-host/bin/quantize'),str(original),str(destination),'q4_0'],check=True)
spec={'name':'Whisper Small multilingual Q4_0','engine_revision':'a8d002cfd879315632a579e73f0148d06959de36','size':destination.stat().st_size,'sha256':digest(destination,'sha256'),'license':'MIT'}
(root/'app/src/main/assets/whisper-model.json').write_text(json.dumps(spec,indent=2))
# Vosk remains only in test fixtures for comparison; release uses the bundled Whisper model.
for old in destination.parent.glob('model-*.zip'):old.unlink()
print(json.dumps(spec))
