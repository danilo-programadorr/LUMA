import secrets,json
import pytest
from backend.tests.test_conversation import bundle
from backend.app.agent_team import route,validate_route,ROLES,AgentRouteProposal
from backend.app.errors import Fault
from backend.app.adk_bridge import worker_environment

def task(bundle,message='Qual o estado atual do Meu Gestor?',**extra):
    api,_,_,_,sid=bundle
    return api.post('/v1/tasks',json={**dict(project_id='meu-gestor',session_id=sid,message=message),**extra},headers={'Idempotency-Key':secrets.token_hex(12)})

def test_adk_real_workflow_fake_model(bundle):
    r=task(bundle,'Planeje como implementar uma melhoria na interface')
    assert r.status_code==200,r.text
    assert r.json()['route']['requested_agents']==['product','development']
    w=bundle[0].get('/v1/workflows/'+r.json()['workflow_run_id']).json()
    assert w['root_agent']=='luma' and w['model_calls']==4 and w['agent_calls']==4 and w['status']=='COMPLETED'
    assert len(bundle[3].inputs)==4
    assert all(x.available_tools==() and x.knowledge for x in bundle[3].inputs)
    assert len({x.session_id for x in bundle[3].inputs})==4

def test_registry(bundle):
    agents=bundle[0].get('/v1/agents').json()
    assert {x['agent_id'] for x in agents}==set(ROLES)
    assert all(x['status']=='ENABLED_LOCAL' for x in agents)

@pytest.mark.parametrize('message,agents',[('Analise a segurança do Meu Gestor',['security']),('Melhoria na interface',['product']),('Planeje como implementar X',['product','development']),('Revise a implementação',['qa','security']),('Estratégia de lançamento',['growth','content']),('KPIs e dados',['data']),('Planeje tarefa Codex',['codex'])])
def test_routes(message,agents):assert list(route(message,'meu-gestor','c').requested_agents)==agents

@pytest.mark.parametrize('field,value',[('authorized',True),('requested_agents',['unknown']),('max_output_tokens',99999),('project_id','other')])
def test_client_authority_denied(bundle,field,value):assert task(bundle,**{field:value}).status_code in (400,403,404)

def test_adk_environment_no_secrets(monkeypatch):
    for k in ['LUMA_OWNER_TOKEN','GEMINI_API_KEY','LUMA_RUNTIME_TOKEN','DATABASE_URL']:monkeypatch.setenv(k,'synthetic-forbidden')
    assert all(v!='synthetic-forbidden' for v in worker_environment().values())

def test_disabled_agent(bundle):
    c=bundle[0].app.state.control
    with c.store.transaction() as repo:
        row=repo.get('agents','security');row['status']='DISABLED';repo.put('agents','security',row)
    assert task(bundle,'Analise segurança').status_code==403
    assert not bundle[3].inputs


def test_fanout_fanin(bundle):
    response=task(bundle,'Criar estratégia de lançamento')
    assert response.status_code==200,response.text
    row=bundle[0].get('/v1/workflows/'+response.json()['workflow_run_id']).json()
    assert row['participating_agents']==['luma','growth','content','luma'] and row['agent_calls']==4

@pytest.mark.parametrize('roles,depth',[(('unknown',),1),(('product','product'),2),(('product','qa','security','development'),5)])
def test_route_limits(bundle,roles,depth):
    with bundle[0].app.state.control.store.read() as repo:
        proposal=AgentRouteProposal(requested_agents=roles,reason_code='GENERAL',project_id='other' if len(roles)==4 else 'meu-gestor',correlation_id='c',max_depth=depth,task_classification='GENERAL')
        with pytest.raises(Fault):validate_route(repo,proposal,'meu-gestor')
