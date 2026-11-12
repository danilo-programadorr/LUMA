import hashlib,json,uuid
from pathlib import Path
from datetime import timedelta
import pytest
from backend.tests.private_library_support import build,enable,register,metadata,create,delivery,HEADERS

@pytest.fixture
def library(monkeypatch):
 monkeypatch.setenv('LUMA_ENV','test');path=Path('runtime')/('private-library-test-'+uuid.uuid4().hex+'.db')
 app,c,clock,d,send=build('sqlite:///'+path.resolve().as_posix())
 yield app,c,clock,d,send
 c.__exit__(None,None,None);app.state.control.close();path.unlink(missing_ok=True)

def test_library_schema_and_initial_grant_closed(library):
 app,c,clock,d,send=library;devices=c.get('/v1/library/devices',headers=HEADERS);assert devices.status_code==200 and devices.json()[0]['private_library_approved'] is False
 assert send('check',{'project_id':'meu-gestor'}).status_code==403

def test_authorized_metadata_register_deduplicates(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);register(c,d,send)
 rows=c.get('/v1/library/projects/meu-gestor/sources',headers=HEADERS).json();assert len(rows)==1 and rows[0]['source_id']==m.source_id

def test_roundtrip_transient_result_no_private_content_in_db(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);r=create(c,d);assert r.status_code==200
 payload=delivery(send,m,'UniquePrivateQuoteNotForDatabase');assert send('result',payload).status_code==200
 view=c.get('/v1/library/queries/'+r.json()['query_id'],headers=HEADERS).json();assert view['status']=='COMPLETED' and view['result']['matches'][0]['excerpt']=='UniquePrivateQuoteNotForDatabase'
 assert view['result']['matches'][0]['source']['title']==m.title
 assert c.get('/v1/library/queries/'+r.json()['query_id'],headers=HEADERS).json()['result'] is None
 with app.state.control.store.read() as repo:
  assert 'UniquePrivateQuoteNotForDatabase' not in json.dumps(repo.rows('library_queries')+repo.rows('audit_events'))
  assert not repo.rows('jobs') and not repo.rows('execution_authorizations')

def test_query_idempotency_no_duplicate_work(library):
 app,c,clock,d,send=library;enable(c,d,send);register(c,d,send);key=uuid.uuid4().hex;a=create(c,d,idempotency_key=key);b=create(c,d,idempotency_key=key);assert a.json()['query_id']==b.json()['query_id']
 assert create(c,d,idempotency_key=key,query='outro termo').status_code==409

def test_empty_retrieval_does_not_invent(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);r=create(c,d);payload=delivery(send,m);payload['matches']=[];assert send('result',payload).status_code==200
 assert c.get('/v1/library/queries/'+r.json()['query_id'],headers=HEADERS).json()['result']['matches']==[]

def test_offline_waits_and_expires_without_fallback(library):
 app,c,clock,d,send=library;enable(c,d,send);register(c,d,send);clock[0]+=timedelta(seconds=60);r=create(c,d);assert r.json()['status']=='WAITING_FOR_DEVICE';clock[0]+=timedelta(seconds=181)
 view=c.get('/v1/library/queries/'+r.json()['query_id'],headers=HEADERS).json();assert view['status']=='FAILED' and view['error_code']=='LIBRARY_QUERY_EXPIRED'

def test_archive_cancels_pending_and_blocks_register_resurrection(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);r=create(c,d);payload=delivery(send,m)
 assert c.post('/v1/library/projects/meu-gestor/sources/'+m.source_id+'/archive',headers=HEADERS,json={}).status_code==200
 assert send('result',payload).status_code!=200
 assert send('register',{'source':m.model_dump()}).status_code==409
 view=c.get('/v1/library/queries/'+r.json()['query_id'],headers=HEADERS).json();assert not view['result']

def test_archive_invalidates_already_received_result(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);r=create(c,d);assert send('result',delivery(send,m)).status_code==200
 c.post('/v1/library/projects/meu-gestor/sources/'+m.source_id+'/archive',headers=HEADERS,json={});assert not c.get('/v1/library/queries/'+r.json()['query_id'],headers=HEADERS).json()['result']

