import uuid,time
from pathlib import Path
from datetime import timedelta
import pytest
from backend.app.errors import Fault
from backend.research.contracts import *
from backend.research.policy import *
from backend.research.runtime import ResearchProcessor
from backend.research.provider import MockWebResearchProvider,GeminiGoogleSearchProvider,normalize_interaction
from backend.tests.research_support import build,create,HEADERS

@pytest.fixture
def research(monkeypatch):
    monkeypatch.setenv('LUMA_ENV','test');path=Path('runtime')/('research-test-'+uuid.uuid4().hex+'.db')
    app,c,clock,d,send=build('sqlite:///'+path.resolve().as_posix())
    yield app,c,clock,d,send
    c.__exit__(None,None,None);app.state.control.close();path.unlink(missing_ok=True)

def request(query='Versão atual do React?',**kw):
    return ResearchRequest(research_id=uuid.uuid4().hex,project_id='meu-gestor',query=query,route=KnowledgeRouter().route(query),target_device_id=uuid.uuid4().hex,requested_at=int(time.time()),expires_at=int(time.time())+240,**kw)

@pytest.mark.parametrize('query,route',[('Como funciona fotossíntese?','WEB_FIRST'),('Qual a versão mais recente do React?','WEB_REQUIRED'),('Como a autenticação da LUMA está implementada?','PROJECT_FIRST'),('Existe vulnerabilidade atual do React usado na LUMA?','HYBRID_WEB_PROJECT'),('Reescreva esta mensagem.','NO_RETRIEVAL'),('Pesquise o significado de API','WEB_REQUIRED'),('Não pesquise na internet sobre React','NO_RETRIEVAL'),('Minha biblioteca privada','PRIVATE_LIBRARY_FUTURE')])
def test_router(query,route):assert KnowledgeRouter().route(query).route==route

@pytest.mark.parametrize('query',['api_key: syntheticsecret','Bearer synthetic','password=abc','D:\\project\\private.txt','postgresql'+':'+'//'+'user'+':'+'secret'+'@host/db','contato@example.com','documento interno confidencial','```secret```','AIza'+'a'*35],ids=['key-assignment','bearer','password-assignment','local-path','database-uri','email','private-content','code-fence','google-key-synthetic'])
def test_egress_blocks(query):
    with pytest.raises(Fault):ExternalQueryPolicy().check(query)

@pytest.mark.parametrize('url',['javascript:alert(1)','file:///etc/passwd','http://localhost/','http://127.0.0.1','http://10.0.0.1','http://169.254.169.254','http://[::1]/','http://[fc00::1]/','http://user:pass@example.com','https://example.com/?token=secret','http://2130706433/'])
def test_unsafe_url(url):
    with pytest.raises(Fault):URLPolicy().check(url)

def test_dns_private_rebinding(monkeypatch):
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**kw:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(Fault):URLPolicy().check('https://public.example.com',resolve=True)

def test_source_dedup_and_no_invented_date():
    p=SourceRankingPolicy();a=p.normalize('https://react.dev/?utm_source=x','React',1,'test');b=p.normalize('https://react.dev/','React',1,'test')
    assert a.source_id==b.source_id and a.published_at is None and a.source_type=='OFFICIAL'
    assert p.normalize('https://unknown.example.org/','Unknown',1,'test').source_type=='UNKNOWN'

def test_no_real_call_before_cost_gate():
    p=GeminiGoogleSearchProvider('synthetic')
    with pytest.raises(Fault) as e:p.search(request())
    assert e.value.code=='RESEARCH_COST_GATE_REQUIRED' and p.calls==0

def test_runtime_no_authority_import():
    import subprocess,sys
    code="import backend.research.runtime,research_agent.client,sys;assert not any(x in sys.modules for x in ('sqlalchemy','psycopg','backend.app.trust','backend.control_plane_app'))"
    assert subprocess.run([sys.executable,'-c',code],capture_output=True).returncode==0

def test_project_sovereignty_no_provider_calls():
    p=MockWebResearchProvider();r=ResearchProcessor(p,lambda req:('Internal fact',['doc:chunk'])).process(request('Como a LUMA funciona?'))
    assert r.project_answer=='Internal fact' and r.answer=='' and p.calls==0

