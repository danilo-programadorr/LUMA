import json,secrets
from datetime import timedelta
import pytest,httpx
from fastapi.testclient import TestClient
from backend.tests.test_conversation import bundle,FakeModelProvider
from backend.tests.test_model_worker import config,context,result
from backend.app.model_contracts import ToolCallProposal
from backend.app.errors import Fault
from backend.app.database import Repository
from backend.app.models import now
from backend.app import orchestration
from backend.app.main import create_app
from backend.app.knowledge import KnowledgeClient
from backend.tests.test_foundation import transport
from backend.app.trust_data import verify

@pytest.fixture
def proposed(bundle,monkeypatch):
    def workflow(roles,generate):
        for i,role in enumerate(roles):generate(role['agent_id'],i)
        return {'agent_calls':len(roles),'workflow_latency_ms':1}
    monkeypatch.setattr(orchestration,'run_workflow',workflow)
    item=ToolCallProposal(tool_id='google_calendar',capability='calendar.create',parameters={'title':'synthetic','start':'2030-01-15T09:00:00-03:00','end':'2030-01-15T10:00:00-03:00','time_zone':'America/Sao_Paulo','calendar_id':'synthetic-calendar'},reason='proposal',correlation_id='untrusted-model-id')
    bundle[3].change=lambda result,ctx:result.model_copy(update={'decision':result.decision.model_copy(update={'proposed_actions':() if ctx.decision_mode=='SECURITY_REVIEW' else (item,)})})
    return bundle,item

def request(bundle,key='proposal-request-key',**extra):
    return bundle[0].post('/v1/tasks',json=dict(project_id='meu-gestor',session_id=bundle[4],message='Proponha uma reunião sem executar.',**extra),headers={'Idempotency-Key':key})

def state(bundle):
    with bundle[0].app.state.control.store.read() as r:
        assert verify(r)
        return {table:r.rows(table) for table in ('agent_tasks','workflow_runs','actions','approvals','execution_authorizations','jobs','execution_records')}

def no_authority(rows):
    assert all(not rows[t] for t in ('approvals','execution_authorizations','jobs','execution_records'))

def test_legitimate_disabled_tool_and_backend_risk(proposed):
    bundle,_=proposed;r=request(bundle);assert r.status_code==200,r.text
    rows=state(bundle);assert len(rows['actions'])==1;action=rows['actions'][0]
    assert action['risk_level']=='HIGH' and action['origin_type']=='AGENT_PROPOSED'
    assert action['principal_id']=='local-owner' and action['envelope']['project_id']=='meu-gestor'
    assert action['correlation_id']==r.headers['x-correlation-id'] and action['action_id'] in r.json()['action_ids']
    assert rows['agent_tasks'][0]['status']=='WAITING_AUTHORIZATION'
    assert rows['workflow_runs'][0]['status']=='COMPLETED'
    d=r.json()['diagnostic'];assert d['proposal_emitted'] and d['proposal_count']==1
    assert d['action_request_created'] and d['action_request_persisted'] and d['transaction_committed']
    assert d['tool_enabled'] is False and d['last_completed_stage']=='transaction_commit'
    no_authority(rows)

@pytest.mark.parametrize('field,value,code',[('tool_id','unknown','PROPOSAL_TOOL_UNKNOWN'),('capability','tasks.create','PROPOSAL_CAPABILITY_DENIED'),('capability','admin.approve','PROPOSAL_SCHEMA_INVALID')])
def test_invalid_tool_capability_schema(proposed,field,value,code):
    bundle,item=proposed
    bundle[3].change=lambda result,ctx:result.model_copy(update={'decision':result.decision.model_copy(update={'proposed_actions':(item.model_copy(update={field:value}),)})})
    response=request(bundle);assert response.status_code==503 and response.json()['error']['code']==code
    rows=state(bundle);assert not rows['actions'];no_authority(rows)

@pytest.mark.parametrize('field',['approved','authorized','owner','execute_now','risk_level','authorization_id','approval_id','grant','kill_switch','project_id','effective_risk','requested_risk'])
def test_forbidden_parameter(proposed,field):
    bundle,item=proposed
    item.parameters[field]=True
    response=request(bundle);assert response.status_code==503 and response.json()['error']['code'] in ('PROPOSAL_PARAMETER_INVALID','SENSITIVE_PAYLOAD')
    rows=state(bundle);assert not rows['actions'];no_authority(rows)

def test_project_mismatch(proposed):
    bundle,_=proposed
    response=bundle[0].post('/v1/tasks',json={'project_id':'other','session_id':bundle[4],'message':'Proposta'},headers={'Idempotency-Key':'project-mismatch'})
    assert response.status_code in (403,404);assert not state(bundle)['actions']

