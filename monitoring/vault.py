"""Windows current-user DPAPI store. Plaintext only travels through process pipes.

Never invoke `load` directly in a logged terminal: notifier.cjs consumes its output.
"""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import sys

class Blob(C.Structure):
    _fields_ = [('cbData', W.DWORD), ('pbData', C.POINTER(C.c_ubyte))]

def transform(data, decrypt=False):
    crypt=C.WinDLL('crypt32',use_last_error=True)
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[C.c_void_p]
    kernel.LocalFree.restype=C.c_void_p
    buffer=C.create_string_buffer(data)
    source=Blob(len(data),C.cast(buffer,C.POINTER(C.c_ubyte)))
    target=Blob()
    fn=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes=[C.POINTER(Blob),C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,W.DWORD,C.POINTER(Blob)]
    fn.restype=W.BOOL
    if not fn(C.byref(source),None,None,None,None,1,C.byref(target)):
        raise RuntimeError('Windows credential protection operation failed')
    try:
        return C.string_at(target.pbData,target.cbData)
    finally:
        kernel.LocalFree(C.cast(target.pbData,C.c_void_p))

def main():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from core.runtime_paths import private_directory
    target=private_directory()/'telegram.dpapi'
    command=sys.argv[1]
    if command=='save':
        raw=sys.stdin.buffer.read(16384)
        obj=json.loads(raw)
        if set(obj)!= {'token','chat_id'} or not isinstance(obj['token'],str) or not str(obj['chat_id']).isdigit():
            raise ValueError('Invalid credential payload')
        encrypted=transform(raw)
        if transform(encrypted,True)!=raw:
            raise ValueError('Credential roundtrip failed')
        target.parent.mkdir(parents=True,exist_ok=True)
        # Refuse silent replacement of an existing credential.
        with target.open('xb') as f:
            f.write(encrypted)
        print('ENCRYPTED_CREDENTIAL_SAVED')
    elif command=='load':
        sys.stdout.buffer.write(transform(target.read_bytes(),True))
    elif command=='selftest':
        raw=b'synthetic-test-only'
        assert transform(transform(raw),True)==raw
        print('DPAPI_SELFTEST_PASSED')
    else:
        raise ValueError('Unknown operation')

if __name__=='__main__':
    try:
        main()
    except Exception:
        print('CREDENTIAL_OPERATION_FAILED',file=sys.stderr)
        raise SystemExit(1)
