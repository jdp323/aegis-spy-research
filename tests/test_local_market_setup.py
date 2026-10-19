"""Local configuration security boundaries, synthetic keys only."""
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from data.credentials import NAMES,save
from data.local_setup import allowed_request,parse_keys,SetupServer

class LocalSetupTests(unittest.TestCase):
    def test_http_import_requires_nonce_origin_valid_fields_and_single_use(self):
        server=SetupServer(('127.0.0.1',0))
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True)
        thread.start()
        host='127.0.0.1:'+str(server.server_port)
        path='/setup/'+server.token
        body='APCA_API_KEY_ID=synthetic-key&APCA_API_SECRET_KEY=synthetic-secret'
        def request(method,target=path,payload=None,origin='http://'+host):
            client=HTTPConnection('127.0.0.1',server.server_port,timeout=2)
            headers={'Content-Type':'application/x-www-form-urlencoded'}
            if origin is not None:headers['Origin']=origin
            client.request(method,target,body=payload,headers=headers)
            response=client.getresponse();data=response.read().decode();status=response.status;cache=response.getheader('Cache-Control')
            self.assertEqual(response.getheader('Referrer-Policy'),'same-origin')
            client.close();return status,data,cache
        try:
            with patch('data.local_setup.save') as persist,patch('data.local_setup.verify',return_value='AUTHENTICATION_REJECTED') as verify:
                status,page,cache=request('GET')
                self.assertEqual(status,200);self.assertEqual(cache,'no-store')
                self.assertEqual(page.count('type="password"'),7) # Optional encrypted Reddit/FRED inputs.
                self.assertEqual(request('POST',payload=body,origin=None)[0],403)
                self.assertEqual(request('POST',target='/setup/wrong',payload=body)[0],404)
                self.assertEqual(request('POST',payload=body+'&token=extra')[0],400)
                persist.assert_not_called()
                self.assertEqual(request('POST',payload=body)[0],400)
                persist.assert_not_called();self.assertFalse(server.used)
                verify.return_value='ACCESS_UNVERIFIED'
                self.assertEqual(request('POST',payload=body)[0],400)
                persist.assert_not_called();self.assertFalse(server.used)
                verify.return_value='AUTHENTICATED_IEX'
                status,message,cache=request('POST',payload=body)
                self.assertEqual(status,200);self.assertNotIn('synthetic-secret',message)
                persist.assert_called_once_with(dict(zip(NAMES,('synthetic-key','synthetic-secret'))))
                self.assertEqual(request('POST',payload=body)[0],410)
                self.assertEqual(persist.call_count,1)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_exact_origin_and_host_required_for_post(self):
        host='127.0.0.1:8769'
        self.assertTrue(allowed_request(host,'http://'+host,host,True))
        for value in (None,'null','http://evil.example','http://localhost:8769','http://127.0.0.1:8768'):
            self.assertFalse(allowed_request(host,value,host,True))
        self.assertFalse(allowed_request('evil.example','http://'+host,host,True))
    def test_detached_launch_preserves_existing_configuration(self):
        from data.local_setup import launch
        with patch('data.local_setup.configured',return_value={'encrypted_config_present':True}),patch('socket.socket') as socket,patch('data.local_setup.subprocess.Popen') as spawn:
            socket.return_value.__enter__.return_value.connect_ex.return_value=0
            with self.assertRaises(RuntimeError):launch()
            spawn.assert_not_called()
    def test_detached_launch_refuses_existing_listener(self):
        from data.local_setup import launch
        with patch('data.local_setup.configured',return_value={'encrypted_config_present':False}),patch('socket.socket') as socket,patch('data.local_setup.subprocess.Popen') as spawn:
            socket.return_value.__enter__.return_value.connect_ex.return_value=0
            with self.assertRaises(RuntimeError):launch()
            spawn.assert_not_called()
    def test_duplicate_missing_extra_invalid_and_non_utf8_fields_rejected(self):
        valid=b'APCA_API_KEY_ID=synthetic-key&APCA_API_SECRET_KEY=synthetic-secret'
        self.assertEqual(parse_keys(valid),dict(zip(NAMES,('synthetic-key','synthetic-secret'))))
        for body in (valid+b'&APCA_API_KEY_ID=duplicate',valid+b'&token=unrelated',
                     b'APCA_API_KEY_ID=synthetic-key',b'APCA_API_KEY_ID=short&APCA_API_SECRET_KEY=synthetic-secret',b'\xff'):
            with self.assertRaises((ValueError,UnicodeError)):parse_keys(body)
    def test_non_loopback_bind_rejected_before_socket(self):
        with patch('data.local_setup.HTTPServer.__init__') as bind:
            with self.assertRaises(ValueError):SetupServer(('0.0.0.0',8769))
            bind.assert_not_called()
    def test_save_encrypts_and_roundtrip_checks_before_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.dpapi'
            keys=dict(zip(NAMES,('synthetic-key','synthetic-secret')))
            with patch('data.credentials.PATH',path),patch('data.credentials.transform',side_effect=[b'encrypted',b'invalid']):
                with self.assertRaises(RuntimeError):save(keys)
                self.assertFalse(path.exists())
    def test_save_exclusive_and_never_overwrites_existing(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.dpapi'
            keys=dict(zip(NAMES,('synthetic-key','synthetic-secret')))
            with patch('data.credentials.PATH',path),patch('data.credentials.transform',side_effect=[b'ciphertext',json.dumps(keys).encode()]):
                save(keys)
                self.assertEqual(path.read_bytes(),b'ciphertext')
                with self.assertRaises(RuntimeError):save(keys)
                self.assertEqual(path.read_bytes(),b'ciphertext')

if __name__=='__main__':unittest.main()
