"""Persistent creator collections on the separate media service.
A received message never grants collection ownership. Job expiry does not expire saved stickers.
"""
import base64
import hashlib
import json
import re
import secrets
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import sticker_generation as generation


def init(s):
 with s.LOCK:
  s.DB.execute('CREATE TABLE IF NOT EXISTS sticker_ownership(digest TEXT PRIMARY KEY,owner TEXT NOT NULL,job TEXT NOT NULL)')
  s.DB.execute('CREATE TABLE IF NOT EXISTS sticker_collection(id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,created INTEGER NOT NULL,payload BLOB NOT NULL)')
  s.DB.execute('CREATE INDEX IF NOT EXISTS sticker_collection_owner ON sticker_collection(owner,created)')
  s.DB.commit()
 def claim(owner,job,digest):
  previous=s.DB.execute('SELECT owner,job FROM sticker_ownership WHERE digest=?',(digest,)).fetchone()
  if previous and previous!=(owner,job):raise generation.GenerationError('STICKER_NOT_UNIQUE')
  s.DB.execute('INSERT OR IGNORE INTO sticker_ownership VALUES(?,?,?)',(digest,owner,job))
 s.claim_sticker=claim


def item(s,owner,id):
 with s.LOCK:row=s.DB.execute('SELECT title,created,payload FROM sticker_collection WHERE id=? AND owner=?',(id,owner)).fetchone()
 if not row:raise s.Problem(404,'STICKER_NOT_FOUND')
 payload=row[2];raw=AESGCM(s.CHANNEL_KEY).decrypt(payload[:12],payload[12:],('oldi-collection:'+owner+':'+id).encode())
 return dict(id=id,owner=owner,title=row[0],created_at=row[1],image=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest(),motion=True)


def api(s,path,post,data,owner):
 if path!='/stickers/collection' and not path.startswith('/stickers/collection/'):return None
 if path=='/stickers/collection' and not post:
  with s.LOCK:rows=s.DB.execute('SELECT id,title,created FROM sticker_collection WHERE owner=? ORDER BY created DESC LIMIT 300',(owner,)).fetchall()
  return {'stickers':[dict(id=r[0],title=r[1],created_at=r[2]) for r in rows]}
 if post and path in ('/stickers/collection/save','/stickers/collection/remove'):
  id=data.get('id')
 else:id=path.rsplit('/',1)[-1]
 if not isinstance(id,str) or not re.fullmatch('[a-f0-9-]{36}',id):raise s.Problem(400,'STICKER_ID_INVALID')
 if path=='/stickers/collection/save' and post:
  title=data.get('title','Мой стикер')
  if set(data)-{'id','title'} or not isinstance(title,str) or len(title)>40:raise s.Problem(400,'STICKER_TITLE_INVALID')
  with s.LOCK:
   row=s.DB.execute('SELECT owner FROM sticker_collection WHERE id=?',(id,)).fetchone()
   if row:
    if row[0]!=owner:raise s.Problem(404,'STICKER_NOT_FOUND')
    return item(s,owner,id)
   result=generation.public(s,owner,id)
   if result['state']!='ready':raise s.Problem(409,'STICKER_NOT_READY')
   if s.DB.execute('SELECT COUNT(*) FROM sticker_collection WHERE owner=?',(owner,)).fetchone()[0]>=300:raise s.Problem(409,'STICKER_COLLECTION_FULL')
   raw=base64.b64decode(result['image'],validate=True);s.claim_sticker(owner,id,hashlib.sha256(raw).hexdigest())
   nonce=secrets.token_bytes(12);payload=nonce+AESGCM(s.CHANNEL_KEY).encrypt(nonce,raw,('oldi-collection:'+owner+':'+id).encode())
   s.DB.execute('INSERT INTO sticker_collection VALUES(?,?,?,?,?)',(id,owner,title,int(time.time()*1000),payload));s.DB.commit()
  return item(s,owner,id)
 if path=='/stickers/collection/remove' and post:
  with s.LOCK:
   # Keep the ownership reservation: an exact copy cannot be issued to someone else later.
   s.DB.execute('DELETE FROM sticker_collection WHERE id=? AND owner=?',(id,owner));s.DB.commit()
  return {'ok':True}
 if not post:return item(s,owner,id)
 raise s.Problem(404,'STICKER_ENDPOINT_NOT_FOUND')
