import importlib,json,subprocess,sys,threading,time,uuid
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import pytest
from device_agent.identity import Identity
from device_agent.client import DeviceClient,ChannelError
from backend.private_library.store import LibraryStore
from backend.private_library.extract import parser_environment
from backend.app.errors import Fault

DID='a'*32

def agent():
 try:return importlib.import_module('library_agent.client'),importlib.import_module('library_agent.__main__')
 except ModuleNotFoundError:pytest.fail('Private library agent not implemented')

def test_shared_identity_serializes_sequence_and_send():
 path=Path('runtime')/('library-transport-test-'+uuid.uuid4().hex)/'identity.db';identity=Identity(path,create=True);identity.bind(DID,'http://127.0.0.1');received=[];barrier=threading.Barrier(2)
 class Transport:
  def post(self,url,**kw):
   b=kw['json']
   if b['sequence']==1:time.sleep(.15)
   received.append(b['sequence']);data={'request_nonce':b['nonce'],'device_id':DID};return SimpleNamespace(status_code=200,content=json.dumps(data).encode(),json=lambda:data)
 clients=[DeviceClient(Identity(path),'http://127.0.0.1',Transport()) for _ in range(2)]
 def issue(i):barrier.wait();return clients[i].signed('heartbeat',{})
 with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(issue,range(2)))
 assert received==[1,2]

@pytest.mark.parametrize('base',['https://public.example','http://192.168.1.10:8770'])
def test_private_agent_refuses_nonlocal_endpoint(base):
 cls=agent()[0].LibraryClient
 with pytest.raises(ValueError,match='LIBRARY_LOCAL_ENDPOINT_REQUIRED'):cls(SimpleNamespace(binding=lambda:(DID,'')),base)

def test_import_only_metadata_leaves_store(tmp_path):
 _,main=agent();raw=b'UniqueLocalPrivateSentinel cancellation.';path=tmp_path/'manual.txt';path.write_bytes(raw);calls=[]
 class Client:
  identity=SimpleNamespace(binding=lambda:(DID,'http://127.0.0.1:8770'))
  def library(self,op,payload):calls.append((op,payload));return {'status':'AUTHORIZED'} if op=='check' else {'status':'REGISTERED','source_id':payload['source']['source_id']}
 result=main.import_document(Client(),LibraryStore(tmp_path/'store',device_id=DID),'meu-gestor',path,None)
 assert result['status']=='REGISTERED' and 'UniqueLocalPrivateSentinel' not in json.dumps(calls)
 assert calls[0][0]=='check' and calls[-1][0]=='register'

def test_denied_import_does_not_open_file(tmp_path):
 _,main=agent()
 class Client:
  def library(self,*a):raise ChannelError('LIBRARY_CAPABILITY_REQUIRED')
 with pytest.raises(ChannelError):main.import_document(Client(),None,'meu-gestor',tmp_path/'missing.txt',None)

def stub_client(job,check_error=None):
 cls=agent()[0].LibraryClient
 class Client(cls):
  def __init__(self):self.identity=SimpleNamespace(binding=lambda:(DID,'http://127.0.0.1:8770'));self.sent=[];self.stop=threading.Event()
  def heartbeat(self):pass
  def library(self,op,payload):
   self.sent.append((op,payload))
   if op=='poll':return {'request':job,'lease_id':'b'*32}
   if op=='check' and check_error:raise ChannelError(check_error)
   return {'status':'ACCEPTED'}
 return Client()

def work(source):return {'query_id':'d'*32,'project_id':'meu-gestor','target_device_id':DID,'query':'cancelamento','source_ids':[source],'expires_at':int(time.time())+180}

def test_local_query_returns_only_scoped_excerpts(tmp_path):
 agent();store=LibraryStore(tmp_path/'store',device_id=DID);m=store.ingest('meu-gestor','Synthetic','.txt',b'Cancelamento imediato protege o sistema.');client=stub_client(work(m.source_id));client.cycle(store)
 result=[p for op,p in client.sent if op=='result'][0];assert result['matches'][0]['source_id']==m.source_id and result['matches'][0]['excerpt'].startswith('Cancelamento')
 assert [op for op,_ in client.sent].count('check')==2