@pytest.mark.parametrize('point,code',[('actions','ACTION_REQUEST_PERSIST_FAILED'),('agent_tasks','ACTION_REQUEST_COMMIT_FAILED')])
def test_transaction_rollback(proposed,monkeypatch,point,code):
    bundle,_=proposed;original=Repository.add if point=='actions' else Repository.put
    def fail(repo,table,key,data):
        if table==point and (point=='actions' or data.get('status')=='WAITING_AUTHORIZATION'):raise RuntimeError('secret-do-not-expose')
        return original(repo,table,key,data)
    monkeypatch.setattr(Repository,'add' if point=='actions' else 'put',fail)
    response=request(bundle);assert response.status_code==503,response.text
    assert response.json()['error']['code']==code and 'secret-do-not-expose' not in response.text
    rows=state(bundle);assert not rows['actions'];assert rows['agent_tasks'][0]['diagnostic']['transaction_committed'] is False;no_authority(rows)

def test_serialization_failure_before_commit(proposed,monkeypatch):
    bundle,_=proposed
    def fail(value):raise TypeError('secret-output')
    monkeypatch.setattr(orchestration,'serialize_response',fail)
    response=request(bundle);assert response.json()['error']['code']=='RESPONSE_SERIALIZATION_FAILED'
    rows=state(bundle);assert not rows['actions'];no_authority(rows)

def test_response_failure_after_commit_retry_restart(proposed,monkeypatch):
    bundle,_=proposed;api,cfg,model,fake,sid=bundle;original=orchestration.deliver_response
    def fail(value):raise Fault('RESPONSE_SERIALIZATION_FAILED',503)
    monkeypatch.setattr(orchestration,'deliver_response',fail)
    assert request(bundle).status_code==503
    rows=state(bundle);assert len(rows['actions'])==1 and rows['agent_tasks'][0]['status']=='WAITING_AUTHORIZATION'
    monkeypatch.setattr(orchestration,'deliver_response',original)
    response=request(bundle);assert response.status_code==200 and len(fake.inputs)==2
    assert response.json()['action_ids']==[rows['actions'][0]['action_id']]
    other=FakeModelProvider();app=create_app(cfg,KnowledgeClient(cfg,httpx.MockTransport(transport)),other,model)
    with TestClient(app,base_url='http://127.0.0.1',headers={'Authorization':'Bearer '+cfg.token}) as client:
        retry=client.post('/v1/tasks',json={'project_id':'meu-gestor','session_id':sid,'message':'Proponha uma reunião sem executar.'},headers={'Idempotency-Key':'proposal-request-key'})
        assert retry.status_code==200 and retry.json()==response.json() and not other.inputs
    assert len(state(bundle)['actions'])==1;no_authority(state(bundle))

def test_later_failure_discards_earlier_proposals(proposed,monkeypatch):
    bundle,_=proposed
    def interrupted(roles,generate):
        generate('luma',0);raise Fault('WORKFLOW_BUDGET_EXCEEDED',503)
    monkeypatch.setattr(orchestration,'run_workflow',interrupted)
    assert request(bundle).status_code==503
    rows=state(bundle);assert not rows['actions'];no_authority(rows)

def test_owner_approval_is_separate_and_tool_remains_disabled(proposed):
    bundle,_=proposed;r=request(bundle);aid=r.json()['action_ids'][0];e=bundle[0].app.state.execution;p=e.control.principal()
    spec=dict(valid_from=now().isoformat(),expires_at=(now()+timedelta(minutes=5)).isoformat(),max_executions=1,confirmation='AUTHORIZE_EXACT_ACTION')
    with pytest.raises(Fault,match='TOOL_DISABLED'):e.authorize(p,aid,spec,'owner-disabled-approval','approval',True)
    for actor in ('luma-runtime','luma-executor'):
        with pytest.raises(Fault):e.authorize(e.control.principal(actor),aid,spec,'not-owner-approval','approval',True)
    # Future enabled-tool state is synthetic only; no adapter or effect exists.
    with e.store.transaction() as repo:
        tool=repo.get('tools','google_calendar');tool['enabled']=True;repo.put('tools','google_calendar',tool)
    auth=e.authorize(p,aid,spec,'owner-later-approval','approval',True)
    assert auth['status']=='ACTIVE' and not state(bundle)['jobs']

def test_missing_proposal_is_not_persistence_failure(proposed):
    bundle,_=proposed;bundle[3].change=None
    r=request(bundle);assert r.status_code==503 and r.json()['error']['code']=='ACTION_INTENT_UNFULFILLED'
    d=state(bundle)['agent_tasks'][0]['diagnostic']
    assert not d['action_request_created'] and not d['action_request_persisted']

