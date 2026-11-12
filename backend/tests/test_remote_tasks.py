import secrets
import pytest
from backend.tests.test_execution import engine
from backend.tests.test_conversation import bundle
from backend.app.errors import Fault
from backend.app.models import ident

def service(engine):
 from backend.remote_tasks import RemoteTasks
 return RemoteTasks(engine[0])
def create(engine,operation='record'):
 e,p,t=engine
 device=e.devices.register(p,{'device_id':'remote-test','name':'Remote Test','device_type':'WINDOWS'},secrets.token_hex(12),'test')
 e._remote_test_credential=device['device_credential']
 return service(engine).create(p,{'project_id':'meu-gestor','task_type':'ACTION_ORIENTED','input':'Efeito sintético autorizado somente após revisão','target_device_id':'remote-test','idempotency_key':secrets.token_hex(12),'operation':operation},'test')
def test_remote_task_idempotency_and_no_implicit_approval(engine):
 s=service(engine);e,p,t=engine
 body={'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'Analise as alternativas','idempotency_key':secrets.token_hex(12)}
 a=s.create(p,body,'test');b=s.create(p,body,'test');assert a['task_id']==b['task_id']
 with e.store.read() as r:assert not r.rows('execution_authorizations') and not r.rows('jobs')
def test_remote_approve_snapshot_and_one_job(engine):
 a=create(engine);s=service(engine);e,p,t=engine
 assert a['status']=='WAITING_AUTHORIZATION'
 b=s.decide(p,a['task_id'],{'decision':'APPROVE','proposal_hash':a['proposal_hash']},'test',True)
 again=s.decide(p,a['task_id'],{'decision':'APPROVE','proposal_hash':a['proposal_hash']},'test',True)
 assert b['job_id']==again['job_id'] and 'authorization_id' not in b
 with e.store.read() as r:assert len(r.rows('execution_authorizations'))==len(r.rows('approvals'))==len(r.rows('jobs'))==1
 assert s.get(p,a['task_id'])['status']=='WAITING_FOR_DEVICE'
def test_remote_reject_is_final(engine):
 a=create(engine);s=service(engine);e,p,t=engine
 s.decide(p,a['task_id'],{'decision':'REJECT','proposal_hash':a['proposal_hash']},'test',False)
 with pytest.raises(Fault):s.decide(p,a['task_id'],{'decision':'APPROVE','proposal_hash':a['proposal_hash']},'test',True)
 with e.store.read() as r:assert not r.rows('execution_authorizations') and not r.rows('jobs')
def test_remote_stale_snapshot_denied(engine):
 a=create(engine);e,p,t=engine
 with e.store.transaction() as r:
  action=r.get('actions',a['action_request_id']);action['envelope']['parameters']={'changed':True};r.put('actions',a['action_request_id'],action)
 with pytest.raises(Fault,match='PROPOSAL_CHANGED'):service(engine).decide(p,a['task_id'],{'decision':'APPROVE','proposal_hash':a['proposal_hash']},'test',True)
def test_remote_cancel_before_approval(engine):
 a=create(engine);e,p,t=engine;s=service(engine);assert s.cancel(p,a['task_id'],'test')['status']=='CANCELLED'
 with pytest.raises(Fault):s.decide(p,a['task_id'],{'decision':'APPROVE','proposal_hash':a['proposal_hash']},'test',True)

import uuid
from backend.tests.device_support import build,HEADERS,enroll

def test_remote_api_owner_binding_recent_auth_and_scope(tmp_path,monkeypatch):
 monkeypatch.setenv('LUMA_ENV','test');app,c,clock=build('sqlite:///'+(tmp_path/'remote.db').as_posix())
 try:
  _,d,_,_=enroll(c)
  with app.state.control.store.transaction() as r:r.add('tools','sandbox-test',dict(tool_id='sandbox-test',enabled=True,capabilities=['record','review','sensitive','critical']))
  body=dict(project_id='meu-gestor',task_type='ACTION_ORIENTED',input='Teste sintético',target_device_id=d['device_id'],idempotency_key=uuid.uuid4().hex)
  response=c.post('/v1/tasks',headers=HEADERS,json=body);assert response.status_code==200,response.text
  t=response.json();assert c.get('/v1/tasks/'+t['task_id'],headers=HEADERS).status_code==200
  denied=c.post('/v1/tasks/'+t['task_id']+'/decision',headers={**HEADERS,'Origin':'https://evil.invalid'},json=dict(decision='APPROVE',proposal_hash=t['proposal_hash']));assert denied.status_code==403
  accepted=c.post('/v1/tasks/'+t['task_id']+'/decision',headers=HEADERS,json=dict(decision='APPROVE',proposal_hash=t['proposal_hash']));assert accepted.status_code==200,accepted.text
  assert 'authorization_id' not in accepted.json()
 finally:c.__exit__(None,None,None)

from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from backend.app.trust_data import verify

def approve(engine,t):return service(engine).decide(engine[1],t['task_id'],{'decision':'APPROVE','proposal_hash':t['proposal_hash'],'confirmation':'AUTHORIZE_EXACT_ACTION'},'test',True)
def test_remote_recent_auth_required(engine):
 t=create(engine)
 with pytest.raises(Fault,match='RECENT_AUTH_REQUIRED'):service(engine).decide(engine[1],t['task_id'],{'decision':'APPROVE','proposal_hash':t['proposal_hash']},'test',False)
def test_remote_critical_denied(engine):
 t=create(engine,'critical')
 with pytest.raises(Fault,match='CRITICAL_UNATTENDED_DENIED'):approve(engine,t)
def test_remote_high_requires_explicit_confirmation(engine):
 t=create(engine,'sensitive')
 with pytest.raises(Fault,match='HIGH_CONFIRMATION_REQUIRED'):service(engine).decide(engine[1],t['task_id'],{'decision':'APPROVE','proposal_hash':t['proposal_hash']},'test',True)
 approve(engine,t)
def test_remote_expired_proposal_denied(engine):
 t=create(engine);engine[2][0]+=timedelta(minutes=6)
 with pytest.raises(Fault,match='TASK_NOT_APPROVABLE'):approve(engine,t)
def test_remote_idempotency_conflict(engine):
 e,p,_=engine;s=service(engine);b={'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'first','idempotency_key':secrets.token_hex(12)};s.create(p,b,'test')
 with pytest.raises(Fault,match='IDEMPOTENCY_CONFLICT'):s.create(p,{**b,'input':'second'},'test')
def test_remote_wrong_project_denied(engine):
 with pytest.raises(Fault):service(engine).create(engine[1],{'project_id':'unknown','task_type':'ANALYTICAL','input':'test','idempotency_key':secrets.token_hex(12)},'test')
def test_remote_agent_cannot_decide(engine):
 t=create(engine);runtime=engine[0].control.principal('luma-runtime')
 with pytest.raises(Fault):service(engine).decide(runtime,t['task_id'],{'decision':'APPROVE','proposal_hash':t['proposal_hash']},'test',True)
def test_remote_offline_revoke_prevents_execution(engine):
 t=create(engine);approve(engine,t);s=service(engine);e,p,_=engine
 assert s.revoke(p,t['task_id'],'test')['status']=='BLOCKED';e.tick();assert e.claim('worker','remote-test',e._remote_test_credential) is None
 with e.store.read() as r:assert not r.rows('sandbox_effects');verify(r)
def test_remote_offline_cancel_prevents_execution(engine):
 t=create(engine);approve(engine,t);e,p,_=engine;s=service(engine);s.cancel(p,t['task_id'],'test');e.tick();assert e.claim('worker','remote-test',e._remote_test_credential) is None
 with e.store.read() as r:assert not r.rows('sandbox_effects')
def test_remote_approve_reject_race(engine):
 t=create(engine);gate=Barrier(2)
 def decide(value):
  gate.wait()
  try:return service(engine).decide(engine[1],t['task_id'],{'decision':value,'proposal_hash':t['proposal_hash']},'test',True)['decision']
  except Fault:return 'DENIED'
 with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(decide,('APPROVE','REJECT')))
 assert result.count('DENIED')==1
 with engine[0].store.read() as r:assert len(r.rows('approvals'))==1


def online(engine):
 e,p,t=engine
 e.devices.heartbeat({'device_id':'remote-test','executor_version':'0.6.0rc1','status':'ONLINE','capabilities':['sandbox-test'],'current_job_count':0},e._remote_test_credential)
def test_remote_synthetic_effect_completes_once(engine):
 t=create(engine);approved=approve(engine,t);e,p,_=engine;online(engine);e.tick();job=e.claim('worker','remote-test',e._remote_test_credential);assert job['job_id']==approved['job_id'];assert e.execute(job['job_id'],'worker')['status']=='SUCCEEDED';assert service(engine).get(p,t['task_id'])['status']=='COMPLETED'
 with e.store.read() as r:assert len(r.rows('sandbox_effects'))==len(r.rows('execution_records'))==1
def test_remote_offline_expiry_no_effect(engine):
 t=create(engine);approve(engine,t);e,p,time=engine;time[0]+=timedelta(minutes=6);online(engine);e.tick();assert e.claim('worker','remote-test',e._remote_test_credential) is None
 with e.store.read() as r:assert not r.rows('sandbox_effects')
def test_remote_kill_switch_prevents_effect(engine):
 t=create(engine);approve(engine,t);e,p,_=engine;online(engine)
 with e.store.transaction() as r:row=r.get('system_state','global');row['state']='STOPPED';r.put('system_state','global',row)
 e.tick();assert e.claim('worker','remote-test',e._remote_test_credential) is None
 with e.store.read() as r:assert not r.rows('sandbox_effects')
def test_remote_restart_projection_persistent(engine):
 t=create(engine);approved=approve(engine,t);assert service(engine).get(engine[1],t['task_id'])['job_id']==approved['job_id']
# Official TestTool grant is separate from approval of any action.
def test_remote_testtool_grant_requires_owner_confirmation(tmp_path,monkeypatch):
 monkeypatch.setenv('LUMA_ENV','test');app,c,clock=build('sqlite:///'+(tmp_path/'grant.db').as_posix())
 try:
  _,d,_,_=enroll(c);path='/v1/remote-task-devices/'+d['device_id']+'/test-capability'
  assert c.post(path,headers=HEADERS,json={'enabled':True,'confirmation':'wrong'}).status_code==400
  response=c.post(path,headers=HEADERS,json={'enabled':True,'confirmation':'SYNTHETIC_TEST_ONLY'});assert response.status_code==200,response.text
  with app.state.control.store.read() as r:assert not r.rows('approvals') and not r.rows('execution_authorizations')
 finally:c.__exit__(None,None,None)

def test_remote_action_cannot_use_legacy_approval_route(engine):
 t=create(engine);e,p,time=engine
 spec={'valid_from':time[0].isoformat(),'expires_at':(time[0]+timedelta(minutes=5)).isoformat(),'max_executions':1,'confirmation':'AUTHORIZE_EXACT_ACTION'}
 with pytest.raises(Fault,match='REMOTE_APPROVAL_REQUIRED'):e.authorize(p,t['action_request_id'],spec,secrets.token_hex(12),'legacy',confirmed=True)
def test_remote_analytical_task_uses_existing_runtime(engine):
 from backend.control_plane_tasks import RuntimeTaskService
 from backend.remote_protocol import RuntimeResultEnvelope
 e,p,_=engine;e.devices.register(p,{'device_id':'analysis-pc','name':'Analysis PC','device_type':'WINDOWS'},secrets.token_hex(12),'test')
 t=service(engine).create(p,{'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'Compare synthetic options','target_device_id':'analysis-pc','idempotency_key':secrets.token_hex(12)},'test')
 runtime=e.control.principal('luma-runtime');gateway=RuntimeTaskService(e.control,e);work=gateway.claim(runtime,t['task_id'],'analysis-pc')
 reply=RuntimeResultEnvelope(task_id=work.task_id,device_id=work.target_device_id,correlation_id=work.correlation_id,answer='Synthetic runtime conclusion')
 gateway.accept(runtime,'analysis-pc',reply.model_dump_json().encode())
 result=service(engine).get(p,t['task_id']);assert result['status']=='COMPLETED' and result['summary']=='Synthetic runtime conclusion'
 with e.store.read() as r:assert not r.rows('approvals') and not r.rows('jobs')

def test_remote_approvals_filter_before_pagination(engine):
 t=create(engine);e,p,_=engine
 with e.store.transaction() as r:
  original=r.get('agent_tasks',t['task_id'])
  for n in range(101):
   x={**original,'task_id':ident(),'task_type':'ANALYTICAL','action_request_id':None,'status':'NEEDS_CLARIFICATION'};r.add('agent_tasks',x['task_id'],x)
 result=service(engine).listing(p,50,approvals=True);assert len(result)==1 and result[0]['task_id']==t['task_id']
def test_remote_revoke_preserves_completed_history(engine):
 t=create(engine);approve(engine,t);e,p,_=engine;online(engine);e.tick();job=e.claim('worker','remote-test',e._remote_test_credential);e.execute(job['job_id'],'worker');assert service(engine).revoke(p,t['task_id'],'test')['status']=='COMPLETED'
def test_remote_reject_requires_approval_grant(engine):
 t=create(engine);e,p,_=engine
 with e.store.transaction() as r:
  for g in r.rows('grants'):
   if g['principal_id']==p.principal_id and g['capability']=='admin.approvals.manage':g['status']='REVOKED';r.put('grants',g['grant_id'],g)
 with pytest.raises(Fault):service(engine).decide(p,t['task_id'],{'decision':'REJECT','proposal_hash':t['proposal_hash']},'test',False)
def test_remote_cancel_blocks_late_runtime_answer(engine):
 from backend.control_plane_tasks import RuntimeTaskService
 from backend.remote_protocol import RuntimeResultEnvelope
 e,p,_=engine;e.devices.register(p,{'device_id':'late-pc','name':'Late PC','device_type':'WINDOWS'},secrets.token_hex(12),'test')
 t=service(engine).create(p,{'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'Synthetic analysis','target_device_id':'late-pc','idempotency_key':secrets.token_hex(12)},'test');gateway=RuntimeTaskService(e.control,e);runtime=e.control.principal('luma-runtime');w=gateway.claim(runtime,t['task_id'],'late-pc');service(engine).cancel(p,t['task_id'],'test')
 reply=RuntimeResultEnvelope(task_id=w.task_id,device_id=w.target_device_id,correlation_id=w.correlation_id,answer='late synthetic answer')
 with pytest.raises(Fault,match='TASK_TERMINAL'):gateway.accept(runtime,'late-pc',reply.model_dump_json().encode())
 assert service(engine).get(p,t['task_id'])['status']=='CANCELLED'
def test_remote_api_runtime_identity_and_answer(tmp_path,monkeypatch):
 from dataclasses import replace
 from fastapi.testclient import TestClient
 from backend.control_plane_app import create_control_plane
 from backend.tests.device_support import Verifier
 from backend.remote_protocol import RuntimeResultEnvelope
 monkeypatch.setenv('LUMA_ENV','test');app,c,_=build('sqlite:///'+(tmp_path/'runtime.db').as_posix())
 try:
  _,d,_,_=enroll(c);secret=secrets.token_urlsafe(32);cfg=replace(app.state.control.settings,runtime_token=secret);second=create_control_plane(cfg,_test_verifier=Verifier())
  with TestClient(second,base_url='http://127.0.0.1') as client:
   t=client.post('/v1/tasks',headers=HEADERS,json={'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'Synthetic analysis','target_device_id':d['device_id'],'idempotency_key':secrets.token_hex(12)}).json()
   assert client.post('/v1/runtime/tasks/poll',headers=HEADERS,json={'device_id':d['device_id']}).status_code==401
   h={'Authorization':'Bearer '+secret};work=client.post('/v1/runtime/tasks/poll',headers=h,json={'device_id':d['device_id']});assert work.status_code==200,work.text;w=work.json()['task']
   result=RuntimeResultEnvelope(task_id=w['task_id'],device_id=w['target_device_id'],correlation_id=w['correlation_id'],answer='Synthetic conclusion')
   response=client.post('/v1/runtime/tasks/result',headers=h,content=result.model_dump_json());assert response.status_code==200,response.text
   assert client.get('/v1/tasks/'+t['task_id'],headers=HEADERS).json()['summary']=='Synthetic conclusion'
   assert client.post('/v1/runtime/tasks/result',headers=h,content='bad').status_code==400
 finally:c.__exit__(None,None,None)
def test_remote_api_recent_auth_ignores_new_iat(tmp_path,monkeypatch):
 import time
 monkeypatch.setenv('LUMA_ENV','test');app,c,_=build('sqlite:///'+(tmp_path/'recent.db').as_posix())
 try:
  _,d,_,_=enroll(c)
  with app.state.control.store.transaction() as r:r.add('tools','sandbox-test',dict(tool_id='sandbox-test',enabled=True,capabilities=['record']))
  t=c.post('/v1/tasks',headers=HEADERS,json={'project_id':'meu-gestor','task_type':'ACTION_ORIENTED','input':'Synthetic test','target_device_id':d['device_id'],'idempotency_key':secrets.token_hex(12)}).json()
  app.state.owner_auth.verifier.verify=lambda token:{'sub':'owner-fixture','auth_time':int(time.time())-3600,'iat':int(time.time())}
  response=c.post('/v1/tasks/'+t['task_id']+'/decision',headers=HEADERS,json={'decision':'APPROVE','proposal_hash':t['proposal_hash']});assert response.status_code==403 and response.json()['error']['code']=='RECENT_AUTH_REQUIRED'
  with app.state.control.store.read() as r:assert any(e['event_type']=='REMOTE_TASK_DECISION_REJECTED' and e['result']=='RECENT_AUTH_REQUIRED' for e in r.rows('audit_events'))
 finally:c.__exit__(None,None,None)
def test_remote_private_library_request_cannot_dispatch_runtime(engine):
 e,p,_=engine;e.devices.register(p,{'device_id':'private-pc','name':'Private PC','device_type':'WINDOWS'},secrets.token_hex(12),'test')
 t=service(engine).create(p,{'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'Consulte minha biblioteca privada','target_device_id':'private-pc','idempotency_key':secrets.token_hex(12)},'test')
 assert t['status']=='BLOCKED' and t['safe_error']=='PRIVATE_LIBRARY_USE_KNOWLEDGE'
 with e.store.read() as r:assert 'envelope' not in r.get('agent_tasks',t['task_id'])
def test_remote_offline_return_can_execute_until_displayed_expiration(engine):
 t=create(engine);approve(engine,t);e,p,clock=engine
 clock[0]+=timedelta(seconds=180);online(engine);e.tick()
 job=e.claim('worker','remote-test',e._remote_test_credential)
 assert job is not None
 assert e.execute(job['job_id'],'worker')['status']=='SUCCEEDED'
def test_remote_listing_reads_audit_timeline_once(engine,monkeypatch):
 from backend.app.database import Repository
 first=create(engine);e,p,_=engine;s=service(engine)
 s.create(p,{'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'Second synthetic task','idempotency_key':secrets.token_hex(12)},'test')
 original=Repository.rows;reads=[]
 def observed(self,table,*args,**kwargs):
  if table=='audit_events':reads.append(table)
  return original(self,table,*args,**kwargs)
 monkeypatch.setattr(Repository,'rows',observed)
 result=s.listing(p)
 assert len(result)==2 and any(t['timeline'] for t in result)
 assert len(reads)==1
