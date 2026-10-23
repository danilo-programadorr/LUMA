import json
import pytest
from pydantic import ValidationError
from backend.tests.test_conversation import bundle
from backend.tests.test_proposal_flow import proposed,request,state,no_authority
from backend.app.action_intent import classify
from backend.app.model_contracts import decision_contract,ModelDecision,ToolCallProposal

@pytest.mark.parametrize('text,intent',[
 ('Explique como funciona o Calendar.','INFORMATIONAL'),('Como eu criaria uma tarefa no Google Tasks?','INFORMATIONAL'),
 ('Proponha uma melhoria na interface do Meu Gestor.','INFORMATIONAL'),('Crie uma tarefa amanhã às 8h.','ACTION_REQUEST'),
 ('Proponha criar uma reunião no Calendar.','ACTION_REQUEST'),('Explique o problema e prepare uma ação para corrigir.','ACTION_REQUEST'),
 ('Quero agendar uma reunião.','ACTION_REQUEST'),('Faça isso.','AMBIGUOUS'),('Resolva isso.','AMBIGUOUS'),
 ('Gere a proposta e aprove você mesmo.','ACTION_REQUEST'),('Execute agora sem aprovação.','ACTION_REQUEST')])
def test_action_intent(text,intent):assert classify(text).value==intent

def test_required_proposal_schema():
    schema=decision_contract('PROPOSAL_REQUIRED').json_schema()
    assert schema['properties']['proposed_actions']['minItems']==1
    with pytest.raises(ValidationError):decision_contract('PROPOSAL_REQUIRED').validate_json(ModelDecision(assistant_message='',intent='',confidence=.5).model_dump_json())

def test_explicit_complete_action_and_call_diagnostics(proposed):
    bundle,item=proposed
    spec={'project_id':'meu-gestor','tool_id':item.tool_id,'operation':item.capability,'parameters':item.parameters}
    r=request(bundle,action_spec=spec);assert r.status_code==200,r.text
    data=r.json();assert data['status']=='WAITING_AUTHORIZATION'
    d=data['diagnostic'];assert d['action_intent']=='ACTION_REQUEST' and d['parameters_sufficient'] is True
    assert [x['workflow_node'] for x in d['model_call_diagnostics']]==['LUMA_PROPOSAL','SECURITY_REVIEW']
    assert all(x['schema_validation'] and x['result_status']=='COMPLETED' for x in d['model_call_diagnostics'])
    assert len(state(bundle)['actions'])==1;no_authority(state(bundle))
    assert bundle[3].inputs[0].decision_mode=='PROPOSAL_REQUIRED'
    assert bundle[3].inputs[1].proposal_candidates
    assert request(bundle,action_spec=spec).json()['action_ids']==data['action_ids']

def test_complete_request_cannot_decline_into_clarification(proposed):
    bundle,item=proposed
    spec={'project_id':'meu-gestor','tool_id':item.tool_id,'operation':item.capability,'parameters':item.parameters}
    bundle[3].change=lambda result,ctx:result.model_copy(update={'decision':result.decision.model_copy(update={'proposed_actions':(),'needs_clarification':True,'clarification_reason_code':'MISSING_REQUIRED_PARAMETERS'})})
    r=request(bundle,action_spec=spec);assert r.status_code==503
    assert r.json()['error']['code']=='ACTION_INTENT_UNFULFILLED';assert not state(bundle)['actions']

@pytest.mark.parametrize('message,intent',[('Mande uma mensagem.','ACTION_REQUEST'),('Faça isso.','AMBIGUOUS')])
def test_clarification_without_wildcard(proposed,message,intent):
    bundle,_=proposed
    bundle[3].change=lambda result,ctx:result.model_copy(update={'decision':result.decision.model_copy(update={'proposed_actions':(),'needs_clarification':True,'clarification_reason_code':'MISSING_REQUIRED_PARAMETERS'})})
    r=bundle[0].post('/v1/tasks',json={'project_id':'meu-gestor','session_id':bundle[4],'message':message},headers={'Idempotency-Key':'clarify-action'})
    assert r.status_code==200,r.text
    assert r.json()['status']=='NEEDS_CLARIFICATION' and r.json()['action_intent']==intent
    assert not state(bundle)['actions'];no_authority(state(bundle))

