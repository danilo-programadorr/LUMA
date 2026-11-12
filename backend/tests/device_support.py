import hashlib,time,uuid
from datetime import datetime,timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from backend.device_protocol import *
from backend.control_plane_app import ControlPlaneSettings,create_control_plane
from backend.migrate import migrate
HEADERS={'Authorization':'Bearer owner-fixture'}
class Verifier:
    def verify(self,token):
        if token not in ('owner-fixture','other-fixture'):raise Fault('UNAUTHORIZED',401)
        return {'sub':token,'auth_time':int(time.time())}
def build(url,backend='sqlite'):
    migrate(url,backend,devices=True)
    app=create_control_plane(ControlPlaneSettings(database_url=url,database_backend=backend,owner_auth_mode='IDENTITY_PLATFORM',identity_project='synthetic',devices_enabled=True,device_test_tool=True),_test_verifier=Verifier())
    client=TestClient(app,base_url='http://127.0.0.1');client.__enter__()
    code=app.state.owner_auth.issue_bootstrap()
    assert client.post('/v1/owner/bootstrap',headers=HEADERS,json={'code':code}).status_code==200
    clock=[datetime.now(timezone.utc)];app.state.execution.clock=lambda:clock[0]
    return app,client,clock

def enroll(client,approve=True,key=None):
    key=key or Ed25519PrivateKey.generate()
    challenge=client.post('/v1/devices/enrollment/start',headers=HEADERS,json={'display_name':'Synthetic PC'}).json()
    body=enrollment(challenge,key)
    result=client.post('/v1/devices/enrollment/complete',json=body.model_dump());assert result.status_code==200,result.text
    row=result.json()
    if approve:
        result=client.post('/v1/devices/'+row['device_id']+'/approve',headers=HEADERS,json={'fingerprint':row['key_fingerprint']});assert result.status_code==200,result.text
    return key,row,challenge,body

def enrollment(challenge,key):
    b=EnrollmentComplete(challenge_id=challenge['challenge_id'],code=challenge['code'],public_key=public_text(key),signature='A'*88)
    return b.model_copy(update={'signature':encode(key.sign(enrollment_bytes(b)))})
def signed(key,did,seq,payload,operation='heartbeat',timestamp=None,nonce=None):
    b=SignedDeviceRequest(device_id=did,timestamp=timestamp or int(time.time()),sequence=seq,nonce=nonce or uuid.uuid4().hex,payload_hash=hashlib.sha256(canonical(payload)).hexdigest(),payload=payload,signature='A'*88)
    return b.model_copy(update={'signature':encode(key.sign(request_bytes('/v1/device-runtime/'+operation,b)))}).model_dump()
HB={'runtime_version':'0.6.0rc1','capabilities':list(CAPABILITIES),'health':'OK','current_load':0}
