"""Additive account metadata. Existing sessions, profiles and messages stay intact."""
import re
import secrets
import time

STATUSES={'playing','driving','busy','available',''}

def init(db):
 db.executescript('''CREATE TABLE IF NOT EXISTS session_devices(
 id TEXT PRIMARY KEY,session_hash TEXT UNIQUE NOT NULL,device TEXT NOT NULL DEFAULT '',
 platform TEXT NOT NULL DEFAULT '',last_seen INTEGER NOT NULL DEFAULT 0);
 CREATE TABLE IF NOT EXISTS temporary_status(nick TEXT PRIMARY KEY,status TEXT NOT NULL,until_time INTEGER NOT NULL);''')

def public_status(s,nick):
 with s.LOCK:row=s.DB.execute('SELECT status,until_time FROM temporary_status WHERE nick=? AND until_time>?',(nick,int(time.time()))).fetchone()
 return {'status':row[0] if row else '', 'status_until':row[1] if row else 0}

def touch(s,digest):
 with s.LOCK:
  s.DB.execute('UPDATE session_devices SET last_seen=? WHERE session_hash=? AND last_seen<?',(int(time.time()),digest,int(time.time())-60))
  s.DB.commit()

def api(s,path,post,data,nick,digest):
 if path=='/profile/status' and post:
  status=data.get('status','');hours=data.get('hours',4)
  if not isinstance(status,str) or status not in STATUSES or type(hours) is not int or not 1<=hours<=24:raise s.Problem(400,'Неверный статус или срок')
  with s.LOCK:
   s.DB.execute('INSERT INTO temporary_status VALUES(?,?,?) ON CONFLICT(nick) DO UPDATE SET status=excluded.status,until_time=excluded.until_time',(nick,status,int(time.time())+hours*3600 if status else 0));s.DB.commit()
  return public_status(s,nick)
 if path=='/sessions' and post:
  device=data.get('device','');platform=data.get('platform','')
  if not isinstance(device,str) or not isinstance(platform,str) or len(device)>120 or len(platform)>60 or any(ord(c)<32 for c in device+platform):raise s.Problem(400,'Неверное устройство')
  with s.LOCK:
   rows=s.DB.execute('SELECT hash FROM sessions WHERE nick=? AND expires>?',(nick,int(time.time()))).fetchall()
   if digest not in {row[0] for row in rows}:raise s.Problem(401,'Сессия истекла')
   for row in rows:s.DB.execute('INSERT OR IGNORE INTO session_devices(id,session_hash) VALUES(?,?)',(secrets.token_hex(16),row[0]))
   s.DB.execute('UPDATE session_devices SET device=?,platform=?,last_seen=? WHERE session_hash=?',(device,platform,int(time.time()),digest))
   devices=s.DB.execute('SELECT d.id,d.session_hash,d.device,d.platform,d.last_seen FROM session_devices d JOIN sessions x ON x.hash=d.session_hash WHERE x.nick=? AND x.expires>? ORDER BY d.last_seen DESC',(nick,int(time.time()))).fetchall();s.DB.commit()
  return {'items':[{'id':r[0],'current':r[1]==digest,'device':r[2] or 'Ранее подключённое устройство','platform':r[3],'last_seen':r[4]} for r in devices]}
 if path=='/sessions/revoke' and post:
  ident=data.get('id','')
  if not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident):raise s.Problem(400,'Неверная сессия')
  with s.LOCK:
   row=s.DB.execute('SELECT x.hash FROM sessions x JOIN session_devices d ON d.session_hash=x.hash WHERE d.id=? AND x.nick=?',(ident,nick)).fetchone()
   if not row:raise s.Problem(404,'Сессия не найдена')
   s.DB.execute('DELETE FROM sessions WHERE hash=? AND nick=?',(row[0],nick));s.DB.execute('DELETE FROM session_devices WHERE id=?',(ident,));s.DB.commit()
  return {'revoked':True}
 return None
