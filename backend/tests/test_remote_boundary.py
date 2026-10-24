import json,os,secrets,subprocess,sys
from datetime import timedelta
from pathlib import Path
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.migrate import migrate
from backend.control_plane_app import ControlPlaneSettings,create_control_plane
from backend.remote_protocol import *
from backend.runtime_processor import RuntimeTaskProcessor,LocalRuntimeTransport,FutureRemoteRuntimeTransport
from backend.app.errors import Fault
from backend.app.models import now
from backend.app.trust_data import verify

@pytest.fixture
def boundary(tmp_path):
    url='sqlite:///'+(tmp_path/'boundary.db').as_posix();migrate(url)
    cfg=ControlPlaneSettings(token=secrets.token_urlsafe(32),runtime_token=secrets.token_urlsafe(32),admin_confirmation_token=secrets.token_urlsafe(32),database_url=url)
    app=create_control_plane(cfg);c=app.state.control;e=app.state.execution
    owner=c.principal();runtime=c.principal('luma-runtime')
    sid=c.mutate(owner,'session',{'project_id':'meu-gestor'},secrets.token_hex(12),'boundary')['session_id']
    e.devices.register(owner,dict(device_id='pc-boundary',name='Synthetic device',device_type='WINDOWS'),'register-boundary','boundary')
    try:yield app,c,e,owner,runtime,sid
    finally:c.close()

def task(b,**changes):
    app,c,e,o,r,sid=b
    fields=dict(project_id='meu-gestor',session_id=sid,device_id='pc-boundary',message='Crie uma tarefa de teste',
        key=secrets.token_hex(12),correlation='boundary-correlation',scope=Scope(resource='list-main',destination='list-main',workspace_id='workspace-test'))
    fields.update(changes)
    return app.state.runtime_tasks.create(o,**fields)

def result(t,**changes):
    proposal=RuntimeProposalEnvelope(proposal_id='proposal-test',tool_id='google_tasks',operation='tasks.create',project_id=t.project_id,
        workspace_id=t.scope.workspace_id,resource=t.scope.resource,destination=t.scope.destination,
        parameters={'title':'Synthetic task','due':'2026-10-25T10:00:00+00:00','task_list_id':'list-main'},runtime_risk_hint='LOW')
    fields=dict(task_id=t.task_id,device_id=t.target_device_id,correlation_id=t.correlation_id,result_type='PROPOSAL',proposal=proposal)
    fields.update(changes);return RuntimeResultEnvelope(**fields)
def claimed(b):
    t=task(b);b[0].state.runtime_tasks.claim(b[4],t.task_id,t.target_device_id);return t
def send(b,res):return b[0].state.runtime_tasks.accept(b[4],res.device_id,res.model_dump_json().encode())

def test_happy_path_risk_and_no_authority(boundary):
    t=claimed(boundary);answer=send(boundary,result(t))
    assert answer['task_status']=='WAITING_AUTHORIZATION' and answer['effective_risk']=='HIGH'
    with boundary[1].store.read() as r:
        assert len(r.rows('actions'))==1 and not r.rows('approvals') and not r.rows('execution_authorizations') and not r.rows('jobs')
        assert verify(r)

def test_duplicate_result(boundary):
    t=claimed(boundary);res=result(t)
    assert send(boundary,res)==send(boundary,res)
    with boundary[1].store.read() as r:assert len(r.rows('actions'))==1 and verify(r)

@pytest.mark.parametrize('field,value',[('approved',True),('authorization_id','forged'),('owner_override','owner'),('risk','LOW'),('tool_enabled',True),('kill_switch',False),('owner_id','forged')])
def test_forged_result_fields(boundary,field,value):
    t=claimed(boundary);body=result(t).model_dump(mode='json');body[field]=value
    with pytest.raises(Fault,match='RUNTIME_PROTOCOL_ERROR'):boundary[0].state.runtime_tasks.accept(boundary[4],t.target_device_id,json.dumps(body).encode())
    with boundary[1].store.read() as r:assert not r.rows('actions') and verify(r)

