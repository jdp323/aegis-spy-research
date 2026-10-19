import os,subprocess,sys,unittest,tempfile
from pathlib import Path
from ops.supervisor import child_python,clear_previous_shutdown

class ConsoleFreeSupervisor(unittest.TestCase):
    def test_invisible_supervisor_children_keep_stdio_and_json_transport(self):
        executable=str(Path(sys.executable).with_name('pythonw.exe')) if os.name=='nt' else sys.executable
        child=child_python(executable,os.name=='nt')
        result=subprocess.run([child,'-c','import sys,json; assert sys.stdout is not None and sys.stderr is not None; print(json.dumps({"stdio":True}))'],capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'{"stdio": true}')
    def test_restart_clears_old_shutdown_without_swallowing_new_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'runtime').mkdir()
            shutdown=root/'runtime/shutdown.request';stop=root/'runtime/stop.request'
            shutdown.touch();stop.touch();clear_previous_shutdown(root)
            self.assertFalse(shutdown.exists());self.assertTrue(stop.exists())
