"""Independent consented video peers for the loopback emulator fixture only."""
import asyncio,base64,http.client,json,os,ssl,threading,time,uuid
from fractions import Fraction
from aiortc import RTCPeerConnection,RTCConfiguration,RTCSessionDescription,VideoStreamTrack
from av import VideoFrame
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from call_peer import Tone,b64,un64,header,signed,OAEP

class Colour(VideoStreamTrack):
 async def recv(self):
  pts,base=await self.next_timestamp();frame=VideoFrame(160,120,'yuv420p')
  for index,plane in enumerate(frame.planes):plane.update(bytes([90+index*35])*plane.buffer_size)
  frame.pts=pts;frame.time_base=base;return frame

class ConferencePeer:
 def __init__(self,certificate,index):
  self.nick='video_'+str(index);self.address='127.0.0.'+str(index+10);self.ssl=ssl.create_default_context(cafile=str(certificate));self.ready=False;self.error='';self.token='';self.cid='';self.host='';self.roster=set();self.version=-1;self.connections={};self.frames={};self.sent_end=False;self.pending={}
  self.loop=asyncio.new_event_loop();threading.Thread(target=self.run,daemon=True).start()
 def run(self):asyncio.set_event_loop(self.loop);self.loop.create_task(self.begin());self.loop.run_forever()
 def request(self,path,body=None):
  connection=http.client.HTTPSConnection('127.0.0.1',8444,context=self.ssl,timeout=35,source_address=(self.address,0));headers={'Content-Type':'application/json','Connection':'close'}
  if self.token:headers['Authorization']='Bearer '+self.token
  try:
   connection.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body).encode(),headers=headers);response=connection.getresponse();data=json.load(response)
   if response.status!=200:raise RuntimeError(str(response.status)+' '+path)
   return data
  finally:connection.close()
 async def api(self,path,body=None):return await asyncio.to_thread(self.request,path,body)
 async def begin(self):
  try:
   self.rsa=await asyncio.to_thread(rsa.generate_private_key,public_exponent=65537,key_size=3072);self.ec=ec.generate_private_key(ec.SECP256R1());pub=lambda k:b64(k.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo));email=self.nick+'@example.test';ticket=await self.api('/signup/request',{'email':email});code=await self.api('/test-code?email='+email);reply=await self.api('/register',{'policy_version':'2026-09-10.2','nick':self.nick,'name':self.nick,'password':uuid.uuid4().hex,'email':email,'ticket':ticket['ticket'],'code':code['code'],'enc':pub(self.rsa),'sig':pub(self.ec)});self.token=reply['token'];self.ready=True
   while True:
    for envelope in (await self.api('/poll'))['messages']:
     peer=await self.api('/user/'+envelope['from']);serialization.load_der_public_key(un64(peer['sig'])).verify(un64(envelope['signature']),signed(envelope),ec.ECDSA(hashes.SHA256()));aes=self.rsa.decrypt(un64(envelope['key']),OAEP);plain=AESGCM(aes).decrypt(un64(envelope['iv']),un64(envelope['body']),header(envelope).encode()).decode();await self.api('/ack',{'from':envelope['from'],'id':envelope['id']})
     if plain.startswith('\x1eoldy2:'):await self.receive(envelope['from'],json.loads(plain[len('\x1eoldy2:'):]))
  except Exception as error:self.error=type(error).__name__+': '+str(error)
 async def signal(self,peer,op,**fields):
  user=await self.api('/user/'+peer);now=int(time.time()*1000);envelope={'v':1,'id':str(uuid.uuid4()),'from':self.nick,'to':peer,'time':now,'action':'signal'};p={'kind':'signal','op':op,'cid':self.cid,'sent_at':now,**fields};aes=os.urandom(32);iv=os.urandom(12);envelope['body']=b64(AESGCM(aes).encrypt(iv,('\x1eoldy2:'+json.dumps(p)).encode(),header(envelope).encode()));envelope['iv']=b64(iv);envelope['key']=b64(serialization.load_der_public_key(un64(user['enc'])).encrypt(aes,OAEP));envelope['signature']=b64(self.ec.sign(signed(envelope),ec.ECDSA(hashes.SHA256())));await self.api('/send',envelope)
 async def connect(self,peer):
  pc=RTCPeerConnection(RTCConfiguration(iceServers=[]));self.connections[peer]=pc;self.frames[peer]={'video':0,'audio':0};pc.addTrack(Tone());pc.addTrack(Colour())
  @pc.on('track')
  async def consume(track):
   try:
    while True:await track.recv();self.frames[peer][track.kind]+=1
   except Exception:pass
  return pc
 async def incoming(self):
  for pc in self.connections.values():await pc.close()
  self.cid=str(uuid.uuid4());self.host=self.nick;self.roster={self.nick,'alice'};self.version=1;self.connections={};self.frames={};self.pending={};self.sent_end=False
  await self.connect('alice');await self.signal('alice','vc_invite',host=self.nick,members=[self.nick,'alice'])
  return {'cid':self.cid}
 async def receive(self,peer,p):
  op=p.get('op','')
  if op=='vc_invite' and peer=='alice':self.cid=p['cid'];self.host=peer;await self.signal(peer,'vc_join');return
  if p.get('cid')!=self.cid:return
  if op=='vc_join' and self.host==self.nick and peer=='alice':await self.signal(peer,'vc_roster',members=[self.nick,'alice'],revision=self.version);return
  if op=='vc_leave' and self.host==self.nick:
   if peer in self.connections:await self.connections[peer].close()
   return
  if op=='vc_end' and peer==self.host:
   self.sent_end=True
   for pc in self.connections.values():await pc.close()
   return
  if op=='vc_roster' and peer==self.host:
   if p['revision']<=self.version:return
   self.version=p['revision'];self.roster=set(p['members'])
   for other in sorted(self.roster-{self.nick}):
    if other in self.connections:continue
    pc=await self.connect(other)
    if self.nick<other:await pc.setLocalDescription(await pc.createOffer());await self.signal(other,'vc_offer',sdp=pc.localDescription.sdp)
    elif other in self.pending:await self.receive(other,self.pending.pop(other))
   return
  if peer not in self.roster or peer not in self.connections:
   if op=='vc_offer':self.pending[peer]=p
   return
  pc=self.connections[peer]
  if op=='vc_offer':await pc.setRemoteDescription(RTCSessionDescription(p['sdp'],'offer'));await pc.setLocalDescription(await pc.createAnswer());await self.signal(peer,'vc_answer',sdp=pc.localDescription.sdp)
  elif op=='vc_answer':await pc.setRemoteDescription(RTCSessionDescription(p['sdp'],'answer'))
  # Tests gather full candidates into each SDP; no fixture-specific runtime bypass.
 def status(self):return {'nick':self.nick,'ready':self.ready,'error':self.error,'frames':self.frames,'connected':{n:p.connectionState for n,p in self.connections.items()},'ended':self.sent_end}
