import hashlib, sqlite3, threading, time, unittest, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import account_features as features
class Problem(Exception):
 def __init__(self,status,code):self.status=status
class AccountFeaturesTest(unittest.TestCase):
 def setUp(self):
  db=sqlite3.connect(':memory:');db.execute('CREATE TABLE sessions(hash TEXT PRIMARY KEY,nick TEXT,expires INTEGER)')
  for token,nick in [('a','alice'),('b','alice'),('c','bobby')]:db.execute('INSERT INTO sessions VALUES(?,?,?)',(token,nick,int(time.time())+3600))
  features.init(db);self.s=SimpleNamespace(DB=db,LOCK=threading.RLock(),Problem=Problem)
 def tearDown(self):self.s.DB.close()
 def test_additive_init_and_owned_revocation_preserve_other_accounts(self):
  features.init(self.s.DB);self.assertEqual(self.s.DB.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],3)
  result=features.api(self.s,'/sessions',True,{'device':'Phone','platform':'Android'},'alice','a')['items']
  self.assertEqual(len(result),2);self.assertEqual(sum(x['current'] for x in result),1);self.assertTrue(all('session_hash' not in x for x in result))
  other=features.api(self.s,'/sessions',True,{},'bobby','c')['items'][0]
  with self.assertRaises(Problem) as error:features.api(self.s,'/sessions/revoke',True,{'id':other['id']},'alice','a')
  self.assertEqual(error.exception.status,404)
  secondary=next(x for x in result if not x['current']);features.api(self.s,'/sessions/revoke',True,{'id':secondary['id']},'alice','a')
  self.assertEqual(self.s.DB.execute('SELECT hash FROM sessions ORDER BY hash').fetchall(),[('a',),('c',)])
 def test_status_expiration_and_account_isolation(self):
  features.api(self.s,'/profile/status',True,{'status':'driving','hours':4},'alice','a')
  self.assertEqual(features.public_status(self.s,'alice')['status'],'driving');self.assertEqual(features.public_status(self.s,'bobby')['status'],'')
  self.s.DB.execute('UPDATE temporary_status SET until_time=0');self.assertEqual(features.public_status(self.s,'alice')['status'],'')
  with self.assertRaises(Problem):features.api(self.s,'/profile/status',True,{'status':'driving','hours':True},'alice','a')
