import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from ops.supervisor import publish_status
class StatusTests(unittest.TestCase):
    def test_transient_windows_lock_recovers(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'runtime').mkdir();original=Path.replace;calls=[]
            def replace(p,target):
                calls.append(1)
                if len(calls)<3:raise PermissionError('synthetic Windows sharing violation')
                return original(p,target)
            with patch.object(Path,'replace',replace):self.assertTrue(publish_status({'worker':{'state':'RUNNING'}},root,sleep=lambda _:None))
            self.assertEqual(len(calls),3);self.assertEqual(json.loads((root/'runtime/services.json').read_text())['components']['worker']['state'],'RUNNING')
    def test_persistent_lock_preserves_last_good_status_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'runtime').mkdir();target=root/'runtime/services.json';target.write_text('{"previous":true}')
            with patch.object(Path,'replace',side_effect=PermissionError('locked')) as replace:self.assertFalse(publish_status({},root,sleep=lambda _:None));self.assertEqual(replace.call_count,3)
            self.assertEqual(json.loads(target.read_text()),{'previous':True})
            self.assertTrue(publish_status({},root,sleep=lambda _:None))