@pytest.mark.parametrize('field,value',[('project_id','other'),('tool_id','invented'),('operation','tasks.delete'),('workspace_id','other'),('resource','other'),('destination','other')])
def test_proposal_binding(boundary,field,value):
    t=claimed(boundary);res=result(t);p=res.proposal.model_copy(update={field:value})
    with pytest.raises(Fault) as caught:send(boundary,res.model_copy(update={'proposal':p}))
    assert caught.value.status==(400 if field=='tool_id' else 403)
    with boundary[1].store.read() as r:assert not r.rows('actions') and verify(r)

def test_parameters_resource_tamper(boundary):
    t=claimed(boundary);res=result(t);p=res.proposal.model_copy(update={'parameters':{**res.proposal.parameters,'task_list_id':'other'}})
    with pytest.raises(Fault):send(boundary,res.model_copy(update={'proposal':p}))
def test_disabled_tool_proposal_not_execution(boundary):
    t=claimed(boundary);assert send(boundary,result(t))['task_status']=='WAITING_AUTHORIZATION'
    with boundary[1].store.read() as r:
        assert not r.get('tools','google_tasks')['enabled']
        assert not r.rows('jobs')
def test_kill_switch_revalidated(boundary):
    t=claimed(boundary)
    with boundary[1].store.transaction() as r:
        row=r.get('system_state','global');row['state']='LOCKED';r.put('system_state','global',row)
    with pytest.raises(Fault,match='CONTROL_BLOCKED'):send(boundary,result(t))
def test_revocation_revalidated(boundary):
    t=claimed(boundary)
    with boundary[1].store.transaction() as r:
        for grant in r.rows('grants'):
            if grant['principal_id']=='luma-runtime' and grant['capability']=='runtime.actions.propose':
                grant['status']='REVOKED';r.put('grants',grant['id'],grant)
    with pytest.raises(Fault):send(boundary,result(t))
def test_expired_result(boundary):
    t=claimed(boundary);boundary[0].state.runtime_tasks.clock=lambda:t.expires_at+timedelta(seconds=1)
    with pytest.raises(Fault,match='TASK_EXPIRED'):send(boundary,result(t))
    with boundary[1].store.read() as r:assert r.get('agent_tasks',t.task_id)['status']=='EXPIRED'
def test_cancelled_result(boundary):
    t=claimed(boundary);boundary[0].state.runtime_tasks.cancel(boundary[3],t.task_id)
    with pytest.raises(Fault,match='TASK_TERMINAL'):send(boundary,result(t))
    with boundary[1].store.read() as r:assert r.get('agent_tasks',t.task_id)['status']=='CANCELLED'
def test_unclaimed_result(boundary):
    t=task(boundary)
    with pytest.raises(Fault,match='TASK_NOT_CLAIMED'):send(boundary,result(t))
def test_registry_stale(boundary):
    t=claimed(boundary)
    with boundary[1].store.transaction() as r:
        row=r.get('tools','google_tasks');row['enabled']=True;r.put('tools','google_tasks',row)
    with pytest.raises(Fault,match='RUNTIME_POLICY_STALE'):send(boundary,result(t))
def test_wrong_device(boundary):
    t=claimed(boundary)
    with pytest.raises(Fault):send(boundary,result(t,device_id='wrong-device'))
def test_device_revoked(boundary):
    t=claimed(boundary);boundary[2].devices.revoke(boundary[3],t.target_device_id)
    with pytest.raises(Fault,match='DEVICE_REVOKED'):send(boundary,result(t))
def test_owner_cannot_impersonate_runtime(boundary):
    t=claimed(boundary)
    with pytest.raises(Fault,match='RUNTIME_IDENTITY_DENIED'):boundary[0].state.runtime_tasks.accept(boundary[3],t.target_device_id,result(t).model_dump_json().encode())
