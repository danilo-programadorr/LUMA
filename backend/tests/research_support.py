import time,uuid,hashlib
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from backend.tests.device_support import Verifier,enroll,HEADERS,HB,signed
from backend.control_plane_app import ControlPlaneSettings,create_control_plane
from backend.migrate import migrate
from backend.device_protocol import SignedDeviceRequest,canonical,encode,request_bytes

def build(url,backend='sqlite'):
    migrate(url,backend,research=True)
    app=create_control_plane(ControlPlaneSettings(database_url=url,database_backend=backend,owner_auth_mode='IDENTITY_PLATFORM',identity_project='synthetic',devices_enabled=True,research_enabled=True),_test_verifier=Verifier())
    c=TestClient(app,base_url='http://127.0.0.1');c.__enter__();code=app.state.owner_auth.issue_bootstrap();assert c.post('/v1/owner/bootstrap',headers=HEADERS,json={'code':code}).status_code==200
    clock=[datetime.now(timezone.utc)];app.state.execution.clock=lambda:clock[0]
    k,d,_,_=enroll(c)
    assert c.post('/v1/research/devices/'+d['device_id']+'/capability',headers=HEADERS,json={'enabled':True}).status_code==200
    assert c.post('/v1/device-runtime/heartbeat',json=signed(k,d['device_id'],1,HB)).status_code==200
    seq=[1]
    def send(op,payload):
        seq[0]+=1;path='/v1/research-runtime/'+op
        b=SignedDeviceRequest(device_id=d['device_id'],timestamp=int(clock[0].timestamp()),sequence=seq[0],nonce=uuid.uuid4().hex,payload_hash=hashlib.sha256(canonical(payload)).hexdigest(),payload=payload,signature='A'*88)
        b=b.model_copy(update={'signature':encode(k.sign(request_bytes(path,b)))})
        return c.post(path,json=b.model_dump())
    assert send('heartbeat',{'protocol_version':'1','capability':'WEB_RESEARCH'}).status_code==200
    return app,c,clock,d,send

def create(c,d,**kw):
    data={'project_id':'meu-gestor','query':'Qual a versão atual do React?','target_device_id':d['device_id'],'idempotency_key':uuid.uuid4().hex,**kw}
    return c.post('/v1/research',headers=HEADERS,json=data)
