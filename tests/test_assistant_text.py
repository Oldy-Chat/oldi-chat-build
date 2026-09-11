import io,json,sys,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import assistant_text as assistant

class Problem(Exception):
 def __init__(self,status,code):self.status,self.code=status,code
class State:
 Problem=Problem
 def rate(self,*args):pass

class AssistantTest(unittest.TestCase):
 def test_only_explicit_bounded_fragment_is_accepted(self):
  good={'text':'Аня отправит макет завтра.','operation':'tasks','language':'ru'}
  with patch.object(assistant,'generate',return_value='Аня: отправить макет завтра.') as generate:
   self.assertIn('Аня',assistant.api(State(),'/assistant/text',True,good,'alice')['text'])
   generate.assert_called_once_with(good['text'],'tasks','ru')
   for change in ({'text':''},{'text':'x'*32001},{'text':[]},{'operation':[]},{'operation':'send'},{'language':'unknown'},{'history':['private']}):
    with self.assertRaises(Problem) as error:assistant.api(State(),'/assistant/text',True,{**good,**change},'alice')
    self.assertEqual(error.exception.status,400)
   with self.assertRaises(Problem) as error:assistant.api(State(),'/assistant/text',False,good,'alice')
   self.assertEqual(error.exception.status,405)
 def test_provider_receives_no_history_and_does_not_store_response(self):
  response=MagicMock();response.__enter__.return_value=response;response.read.return_value=json.dumps({'output':[{'type':'message','content':[{'type':'output_text','text':'Краткий ответ'}]}]}).encode()
  opener=MagicMock();opener.open.return_value=response
  with patch.dict('os.environ',{'OLDY_STICKER_OPENAI_KEY':'test-only'}),patch.object(assistant.urllib.request,'build_opener',return_value=opener):
   self.assertEqual(assistant.generate('Выбранный фрагмент','summary','ru'),'Краткий ответ')
  request=opener.open.call_args.args[0];payload=json.loads(request.data)
  self.assertEqual(request.full_url,'https://api.openai.com/v1/responses');self.assertFalse(payload['store']);self.assertEqual(payload['input'],'Выбранный фрагмент');self.assertNotIn('tools',payload)
 def test_provider_error_does_not_echo_key_or_fragment(self):
  response=urllib.error.HTTPError('https://api.openai.com/v1/responses',403,'denied',{},io.BytesIO(b'{"error":{"message":"PRIVATE-FRAGMENT", "code":"insufficient_permissions"}}'))
  with patch.dict('os.environ',{'OLDY_STICKER_OPENAI_KEY':'test-only'}),patch.object(assistant.urllib.request,'build_opener') as opener:
   opener.return_value.open.side_effect=response
   with self.assertRaises(assistant.AssistError) as error:assistant.generate('PRIVATE-FRAGMENT','summary','ru')
   self.assertEqual(str(error.exception),'PROVIDER_SCOPE')

if __name__=='__main__':unittest.main()