def test_duplicate_task_idempotency(boundary):
    a=task(boundary,key='same-task-key');b=task(boundary,key='same-task-key')
    assert a==b
def test_result_conflict(boundary):
    t=claimed(boundary);send(boundary,result(t))
    with pytest.raises(Fault,match='IDEMPOTENCY_CONFLICT'):send(boundary,result(t,answer='Changed'))
def test_normal_answer(boundary):
    t=claimed(boundary);res=result(t,result_type='ANSWER',proposal=None,answer='Olá')
    assert send(boundary,res)['task_status']=='COMPLETED'
def test_clarification(boundary):
    t=claimed(boundary);res=result(t,result_type='NEEDS_CLARIFICATION',proposal=None,needs_clarification=True)
    assert send(boundary,res)['task_status']=='NEEDS_CLARIFICATION'
def test_runtime_error_domain(boundary):
    t=claimed(boundary);res=result(t,result_type='ERROR',proposal=None,error_code='POLICY_DENIED',runtime_status='FAILED')
    assert send(boundary,res)['task_status']=='POLICY_DENIED'

@pytest.mark.parametrize('path',['/v1/admin/state','/v1/admin/grants','/v1/action-requests/forged/authorize','/v1/jobs'])
def test_runtime_token_has_no_admin_authority(boundary,path):
    app,c,e,o,r,sid=boundary
    with TestClient(app,base_url='http://127.0.0.1') as api:
        response=api.post(path,json={},headers={'Authorization':'Bearer '+c.settings.runtime_token})
        assert response.status_code==403

def test_protocol_roundtrips(boundary):
    t=task(boundary)
    objects=[t,result(t),result(t).proposal,RuntimeHeartbeat(device_id=t.target_device_id,registry_version=t.tool_registry_version,runtime_status='ONLINE'),
        RuntimeErrorEnvelope(task_id=t.task_id,correlation_id=t.correlation_id,code='MODEL_ERROR')]
    for value in objects:assert decode(type(value),value.model_dump_json().encode())==value
def test_protocol_version_rejected(boundary):
    t=task(boundary);body=t.model_dump(mode='json');body['protocol_version']='2'
    with pytest.raises(ValidationError):decode(RemoteTaskEnvelope,json.dumps(body).encode())
def test_payload_limit():
    with pytest.raises(ValueError):decode(RemoteTaskEnvelope,b' '*262145)
def test_context_limit():
    with pytest.raises(ValidationError):ContextEnvelope(messages=('x'*2001,))
def test_result_limit(boundary):
    t=task(boundary)
    with pytest.raises(ValidationError):result(t,answer='x'*4001)
def test_proposal_parameters_limit(boundary):
    t=task(boundary);body=result(t).proposal.model_dump(mode='json');body['parameters']={'title':'x'*2001}
    with pytest.raises(ValidationError):RuntimeProposalEnvelope.model_validate_json(json.dumps(body))
def test_unknown_mode(monkeypatch):
    from backend.modes import mode
    monkeypatch.setenv('LUMA_MODE','WRONG')
    with pytest.raises(ValueError,match='INVALID_LUMA_MODE'):mode()
def test_local_transport_retry_and_dedup(boundary):
    t=task(boundary);calls=[]
    def handler(task):calls.append(task.task_id);return result(task)
    proc=RuntimeTaskProcessor(handler,device_id=t.target_device_id,registry_version=t.tool_registry_version)
    transport=LocalRuntimeTransport(proc);wire=t.model_dump_json().encode()
    assert transport.exchange(wire)==transport.exchange(wire) and calls==[t.task_id]
    assert not any(hasattr(proc,x) for x in ('approve','authorize','grant','unlock','store','control'))
def test_runtime_expired_no_processing(boundary):
    t=task(boundary);calls=[]
    proc=RuntimeTaskProcessor(lambda x:calls.append(x),device_id=t.target_device_id,registry_version=t.tool_registry_version,clock=lambda:t.expires_at)
    with pytest.raises(Fault,match='TASK_EXPIRED'):proc.process(t.model_dump_json().encode())
    assert not calls