def test_hybrid_separates_private_context():
    p=MockWebResearchProvider();r=ResearchProcessor(p,lambda req:('Internal fact',['doc:chunk'])).process(request('Vulnerabilidade atual da LUMA?',public_query='React security advisories'))
    assert r.project_answer=='Internal fact' and r.sources and p.calls==1

def test_cache_and_realtime():
    p=MockWebResearchProvider();engine=ResearchProcessor(p);req=request('Como funciona React?')
    engine.process(req);engine.process(req.model_copy(update={'research_id':uuid.uuid4().hex}));assert p.calls==1
    req=req.model_copy(update={'route':KnowledgeRouter().route('React agora?')});engine.process(req);engine.process(req);assert p.calls==3

def test_freshness_unavailable():
    class Down(MockWebResearchProvider):
        def search(self,r):raise Fault('WEB_RESEARCH_UNAVAILABLE',503)
    r=ResearchProcessor(Down()).process(request());assert r.status=='FAILED' and r.answer=='' and r.error_code=='FRESHNESS_UNAVAILABLE'

def test_invalid_citation_and_extra_thought():
    r=MockWebResearchProvider().search(request()).model_dump();r['citations'][0]['source_id']='invented'
    with pytest.raises(ValueError):ResearchResult.model_validate(r)
    r=MockWebResearchProvider().search(request()).model_dump();r['thought']='hidden'
    with pytest.raises(ValueError):ResearchResult.model_validate(r)

def test_roundtrip_no_effectful_authority(research):
    a,c,t,d,send=research;r=create(c,d);assert r.status_code==200,r.text
    rid=r.json()['research_id'];polled=send('poll',{}).json();req=ResearchRequest.model_validate(polled['request']);result=MockWebResearchProvider().search(req)
    done=send('result',{'research_id':rid,'lease_id':polled['lease_id'],'result':result.model_dump()});assert done.status_code==200,done.text
    assert c.get('/v1/research/'+rid,headers=HEADERS).json()['status']=='COMPLETED'
    assert send('result',{'research_id':rid,'lease_id':polled['lease_id'],'result':result.model_dump()}).status_code==409
    with a.state.control.store.read() as repo:
        assert all(not repo.rows(x) for x in ('actions','approvals','execution_authorizations','jobs','learning'))

def test_idempotency(research):
    a,c,t,d,send=research;key=uuid.uuid4().hex
    x=create(c,d,idempotency_key=key);y=create(c,d,idempotency_key=key);assert x.json()['research_id']==y.json()['research_id']
    assert create(c,d,idempotency_key=key,query='Other question').status_code==409

def test_atomic_poll_single_delivery(research):
    a,c,t,d,send=research;create(c,d)
    assert send('poll',{}).json()['request'] and send('poll',{}).json()['request'] is None

@pytest.mark.parametrize('action',['cancel','kill','revoke','expire'])
def test_late_result_denied(research,action):
    a,c,t,d,send=research;rid=create(c,d).json()['research_id'];polled=send('poll',{}).json();result=MockWebResearchProvider().search(ResearchRequest.model_validate(polled['request']))
    if action=='cancel':assert c.post('/v1/research/'+rid+'/cancel',headers=HEADERS).status_code==200
    if action=='expire':t[0]+=timedelta(seconds=241)
    if action=='revoke':assert c.post('/v1/devices/'+d['device_id']+'/revoke',headers=HEADERS,json={}).status_code==200
    if action=='kill':
        with a.state.control.store.transaction() as r:
            s=r.get('system_state','global');s['state']='STOPPED';r.put('system_state','global',s)
    assert send('result',{'research_id':rid,'lease_id':polled['lease_id'],'result':result.model_dump()}).status_code in (403,409)

def test_offline_no_fallback_and_expiry(research):
    a,c,t,d,send=research;t[0]+=timedelta(seconds=50);r=create(c,d);assert r.json()['status']=='WAITING_FOR_DEVICE'
    assert send('poll',{}).json()['request'] is None
    t[0]+=timedelta(seconds=241);assert c.get('/v1/research/'+r.json()['research_id'],headers=HEADERS).json()['status']=='FAILED'

def test_project_and_credential_separation(research):
    a,c,t,d,send=research;assert create(c,d,project_id='other-project').status_code in (403,404)
    assert c.post('/v1/research-runtime/poll',headers=HEADERS,json={}).status_code==401
    assert c.get('/v1/research/devices').status_code==401