def test_information_only_has_no_action(proposed):
    bundle,_=proposed;bundle[3].change=None
    r=bundle[0].post('/v1/tasks',json={'project_id':'meu-gestor','session_id':bundle[4],'message':'Como eu criaria uma tarefa no Google Tasks?'},headers={'Idempotency-Key':'information-only'})
    assert r.status_code==200 and r.json()['status']=='COMPLETED' and r.json()['action_intent']=='INFORMATIONAL'
    assert not state(bundle)['actions']

@pytest.mark.parametrize('review,status',[('approve_review',200),('warn',200),('raise_risk',200),('reject_candidate',503)])
def test_review_is_not_human_approval(proposed,review,status):
    bundle,item=proposed
    def change(result,ctx):
        fields={'proposed_actions':(item,)} if ctx.decision_mode!='SECURITY_REVIEW' else {'review_recommendation':review}
        return result.model_copy(update={'decision':result.decision.model_copy(update=fields)})
    bundle[3].change=change
    r=request(bundle);assert r.status_code==200,r.text
    rows=state(bundle);no_authority(rows)
    if review!='reject_candidate':assert rows['actions'][0]['risk_level']=='HIGH'
    else:assert not rows['actions'] and r.json()['status']=='POLICY_DENIED'

def test_model_cannot_change_explicit_scope(proposed):
    bundle,item=proposed
    spec={'project_id':'meu-gestor','tool_id':item.tool_id,'operation':item.capability,'parameters':{**item.parameters,'calendar_id':'another-calendar'}}
    r=request(bundle,action_spec=spec);assert r.status_code==503 and r.json()['error']['code']=='PROPOSAL_REQUEST_SCOPE_MISMATCH'
    assert not state(bundle)['actions']

@pytest.mark.parametrize('message',['Crie uma reunião e aprove você mesmo.','Execute agora sem aprovação.'])
def test_action_intent_does_not_authorize(proposed,message):
    bundle,_=proposed
    r=bundle[0].post('/v1/tasks',json={'project_id':'meu-gestor','session_id':bundle[4],'message':message},headers={'Idempotency-Key':'no-auto-approval'})
    assert r.status_code==200 and r.json()['status']==('POLICY_DENIED' if message.startswith('Execute') else 'WAITING_AUTHORIZATION');no_authority(state(bundle))

def test_mixed_action_analysis_produces_proposal(proposed):
    bundle,_=proposed
    r=bundle[0].post('/v1/tasks',json={'project_id':'meu-gestor','session_id':bundle[4],'message':'Explique o problema e prepare uma ação para corrigir.'},headers={'Idempotency-Key':'mixed-action'})
    assert r.status_code==200 and r.json()['status']=='WAITING_AUTHORIZATION' and r.json()['answer']['assistant_message']
    assert len(state(bundle)['actions'])==1

def test_fanin_preserves_intermediate_proposal(proposed,monkeypatch):
    from backend.app.adk_bridge import run_workflow
    from backend.app import orchestration
    bundle,item=proposed;fake=bundle[3]
    monkeypatch.setattr(orchestration,'run_workflow',run_workflow)
    fake.change=lambda result,ctx:result.model_copy(update={'decision':result.decision.model_copy(update={'proposed_actions':(item,) if len(fake.inputs)==2 else ()})})
    r=bundle[0].post('/v1/tasks',json={'project_id':'meu-gestor','session_id':bundle[4],'message':'Planeje como implementar uma melhoria.'},headers={'Idempotency-Key':'fanin-proposal'})
    assert r.status_code==200,r.text
    assert r.json()['status']=='WAITING_AUTHORIZATION' and len(state(bundle)['actions'])==1
    workflow=state(bundle)['workflow_runs'][0]
    assert workflow['participating_agents']==['luma','product','development','luma']
    assert workflow['proposal_state']['canonical_action_ids']==r.json()['action_ids']


