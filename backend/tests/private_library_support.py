import inspect,hashlib,uuid
from pathlib import Path
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from backend.control_plane_app import ControlPlaneSettings,create_control_plane
from backend.migrate import migrate
from backend.device_protocol import SignedDeviceRequest,canonical,encode,request_bytes
from backend.tests.device_support import Verifier,enroll,HEADERS,HB,signed
from backend.private_library.contracts import SourceMetadata
from backend.private_library.store import source_id

def build(url,backend='sqlite'):
 assert 'library' in inspect.signature(migrate).parameters,'Private library migration not implemented'
 assert 'library_enabled' in ControlPlaneSettings.__dataclass_fields__,'Private library feature flag not implemented'
 migrate(url,backend,library=True)
 app=create_control_plane(ControlPlaneSettings(database_url=url,database_backend=backend,owner_auth_mode='IDENTITY_PLATFORM',identity_project='synthetic',devices_enabled=True,research_enabled=True,library_enabled=True),_test_verifier=Verifier())
 c=TestClient(app,base_url='http://127.0.0.1');c.__enter__();code=app.state.owner_auth.issue_bootstrap();assert c.post('/v1/owner/bootstrap',headers=HEADERS,json={'code':code}).status_code==200
 clock=[datetime.now(timezone.utc)];app.state.execution.clock=lambda:clock[0]
 key,device,_,_=enroll(c);assert c.post('/v1/device-runtime/heartbeat',json=signed(key,device['device_id'],1,HB)).status_code==200
 sequence=[1]
 def send(op,payload):
  sequence[0]+=1;path='/v1/library-runtime/'+op;b=SignedDeviceRequest(device_id=device['device_id'],timestamp=int(clock[0].timestamp()),sequence=sequence[0],nonce=uuid.uuid4().hex,payload_hash=hashlib.sha256(canonical(payload)).hexdigest(),payload=payload,signature='A'*88);b=b.model_copy(update={'signature':encode(key.sign(request_bytes(path,b)))});send.last_body=b.model_dump();return c.post(path,json=send.last_body)
 return app,c,clock,device,send

def enable(c,d,send):
 assert c.post('/v1/library/devices/'+d['device_id']+'/capability',headers=HEADERS,json={'enabled':True}).status_code==200
 assert send('heartbeat',{'protocol_version':'1','capability':'PRIVATE_LIBRARY'}).status_code==200

def metadata(d,title='Synthetic private source',content=b'Synthetic private cancellation procedure.'):
 digest=hashlib.sha256(content).hexdigest();return SourceMetadata(source_id=source_id('meu-gestor',d['device_id'],digest),project_id='meu-gestor',device_id=d['device_id'],title=title,content_hash=digest,extension='.txt',byte_count=len(content),page_count=0,chunk_count=1)

def register(c,d,send,**kw):
 m=metadata(d,**kw);response=send('register',{'source':m.model_dump()});assert response.status_code==200,response.text;return m

def create(c,d,**kw):return c.post('/v1/library/queries',headers=HEADERS,json={'project_id':'meu-gestor','target_device_id':d['device_id'],'query':'cancelamento','idempotency_key':uuid.uuid4().hex,**kw})

def delivery(send,m,quote='Synthetic private cancellation procedure.'):
 poll=send('poll',{});assert poll.status_code==200,poll.text;job=poll.json()['request'];return {'query_id':job['query_id'],'lease_id':poll.json()['lease_id'],'matches':[{'source_id':m.source_id,'source_hash':m.content_hash,'chunk_id':'c'*24,'excerpt':quote,'page':None,'line_start':1,'line_end':1,'score':1.0}]}
