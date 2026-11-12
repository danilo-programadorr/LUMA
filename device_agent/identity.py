"""Windows-user DPAPI key protection and atomic SQLite counter reservation."""
import ctypes,os,sqlite3,subprocess,re
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,NoEncryption
from backend.device_protocol import public_text,fingerprint
ROOT=Path(__file__).resolve().parents[1]/'runtime'
class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
def protect(data,decrypt=False):
    if os.name!='nt':raise RuntimeError('WINDOWS_DPAPI_REQUIRED')
    crypt=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    buffer=ctypes.create_string_buffer(data);source=Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));out=Blob()
    function=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype=wintypes.BOOL;kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out)):raise RuntimeError('DEVICE_KEY_PROTECTION_FAILED')
    try:return ctypes.string_at(out.data,out.size)
    finally:kernel.LocalFree(out.data)
class Identity:
    def __init__(self,path=None,create=False):
        self.path=(Path(path) if path else ROOT/'device-agent'/'identity.db').resolve()
        if not self.path.is_relative_to(ROOT.resolve()) or self.path.suffix!='.db':raise ValueError('DEVICE_STORAGE_LOCATION_INVALID')
        if not self.path.exists() and not create:raise RuntimeError('DEVICE_IDENTITY_MISSING_NEW_ENROLLMENT_REQUIRED')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if create:
            if os.name!='nt':raise RuntimeError('WINDOWS_DPAPI_REQUIRED')
            account=os.environ['USERDOMAIN']+'\\'+os.environ['USERNAME']
            result=subprocess.run(['icacls',str(self.path.parent),'/inheritance:r','/grant:r',account+':(OI)(CI)F','SYSTEM:(OI)(CI)F'],capture_output=True)
            if result.returncode:raise RuntimeError('DEVICE_STORAGE_ACL_FAILED')
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY CHECK(id=1), protected_key BLOB NOT NULL, sequence INTEGER NOT NULL, device_id TEXT, endpoint TEXT)')
            if not c.execute('SELECT 1 FROM identity').fetchone():
                if not create:raise RuntimeError('DEVICE_IDENTITY_MISSING_NEW_ENROLLMENT_REQUIRED')
                key=Ed25519PrivateKey.generate().private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption())
                c.execute('INSERT INTO identity VALUES (1,?,0,NULL,NULL)',(protect(key),))
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=10);c.execute('PRAGMA synchronous=FULL')
        try:
            with c:yield c
        finally:c.close()
    def key(self):
        with self.connect() as c:blob=c.execute('SELECT protected_key FROM identity WHERE id=1').fetchone()[0]
        return Ed25519PrivateKey.from_private_bytes(protect(blob,True))
    def public(self):return public_text(self.key())
    def fingerprint(self):return fingerprint(self.public())
    def reserve(self):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');n=c.execute('SELECT sequence FROM identity WHERE id=1').fetchone()[0]+1
            if n>9007199254740991:raise RuntimeError('DEVICE_SEQUENCE_EXHAUSTED')
            c.execute('UPDATE identity SET sequence=? WHERE id=1',(n,));return n
    def binding(self):
        with self.connect() as c:return c.execute('SELECT device_id,endpoint FROM identity WHERE id=1').fetchone()
    def bind(self,device_id,endpoint):
        if not re.fullmatch(r'[a-f0-9]{32}',device_id):raise ValueError('DEVICE_ID_INVALID')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT device_id,endpoint FROM identity WHERE id=1').fetchone()
            if old[0] and old!=(device_id,endpoint):raise RuntimeError('DEVICE_REBIND_DENIED')
            c.execute('UPDATE identity SET device_id=?,endpoint=? WHERE id=1',(device_id,endpoint))
