import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from options import command
class TenantTests(unittest.TestCase):
 def test_private_ledgers_and_path_validation(self):
  with tempfile.TemporaryDirectory() as folder:
   def call(data):
    out=io.StringIO()
    with patch.object(command,'ROOT',Path(folder)),patch('sys.stdin',io.StringIO(json.dumps(data))),patch('sys.stdout',out):command.main()
    return out.getvalue()
   a='a'*24;b='b'*24
   result=call({'command':'option_bought','tenant':a,'id':'test-fill','text':'SPY261016C00600000 1 1.50 0.65 2026-10-02T10:00:00-04:00'})
   self.assertIn('RECORDED_USER_REPORT',result)
   self.assertIn('1 contracts',call({'command':'option_positions','tenant':a}))
   self.assertIn('No SPY option',call({'command':'option_positions','tenant':b}))
   self.assertIn('No SPY option',call({'command':'option_positions'}))
   self.assertIn('Invalid private storage',call({'command':'option_positions','tenant':'../options'}))