def test_runtime_stale_no_processing(boundary):
    t=task(boundary)
    proc=RuntimeTaskProcessor(lambda x:None,device_id=t.target_device_id,registry_version='old')
    with pytest.raises(Fault,match='RUNTIME_POLICY_STALE'):proc.process(t.model_dump_json().encode())
def test_future_remote_fail_closed():
    with pytest.raises(Fault,match='RUNTIME_UNAVAILABLE'):FutureRemoteRuntimeTransport().exchange(b'{}')

def test_control_clean_process_without_local_dependencies(tmp_path):
    url='sqlite:///'+(tmp_path/'clean.db').as_posix();migrate(url)
    code="""import sys,json
from backend.control_plane_app import ControlPlaneSettings,create_control_plane
from fastapi.testclient import TestClient
app=create_control_plane(ControlPlaneSettings.from_env())
with TestClient(app,base_url='http://127.0.0.1') as api:
 assert api.get('/health').json()['mode']=='CONTROL_PLANE'
for prefix in ('google.genai','google.adk','backend.app.adk_bridge','backend.app.knowledge','backend.app.model_provider','backend.runtime_processor','backend.app.orchestration'):
 assert not any(x==prefix or x.startswith(prefix+'.') for x in sys.modules),prefix
print('BOUNDARY_PASS')
"""
    env={k:v for k,v in os.environ.items() if not k.startswith(('LUMA_','GEMINI_'))}
    env.update(PATH='',LUMA_MODE='CONTROL_PLANE',LUMA_OWNER_TOKEN=secrets.token_urlsafe(32),LUMA_DATABASE_URL=url,LUMA_KNOWLEDGE_WORKSPACE=str(tmp_path/'missing'))
    run=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    assert 'BOUNDARY_PASS' in run.stdout

def test_runtime_clean_process_without_canonical_database():
    code="""import sys,json
from backend.local_runtime_app import create_local_runtime
from backend.remote_protocol import RemoteTaskEnvelope,RuntimeResultEnvelope
from datetime import datetime,timezone,timedelta
app=create_local_runtime()
p=app.state.processor
p.handler=lambda t:RuntimeResultEnvelope(task_id=t.task_id,device_id=t.target_device_id,correlation_id=t.correlation_id,answer='safe')
n=datetime.now(timezone.utc)
t=RemoteTaskEnvelope(task_id='t',project_id='meu-gestor',session_id='s',target_device_id='local-dev',correlation_id='c',created_at=n,expires_at=n+timedelta(minutes=1),user_message='Olá',idempotency_key='test-runtime',tool_registry_version='unbound')
assert p.process(t.model_dump_json().encode())
for prefix in ('sqlalchemy','psycopg','backend.app.database','backend.app.trust','backend.app.control','backend.control_plane_app','backend.app.execution'):
 assert not any(x==prefix or x.startswith(prefix+'.') for x in sys.modules),prefix
print('RUNTIME_PASS')
"""
    env={k:v for k,v in os.environ.items() if not k.startswith(('LUMA_','GEMINI_'))};env['LUMA_MODE']='LOCAL_RUNTIME'
    run=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
    assert run.returncode==0,run.stderr

def test_protocol_schema_snapshot():
    classes=(RemoteTaskEnvelope,RuntimeResultEnvelope,RuntimeProposalEnvelope,RuntimeHeartbeat,RuntimeErrorEnvelope)
    expected=json.loads(Path('contracts/RUNTIME_PROTOCOL_V1.json').read_text(encoding='utf-8'))
    assert {c.__name__:c.model_json_schema() for c in classes}==expected

