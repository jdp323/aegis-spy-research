import json,tempfile,unittest
from pathlib import Path
from ops.setup import initialize,pair,safe_status
from ops.release_guard import inspect

class PublicSetup(unittest.TestCase):
 def test_pair_uses_own_bot_private_challenge_and_encrypts(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);seen=[]
   def api(method,body):
    seen.append(method)
    return {'getMe':{'is_bot':True,'id':123,'username':'OwnResearchBot'},'getUpdates':[{'message':{'text':'unique-fixture','chat':{'type':'private','id':1001},'from':{'id':1001}}}],'getChat':{'type':'private','id':1001}}[method]
   def protect(raw,decrypt=False):return raw[6:] if decrypt else b'boxed:'+raw
   result=pair('fixture-not-a-token',api,'unique-fixture',lambda name,c:self.assertEqual(name,'OwnResearchBot'),root,root/'private',protect)
   self.assertFalse(result['sent']);self.assertNotIn('sendMessage',seen)
   self.assertEqual(json.loads((root/'config/telegram.json').read_text())['username'],'OwnResearchBot')
   self.assertTrue(safe_status(root,root/'private')['telegram_encrypted_store_present'])
   with self.assertRaises(ValueError):pair('different',api,'unique-fixture',lambda *a:None,root,root/'private',protect)
 def test_pair_refuses_group_or_other_senders(self):
  for chat,sender in [('group',1001),('private',1002)]:
   with tempfile.TemporaryDirectory() as d:
    def api(method,body):
     return {'getMe':{'is_bot':True,'id':123,'username':'OwnResearchBot'},'getUpdates':[{'message':{'text':'challenge','chat':{'type':chat,'id':1001},'from':{'id':sender}}}]}[method]
    with self.assertRaises(ValueError):pair('fixture',api,'challenge',lambda *a:None,Path(d),Path(d)/'private',lambda x,*a:x)
    self.assertFalse((Path(d)/'private/telegram.dpapi').exists())
 def test_init_preserves_existing_calendar(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'config').mkdir();(root/'config/news_calendar.example.json').write_text('{"coverage_complete":false}')
   initialize(root);p=root/'config/news_calendar.json';p.write_text('preserved');initialize(root)
   self.assertEqual(p.read_text(),'preserved')

class PublicationGuard(unittest.TestCase):
 def report(self):return b'# Changes\nVerification: isolated tests\nLimitations: external feeds\nSetup impact: none'
 def test_sensitive_content_refused_without_echo(self):
  token=(str(123456789)+':'+('X'*35)).encode()
  failures=inspect({'notes.md':token},[],False)
  self.assertEqual(failures[0]['reason'],'telegram token');self.assertNotIn(token.decode(),str(failures))
 def test_private_paths_refused(self):
  for name in ('.private/test.dpapi','monitoring/access.json','options/reported.sqlite','research/VERIFICATION_PACKET_private.md'):
   self.assertTrue(inspect({name:b'{}'},[],False))
 def test_new_report_required_and_setup_changes_documented(self):
  self.assertTrue(inspect({'app.py':b'print(1)'},['app.py']))
  entries={'config/upgrade.json':b'{}','reports/updates/new.md':self.report()}
  self.assertTrue(inspect(entries,list(entries)))
  entries['SETUP.md']=b'Setup';self.assertEqual(inspect(entries,list(entries)),[])
 def test_safe_source_and_report_allowed(self):
  entries={'app.py':b'pass','reports/updates/new.md':self.report()}
  self.assertEqual(inspect(entries,list(entries)),[])
if __name__=='__main__':unittest.main()