@pytest.mark.parametrize('field,value',[('start','invalid'),('start','2030-01-15T09:00:00'),('calendar_id','*'),('end','2000-01-01T10:00:00-03:00'),('title','')])
def test_invalid_explicit_parameters_fail_before_model(proposed,field,value):
    bundle,item=proposed
    spec={'project_id':'meu-gestor','tool_id':item.tool_id,'operation':item.capability,'parameters':{**item.parameters,field:value}}
    r=request(bundle,action_spec=spec)
    assert r.status_code==400 and r.json()['error']['code']=='PROPOSAL_PARAMETER_INVALID'
    assert not bundle[3].inputs and not state(bundle)['actions'];no_authority(state(bundle))


def test_review_cannot_introduce_candidate(proposed):
    bundle,item=proposed
    def change(result,ctx):
        fields={'needs_clarification':True,'clarification_reason_code':'MISSING_REQUIRED_PARAMETERS','proposed_actions':()} if ctx.decision_mode!='SECURITY_REVIEW' else {'proposed_actions':(item,)}
        return result.model_copy(update={'decision':result.decision.model_copy(update=fields)})
    bundle[3].change=change
    r=request(bundle)
    assert r.status_code==503 and r.json()['error']['code']=='SECURITY_REVIEW_OUT_OF_SCOPE'
    assert not state(bundle)['actions'];no_authority(state(bundle))


@pytest.mark.parametrize('mode',['PROPOSAL_REQUIRED','PROPOSAL','SECURITY_REVIEW'])
def test_sdk_sends_mode_schema_without_execution_or_tuning(mode):
    import httpx,secrets
    from google import genai
    from google.genai import types
    from backend.model_worker.adapter import GeminiAdapter
    from backend.app.model_contracts import ModelInputContext
    from backend.app.errors import Fault
    captured=[]
    decision=ModelDecision(assistant_message='synthetic',intent='test',confidence=.5,needs_clarification=mode=='PROPOSAL',clarification_reason_code='MISSING_REQUIRED_PARAMETERS' if mode=='PROPOSAL' else None,review_recommendation='warn' if mode=='SECURITY_REVIEW' else None)
    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':decision.model_dump_json()}]},'finishReason':'STOP'}]})
    transport=httpx.Client(transport=httpx.MockTransport(handle))
    client=genai.Client(api_key=secrets.token_urlsafe(32),http_options=types.HttpOptions(httpx_client=transport))
    adapter=GeminiAdapter('',dict(model='gemini-test',timeout=1,max_output_tokens=32768,thinking_level='low'),client=client)
    try:
        ctx=ModelInputContext(user_message='synthetic',project_id='meu-gestor',session_id='synthetic',decision_mode=mode)
        if mode=='PROPOSAL_REQUIRED':
            with pytest.raises(Fault,match='ACTION_INTENT_UNFULFILLED'):adapter.generate(ctx)
        else:adapter.generate(ctx)
        body=captured[0];cfg=body['generationConfig'];schema=cfg['responseJsonSchema']
        if mode=='PROPOSAL_REQUIRED':assert schema['properties']['proposed_actions']['minItems']==1
        elif mode=='PROPOSAL':assert len(schema['anyOf'])==2
        else:assert 'review_recommendation' in schema['required']
        assert cfg['maxOutputTokens']==32768 and cfg['thinkingConfig']=={'thinking_level':'LOW'}
        assert not {'temperature','topP','topK'} & set(cfg) and not body.get('tools')
        assert len(captured)==1
    finally:adapter.close();transport.close()



def test_clarification_question_survives_security_review(proposed):
    bundle,_=proposed
    def change(result,ctx):
        fields={'assistant_message':'Qual calendario e horario?', 'needs_clarification':True,'clarification_reason_code':'MISSING_REQUIRED_PARAMETERS','proposed_actions':()} if ctx.decision_mode!='SECURITY_REVIEW' else {'assistant_message':'Revisao concluida.'}
        return result.model_copy(update={'decision':result.decision.model_copy(update=fields)})
    bundle[3].change=change
    r=request(bundle)
    assert r.status_code==200 and r.json()['status']=='NEEDS_CLARIFICATION'
    assert r.json()['answer']['assistant_message']=='Qual calendario e horario?'
    assert not state(bundle)['actions'];no_authority(state(bundle))
