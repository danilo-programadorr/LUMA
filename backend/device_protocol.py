"""Device v1: domain-separated deterministic JSON signed with Ed25519."""
import base64,hashlib,json
from dataclasses import dataclass
from typing import Literal
from pydantic import Field
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from .app.models import Contract
from .app.errors import Fault
CAPABILITIES=('RUNTIME_INTELLIGENCE','DEVICE_HEARTBEAT','OUTBOUND_POLLING')
FUTURE_CAPABILITIES=('WEB_RESEARCH','CODEX_EXECUTOR','FILESYSTEM','BROWSER','DESKTOP')

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def encode(value):return base64.urlsafe_b64encode(value).decode('ascii')
def decode(value,length):
    try:
        raw=base64.b64decode(value,altchars=b'-_',validate=True)
        if len(raw)!=length or encode(raw)!=value:raise ValueError()
        return raw
    except Exception:raise Fault('DEVICE_SIGNATURE_INVALID',401) from None
def public_text(key):return encode(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
def fingerprint(public):return hashlib.sha256(decode(public,32)).hexdigest()
def verify(public,signature,message):
    try:Ed25519PublicKey.from_public_bytes(decode(public,32)).verify(decode(signature,64),message)
    except Exception:raise Fault('DEVICE_SIGNATURE_INVALID',401) from None
class EnrollmentStart(Contract):
    display_name:str=Field(min_length=1,max_length=80,pattern=r'^[^\x00-\x1f]+$')
class EnrollmentComplete(Contract):
    challenge_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    code:str=Field(min_length=40,max_length=128)
    public_key:str=Field(min_length=44,max_length=44)
    signature:str=Field(min_length=88,max_length=88)
    platform:Literal['WINDOWS']='WINDOWS'
    device_protocol_version:Literal['1']='1'
def enrollment_bytes(body):
    d=body.model_dump();d.pop('signature');return b'LUMA-DEVICE-ENROLLMENT-1\n'+canonical(d)
class SignedDeviceRequest(Contract):
    device_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    device_protocol_version:Literal['1']='1'
    timestamp:int=Field(gt=0)
    sequence:int=Field(gt=0,le=9007199254740991)
    nonce:str=Field(pattern=r'^[a-f0-9]{32}$')
    payload_hash:str=Field(pattern=r'^[a-f0-9]{64}$')
    payload:dict
    signature:str=Field(min_length=88,max_length=88)
def request_bytes(path,body):
    d=body.model_dump();d.pop('signature');d.pop('payload');d.update(method='POST',path=path)
    return b'LUMA-DEVICE-REQUEST-1\n'+canonical(d)
class Heartbeat(Contract):
    runtime_version:str=Field(pattern=r'^[0-9a-z.-]{1,30}$')
    capabilities:list[Literal['RUNTIME_INTELLIGENCE','DEVICE_HEARTBEAT','OUTBOUND_POLLING']]=Field(max_length=3)
    health:Literal['OK','ERROR']='OK'
    current_load:int=Field(default=0,ge=0,le=1)
class Poll(Contract):pass
class Result(Contract):
    job_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    lease_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    outcome:Literal['SYNTHETIC_OK','RELEASE']='SYNTHETIC_OK'
@dataclass(frozen=True)
class AuthenticatedDevicePrincipal:
    device_id:str
    owner_binding_id:int
    key_fingerprint:str
    sequence:int