def test_duplicate_proposals_from_roles_deduplicated(proposed,monkeypatch):
    bundle,_=proposed
    def repeated(roles,generate):
        generate('luma',0);generate('luma',1)
        return {'agent_calls':2,'workflow_latency_ms':1}
    monkeypatch.setattr(orchestration,'run_workflow',repeated)
    r=request(bundle);assert r.status_code==200 and r.json()['diagnostic']['proposal_count']==2
    assert len(state(bundle)['actions'])==1

def test_provider_schema_observation_sanitized(config):
    from google import genai
    from google.genai import types
    from backend.model_worker.adapter import GeminiAdapter
    from backend.app.provider_diagnostics import valid_metadata
    data=result().decision.model_dump(mode='json')
    data['proposed_actions']=[dict(tool_id='google_calendar',capability='secret-unregistered-value',parameters={},reason='sensitive-reason',correlation_id='x')]
    transport=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':json.dumps(data)}]},'finishReason':'STOP'}]})))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,max_output_tokens=32768,thinking_level='low'),client=client)
    try:
        with pytest.raises(Fault,match='MODEL_INVALID_RESPONSE'):adapter.generate(context())
        d=adapter.metadata;assert valid_metadata(d)
        assert d['proposal_observation']=={'proposal_emitted':True,'proposal_count':1,'proposal_schema_valid':False,'schema_error_fields':['proposal.capability:value_error']}
        assert 'secret-unregistered-value' not in json.dumps(d) and 'sensitive-reason' not in json.dumps(d)
    finally:adapter.close();transport.close()

def test_full_real_suite_requires_isolated_same_candidate(tmp_path,monkeypatch):
    from backend import validate_adk as v
    monkeypatch.setattr(v,'ROOT',tmp_path);(tmp_path/'reports').mkdir()
    assert v.run()==2
    (tmp_path/'reports/FASE_7E_ADK_LEGITIMATE_PROPOSAL_REAL.json').write_text(json.dumps({'status':'PASSED','candidate_hash':'stale'}))
    assert v.run()==2


def test_adk_specialist_proposal_survives_root_synthesis(proposed,monkeypatch):
    from backend.app.adk_bridge import run_workflow
    bundle,item=proposed;fake=bundle[3]
    monkeypatch.setattr(orchestration,'run_workflow',run_workflow)
    def change(result,ctx):
        return result.model_copy(update={'decision':result.decision.model_copy(update={'proposed_actions':(item,) if len(fake.inputs)==2 else ()})})
    fake.change=change
    response=bundle[0].post('/v1/tasks',json={'project_id':'meu-gestor','session_id':bundle[4],'message':'Analise segurança do projeto.'},headers={'Idempotency-Key':'specialist-proposal'})
    assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_AUTHORIZATION'
    assert len(fake.inputs)==3 and len(state(bundle)['actions'])==1
    assert state(bundle)['actions'][0]['origin_id']=='security'
    no_authority(state(bundle))

@pytest.mark.parametrize('field',['approved','authorized','owner','execute_now','risk_level','authorization_id','approval_id','grant','kill_switch'])
def test_model_proposal_cannot_define_authority_fields(field):
    from pydantic import ValidationError
    data=dict(tool_id='google_calendar',capability='calendar.create',parameters={},reason='',correlation_id='')
    data[field]=True
    with pytest.raises(ValidationError):ToolCallProposal.model_validate_json(json.dumps(data))


@pytest.mark.parametrize('proposal_invalid,stage,code',[(True,'proposal_schema_validation','PROPOSAL_SCHEMA_INVALID'),(False,'model_decision_parsed','MODEL_INVALID_RESPONSE')])
def test_trace_distinguishes_proposal_and_decision_errors(proposal_invalid,stage,code):
    from backend.app.proposal_flow import Trace
    from backend.app.provider_diagnostics import empty_metadata
    trace=Trace();metadata=empty_metadata()
    metadata.update(provider_status=200,response_received=True,finish_reason='STOP',schema_validation=False,proposal_observation={'proposal_emitted':True,'proposal_count':1,'proposal_schema_valid':False if proposal_invalid else None,'schema_error_fields':['proposal.capability:value_error' if proposal_invalid else 'decision.confidence:float_type']})
    trace.provider({'provider':metadata,'failure_stage':'schema validation'})
    assert trace.failure(Fault('MODEL_INVALID_RESPONSE',503))==code
    assert trace.data['failure_stage']==stage and trace.data['model_decision_valid'] is False