def test_intelligence_transport_proposal_end_to_end(boundary):
    from backend.runtime_processor import IntelligenceHandler
    from backend.app.generation import ModelResult
    from backend.app.model_contracts import ModelDecision,ToolCallProposal,AnswerCitation
    t=claimed(boundary);modes=[]
    class Model:
        def generate(self,context,cid):
            modes.append(context.decision_mode)
            if context.decision_mode=='SECURITY_REVIEW':
                return ModelResult(model_name='synthetic',decision=ModelDecision(assistant_message='Review only',intent='review',confidence=.5,review_recommendation='approve_review',citations=(AnswerCitation(document_id='synthetic',chunk_id='chunk'),)))
            return ModelResult(model_name='synthetic',decision=ModelDecision(assistant_message='Proposal only',intent='proposal',confidence=.5,citations=(AnswerCitation(document_id='synthetic',chunk_id='chunk'),),
                proposed_actions=(ToolCallProposal(tool_id='google_tasks',capability='tasks.create',parameters=result(t).proposal.parameters,reason='Synthetic',correlation_id=cid),)))
    class Knowledge:
        def query(self,request,cid):
            from backend.app.models import KnowledgeContext
            return KnowledgeContext(project_id=request.project_id,brain_version='0.6.0',engine_version='1.4.0',query=request.query,
                results=[],sources=[{'document_id':'synthetic','chunk_id':'chunk'}],warnings=[],permission_status='NOT_DETERMINED_BY_RETRIEVAL',
                request_id='synthetic',correlation_id=cid,status='OK',confidence='HIGH')
    handler=IntelligenceHandler(Model(),Knowledge())
    processor=RuntimeTaskProcessor(handler,device_id=t.target_device_id,registry_version=t.tool_registry_version)
    wire=LocalRuntimeTransport(processor).exchange(t.model_dump_json().encode())
    response=boundary[0].state.runtime_tasks.accept(boundary[4],t.target_device_id,wire)
    assert response['task_status']=='WAITING_AUTHORIZATION'
    assert 'SECURITY_REVIEW' in modes
    with boundary[1].store.read() as r:assert not r.rows('approvals') and not r.rows('execution_authorizations') and verify(r)

@pytest.mark.parametrize('code,expected',[('MODEL_TIMEOUT','MODEL_ERROR'),('KNOWLEDGE_REJECTED','KNOWLEDGE_UNAVAILABLE'),('UNEXPECTED','TECHNICAL_FAILURE')])
def test_runtime_safe_error_classification(boundary,code,expected):
    from backend.runtime_processor import IntelligenceHandler
    t=task(boundary)
    class Failed:
        def generate(self,*a):raise Fault(code,503)
        def query(self,*a):raise Fault(code,503)
    response=IntelligenceHandler(Failed(),Failed())(t)
    assert response.error_code==expected and response.result_type=='ERROR'
    assert code not in response.answer

def test_security_reject_is_not_human_approval(boundary):
    t=claimed(boundary)
    with pytest.raises(Fault,match='POLICY_DENIED'):send(boundary,result(t,security_review='REJECT'))
    with boundary[1].store.read() as r:assert not r.rows('actions') and not r.rows('approvals') and verify(r)

def test_runtime_concurrent_duplicate_one_generation(boundary):
    import threading,time
    from concurrent.futures import ThreadPoolExecutor
    t=task(boundary);calls=[];barrier=threading.Barrier(2)
    def handler(t):calls.append(t.task_id);time.sleep(.05);return result(t)
    processor=RuntimeTaskProcessor(handler,device_id=t.target_device_id,registry_version=t.tool_registry_version)
    def run(_):barrier.wait(timeout=5);return processor.process(t.model_dump_json().encode())
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(run,range(2)))
    assert responses[0]==responses[1] and len(calls)==1

def test_wrong_device_preserves_task_state(boundary):
    t=claimed(boundary)
    with pytest.raises(Fault):send(boundary,result(t,device_id='wrong-device'))
    with boundary[1].store.read() as r:assert r.get('agent_tasks',t.task_id)['status']=='CLAIMED_BY_RUNTIME'