def test_cancelled_query_not_read_locally():
 client=stub_client(work('e'*32),'LIBRARY_LEASE_INVALID');store=SimpleNamespace(retrieve=lambda *a:pytest.fail('Should not read after cancellation'))
 with pytest.raises(ChannelError):client.cycle(store)
 assert not any(op=='result' for op,_ in client.sent)

def test_wrong_device_job_rejected():
 job=work('e'*32);job['target_device_id']='f'*32;client=stub_client(job)
 with pytest.raises(ChannelError):client.cycle(SimpleNamespace())

def test_local_error_is_bounded():
 client=stub_client(work('e'*32))
 def fail(*a):raise Fault('UNEXPECTED_PRIVATE_DETAILS',500)
 client.cycle(SimpleNamespace(retrieve=fail));result=[p for op,p in client.sent if op=='result'][0];assert result['error_code']=='LIBRARY_LOCAL_FAILURE' and result['matches']==[]

def test_private_agent_import_has_no_model_or_control_authority():
 agent();probe="import json,sys;import library_agent.client,library_agent.__main__;print(json.dumps([m for m in ('sqlalchemy','psycopg','google.genai','backend.app.database','backend.app.trust','backend.research.provider') if m in sys.modules]))"
 result=subprocess.run([sys.executable,'-c',probe],env=parser_environment(),capture_output=True,text=True,check=True);assert json.loads(result.stdout)==[]

def test_synthetic_import_and_signed_roundtrip():
 import os
 from backend.tests.private_library_support import build,HEADERS
 from backend.private_library.contracts import SourceMetadata
 from library_agent.client import LibraryClient
 from library_agent.__main__ import import_document
 from pytest import MonkeyPatch
 flag=MonkeyPatch();flag.setenv('LUMA_ENV','test')
 folder=Path('runtime')/('library-roundtrip-'+uuid.uuid4().hex);folder.mkdir();url='sqlite:///'+(folder/'control.db').resolve().as_posix()
 app,c,clock,existing,send=build(url)
 try:
  identity=Identity(folder/'identity.db',create=True)
  class Transport:
   def post(self,url,**kwargs):return c.post(url,json=kwargs['json'])
  client=LibraryClient(identity,'http://127.0.0.1',Transport())
  ch=c.post('/v1/devices/enrollment/start',headers=HEADERS,json={'display_name':'Synthetic library device'}).json()
  d=client.enroll(ch['challenge_id'],ch['code']);assert c.post('/v1/devices/'+d['device_id']+'/approve',headers=HEADERS,json={'fingerprint':d['key_fingerprint']}).status_code==200
  assert c.post('/v1/library/devices/'+d['device_id']+'/capability',headers=HEADERS,json={'enabled':True}).status_code==200
  text=folder/'source.txt';text.write_text('Cancelamento sintetico com referencia local.',encoding='utf-8');store=LibraryStore(folder/'store',device_id=d['device_id']);assert import_document(client,store,'meu-gestor',text)['status']=='REGISTERED'
  client.heartbeat();row=c.post('/v1/library/queries',headers=HEADERS,json={'project_id':'meu-gestor','target_device_id':d['device_id'],'query':'cancelamento','idempotency_key':uuid.uuid4().hex}).json();assert client.cycle(store)['status']=='COMPLETED'
  result=c.get('/v1/library/queries/'+row['query_id'],headers=HEADERS).json();assert result['result']['matches'][0]['excerpt']=='Cancelamento sintetico com referencia local.'
 finally:c.__exit__(None,None,None);app.state.control.close();flag.undo()

@pytest.mark.parametrize('filename',[r'\\remote-server\share\private.txt','https://example.invalid/private.pdf'])
def test_import_rejects_network_paths_before_filesystem_access(monkeypatch,filename):
 _,main=agent()
 class Client:
  def library(self,*args):return {'status':'AUTHORIZED'}
 monkeypatch.setattr(Path,'lstat',lambda *a,**k:pytest.fail('Network path must be rejected before file IO'))
 with pytest.raises(Fault) as e:main.import_document(Client(),None,'meu-gestor',filename)
 assert e.value.code=='LIBRARY_LOCAL_FILE_REQUIRED'