def test_capability_required(research):
    a,c,t,d,send=research
    assert c.post('/v1/research/devices/'+d['device_id']+'/capability',headers=HEADERS,json={'enabled':False}).status_code==200
    assert create(c,d).status_code==403

def test_voice_contracts_advisory_only():
    from backend.voice_contracts import AgentContribution,VoiceSessionIntent,CollaborationPlan
    with pytest.raises(ValueError):AgentContribution(agent_id='security',kind='CONCLUSION',content='ok',authority='APPROVE')
    with pytest.raises(ValueError):VoiceSessionIntent(provider='GEMINI_LIVE',session_id='s',enabled=True)
    assert CollaborationPlan(mode='PARALLEL').approval_authority=='NONE'


def test_device_project_must_match_request_even_for_owner(research):
    a,c,t,d,send=research
    with a.state.control.store.transaction() as repo:
        device=repo.get('device_identities',d['device_id']);device['project_id']='other-project';repo.put('device_identities',d['device_id'],device)
    assert create(c,d).status_code==403


def test_google_live_delivery_never_persists_and_refresh_does_not_research(research):
    import json
    from backend.tests.google_display_support import google_result,HTML,ANSWER,URL
    a,c,t,d,send=research;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json();result=google_result(ResearchRequest.model_validate(lease['request']))
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    assert c.get('/v1/research/'+rid+'/sources',headers=HEADERS).json()==[]
    one=c.get('/v1/research/'+rid,headers=HEADERS);assert one.headers['cache-control']=='no-store'
    assert one.json()['result']['provider_display_artifact']['search_suggestions_html']==[HTML]
    again=c.get('/v1/research/'+rid,headers=HEADERS).json();assert again['result'] is None and again['display_status']=='GROUNDED_RESULT_NOT_RETAINED'
    assert send('poll',{}).json()['request'] is None
    with a.state.control.store.read() as repo:
        persisted=json.dumps([repo.rows(x) for x in ('research_requests','audit_events','learning','actions','jobs')])
        assert all(x not in persisted for x in (HTML,ANSWER,URL,'Ephemeral title marker'))
        row=repo.rows('research_requests')[0];assert row['usage_metadata']['usage']['search_queries']==1

def test_arbitrary_owner_html_rejected_before_runtime(research):
    a,c,t,d,send=research
    assert create(c,d,provider_display_artifact={'search_suggestions_html':['<script>malicious</script>']}).status_code==400

def test_transient_delivery_owner_scope_and_expiration():
    from backend.research.transient import TransientDisplay
    store=TransientDisplay(ttl=0.02);store.put('id','owner',{'payload':'ONLY_MEMORY'})
    assert store.consume('id','other') is None
    time.sleep(.04);assert store.consume('id','owner') is None and not store._items


def test_google_failed_reply_ends_request_with_original_error_without_artifact(research):
    a,c,t,d,send=research
    rid=create(c,d).json()['research_id'];lease=send('poll',{}).json()
    result=ResearchResult(research_id=rid,status='FAILED',error_code='RESEARCH_ATTRIBUTION_NAVIGATION_UNSUPPORTED',provider='gemini_google_search',model='gemini-3.8-flash',usage=Usage(model_calls=1,search_queries=2,input_tokens=95,output_tokens=128),completed_at=int(time.time()))
    response=send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()})
    assert response.status_code==200,response.text
    row=c.get('/v1/research/'+rid,headers=HEADERS).json()
    assert row['status']=='FAILED' and row['error_code']=='RESEARCH_ATTRIBUTION_NAVIGATION_UNSUPPORTED'
    assert row['result'] is None
    assert row['usage_metadata']['usage']['search_queries']==2
    assert send('poll',{}).json()['request'] is None


def test_google_completed_reply_still_requires_original_suggestions(research):
    from backend.tests.google_display_support import google_result
    a,c,t,d,send=research
    rid=create(c,d).json()['research_id'];lease=send('poll',{}).json()
    result=google_result(ResearchRequest.model_validate(lease['request'])).model_copy(update={'provider_display_artifact':None})
    response=send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()})
    assert response.status_code==400 and response.json()['error']['code']=='RESEARCH_ATTRIBUTION_UNAVAILABLE'