@pytest.mark.parametrize('key',['LUMA_OWNER_TOKEN','LUMA_ADMIN_CONFIRM_TOKEN','LUMA_DATABASE_URL'])
def test_runtime_rejects_authority_credentials(monkeypatch,key):
    from backend.local_runtime_app import create_local_runtime
    monkeypatch.setenv(key,'synthetic-authority-value')
    with pytest.raises(ValueError,match='RUNTIME_AUTHORITY_CREDENTIAL_DENIED'):create_local_runtime()

def test_knowledge_access_revoked_before_result(boundary):
    t=claimed(boundary)
    with boundary[1].store.transaction() as r:
        for g in r.rows('grants'):
            if g['principal_id']=='luma-runtime' and g['capability']=='knowledge.read':
                g['status']='REVOKED';r.put('grants',g['id'],g)
    with pytest.raises(Fault):send(boundary,result(t,result_type='ANSWER',proposal=None,answer='old answer'))
    with boundary[1].store.read() as r:assert not r.rows('actions') and verify(r)

def test_real_local_adk_runtime_clean_process():
    code="""import sys
from datetime import datetime,timezone,timedelta
from backend.local_runtime_app import create_local_runtime
from backend.remote_protocol import RemoteTaskEnvelope,RuntimeResultEnvelope,decode
from backend.app.generation import ModelResult
from backend.app.model_contracts import ModelDecision
class Provider:
 def generate(self,context,cid):return ModelResult(model_name='synthetic-no-network',decision=ModelDecision(assistant_message='Ola',intent='answer',confidence=.5))
 def close(self):pass
app=create_local_runtime(provider=Provider())
n=datetime.now(timezone.utc)
task=RemoteTaskEnvelope(task_id='runtime-adk',project_id='meu-gestor',session_id='session',target_device_id='local-dev',correlation_id='correlation',
 created_at=n,expires_at=n+timedelta(minutes=1),user_message='Oi',idempotency_key='runtime-adk-key',tool_registry_version='unbound')
result=decode(RuntimeResultEnvelope,app.state.processor.process(task.model_dump_json().encode()))
assert result.answer=='Ola' and result.result_type=='ANSWER',result.error_code
assert result.agent_trace_summary[0].agent_id=='luma'
for prefix in ('sqlalchemy','psycopg','backend.app.database','backend.app.control','backend.app.trust','backend.app.execution'):
 assert not any(x==prefix or x.startswith(prefix+'.') for x in sys.modules),prefix
print('REAL_ADK_RUNTIME_NO_DATABASE_PASS')
"""
    env={k:v for k,v in os.environ.items() if not k.startswith(('LUMA_','GEMINI_')) and k not in ('DATABASE_URL','PGPASSWORD')}
    env['LUMA_MODE']='LOCAL_RUNTIME'
    run=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=60)
    assert run.returncode==0,run.stderr
    assert 'REAL_ADK_RUNTIME_NO_DATABASE_PASS' in run.stdout

@pytest.mark.parametrize('attack',['execution_claim','local_secret','invented_citation'])
def test_runtime_blocks_unsafe_model_answer(boundary,attack):
    from types import SimpleNamespace
    from backend.runtime_processor import IntelligenceHandler
    from backend.app.generation import ModelResult
    from backend.app.model_contracts import ModelDecision,AnswerCitation
    t=task(boundary,message='Oi')
    secret='synthetic-local-model-credential'
    class Provider:
        config=SimpleNamespace(api_key=secret)
        def generate(self,context,cid):
            answer='executei' if attack=='execution_claim' else secret if attack=='local_secret' else 'Resposta'
            return ModelResult(model_name='synthetic',decision=ModelDecision(assistant_message=answer,intent='answer',confidence=.5,
                citations=(AnswerCitation(document_id='invented',chunk_id='missing'),) if attack=='invented_citation' else ()))
    response=IntelligenceHandler(Provider())(t)
    assert response.error_code=='MODEL_ERROR'
    assert secret not in response.model_dump_json()