def test_current_capability_rechecked_before_display(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);r=create(c,d);assert send('result',delivery(send,m)).status_code==200
 assert c.post('/v1/library/devices/'+d['device_id']+'/capability',headers=HEADERS,json={'enabled':False}).status_code==200
 assert c.get('/v1/library/queries/'+r.json()['query_id'],headers=HEADERS).status_code==403

@pytest.mark.parametrize('operation',['register','query'])
def test_other_project_cannot_cross_scope(library,operation):
 app,c,clock,d,send=library;enable(c,d,send)
 if operation=='register':
  value=metadata(d).model_dump();value['project_id']='other-project';response=send('register',{'source':value})
 else:response=create(c,d,project_id='other-project')
 assert response.status_code!=200

def test_owner_bearer_is_not_device_signature(library):
 app,c,clock,d,send=library;assert c.post('/v1/library-runtime/poll',headers=HEADERS,json={}).status_code==401

def test_unknown_source_not_accepted_in_result(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);create(c,d);payload=delivery(send,m);payload['matches'][0]['source_id']='f'*32;assert send('result',payload).status_code!=200

def test_replay_and_extra_authority_rejected(library):
 app,c,clock,d,send=library;enable(c,d,send);assert send('check',{'project_id':'meu-gestor'}).status_code==200
 assert c.post('/v1/library-runtime/check',json=send.last_body).status_code==409
 value=metadata(d).model_dump();value['approved']=True;assert send('register',{'source':value}).status_code==400

def test_registration_is_not_google_ingestion(library):
 app,c,clock,d,send=library;enable(c,d,send);value=metadata(d).model_dump();value['origin']='GOOGLE_GROUNDED_RESULT';assert send('register',{'source':value}).status_code==400

def test_cancel_prevents_late_result(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);r=create(c,d);payload=delivery(send,m);c.post('/v1/library/queries/'+r.json()['query_id']+'/cancel',headers=HEADERS,json={});assert send('result',payload).status_code==409

def test_runtime_check_lease_denies_cancelled_query(library):
 app,c,clock,d,send=library;enable(c,d,send);m=register(c,d,send);q=create(c,d);payload=delivery(send,m)
 c.post('/v1/library/queries/'+q.json()['query_id']+'/cancel',headers=HEADERS,json={})
 assert send('check',{'project_id':'meu-gestor','query_id':payload['query_id'],'lease_id':payload['lease_id']}).status_code==409

def test_library_online_is_distinct_from_general_pc_heartbeat(library):
 app,c,clock,d,send=library
 assert c.post('/v1/library/devices/'+d['device_id']+'/capability',headers=HEADERS,json={'enabled':True}).status_code==200
 assert c.get('/v1/library/devices',headers=HEADERS).json()[0]['private_library_online'] is False
 send('heartbeat',{'protocol_version':'1','capability':'PRIVATE_LIBRARY'})
 assert c.get('/v1/library/devices',headers=HEADERS).json()[0]['private_library_online'] is True

def test_private_research_is_directed_to_local_area_without_web_queue(library):
 app,c,clock,d,send=library
 response=c.post('/v1/research',headers=HEADERS,json={'project_id':'meu-gestor','query':'Consulte minha biblioteca privada','target_device_id':d['device_id'],'idempotency_key':uuid.uuid4().hex})
 assert response.status_code==409 and response.json()['error']['code']=='PRIVATE_LIBRARY_USE_KNOWLEDGE'
 with app.state.control.store.read() as r:assert not r.rows('research_requests')

def test_owner_can_suspend_library_without_fresh_stepup(library):
 import time
 from sqlalchemy import select
 from backend.owner_schema import owner_bindings
 from backend.owner_auth import AuthenticatedOwnerPrincipal
 app,c,clock,d,send=library;enable(c,d,send)
 with app.state.control.store.read() as r:b=r.connection.execute(select(owner_bindings)).mappings().one()
 old=AuthenticatedOwnerPrincipal(b['internal_owner_id'],'google.com',b['subject_uid'],int(time.time())-3600,'synthetic-suspension')
 assert app.state.library.grant(old,d['device_id'],False)['private_library_approved'] is False
