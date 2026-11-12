import hashlib,json,importlib
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path
import pytest
from backend.app.errors import Fault
from backend.research.acceptance import AcceptanceLedger,REQUIRED
from backend.research.provider import GeminiGoogleSearchProvider,ResearchProviderSettings
from backend.tests.test_research_provider import req,data

CASES=[{'case_id':'public_scientific','query':'O que a NASA explica sobre as causas de um eclipse lunar? Responda brevemente com fonte.','urls':[],'tool':'google_search'}, {'case_id':'public_url_context','query':'Explique brevemente a compreensão de listas da página pública selecionada e cite essa página.','urls':['https://docs.python.org/3/tutorial/datastructures.html'],'tool':'url_context'}]
CASES.append({'case_id':'public_multi_source','query':'Pesquise como se diferenciam eclipses lunares totais e parciais segundo fontes públicas da NASA e do ESO. Cite as fontes e reconheça incertezas.','urls':[],'tool':'google_search'})

@pytest.fixture
def final_workspace(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);Path('runtime').mkdir();Path('reports').mkdir()
    legacy=AcceptanceLedger();
    for _ in range(6):n=legacy.reserve('synthetic');legacy.finish(n,{})
    legacy.edit(lambda d:d.update(halted=True,stop_reason='AUTHORIZED_MODEL_CALL_LIMIT_REACHED'))
    before=legacy.path.read_bytes();Path('candidate.txt').write_text('candidate')
    gate={'status':'PASS_OWNER_AUTHORIZED','acceptance_profile':'FINAL_THREE','maximum_calls':3,'owner_approval_required':True,'owner_approval_granted':True,'legacy_ledger_sha256':hashlib.sha256(before).hexdigest(),'cases':CASES,'criteria':{**dict.fromkeys(REQUIRED,'PASS'),'AUDIT':'VERIFIED','SECRET_SCAN':'PASSED'},'candidate_files':{'candidate.txt':hashlib.sha256(Path('candidate.txt').read_bytes()).hexdigest()}}
    Path('reports/FASE_7F_D_A_FINAL_THREE_PRECHECK.json').write_text(json.dumps(gate))
    return legacy,before

def module():
    try:return importlib.import_module('backend.research.final_acceptance')
    except ModuleNotFoundError:pytest.fail('Final-two guarded profile not implemented')

def request_for(case=0):return req().model_copy(update={'query':CASES[case]['query'],'urls':CASES[case]['urls']})


def test_final_provider_without_owner_approval_never_dispatches(final_workspace):
    cfg=ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=2,acceptance_profile='FINAL_THREE',final_three_owner_approved=False)
    class Interaction:
        calls=0
        def create(self,**kw):self.calls+=1;return SimpleNamespace(model_dump=lambda **_:data())
    fake=Interaction();p=GeminiGoogleSearchProvider('synthetic',cfg,SimpleNamespace(interactions=fake));p._real_transport=True
    with pytest.raises(Fault) as e:p.search(request_for())
    assert e.value.code=='RESEARCH_FINAL_APPROVAL_REQUIRED' and fake.calls==0 and p.calls==0
    assert not Path('runtime/research-google-final-three-usage.json').exists()


def test_catalog_is_exact_and_status_does_not_create_live_ledger(final_workspace):
    m=module();assert m.case_catalog()==CASES
    assert m.final_status()['remaining_calls']==3
    assert not Path('runtime/research-google-final-three-usage.json').exists()


@pytest.mark.parametrize('mutation',['query','tool','urls','public_query','project','private_route'])
def test_other_case_or_scope_is_blocked_before_reservation(final_workspace,mutation):
    m=module();request=request_for();tool='google_search'
    if mutation=='query':request=request.model_copy(update={'query':'Outra pergunta pública'})
    elif mutation=='tool':tool='url_context'
    elif mutation=='urls':request=request.model_copy(update={'urls':['https://example.org/']})
    elif mutation=='public_query':request=request.model_copy(update={'public_query':request.query})
    elif mutation=='project':request=request.model_copy(update={'project_id':'another-project'})
    else:request=request.model_copy(update={'route':request.route.model_copy(update={'route':'HYBRID_WEB_PROJECT'})})
    with pytest.raises(Fault) as e:m.prepare_final_acceptance(request,tool,True)
    assert e.value.code=='RESEARCH_FINAL_CASE_NOT_APPROVED'
    assert not Path('runtime/research-google-final-three-usage.json').exists()


@pytest.mark.parametrize('mutation',['candidate','legacy','cases','status','maximum'])
def test_changed_precheck_or_legacy_fails_closed(final_workspace,mutation):
    m=module();p=Path('reports/FASE_7F_D_A_FINAL_THREE_PRECHECK.json');d=json.loads(p.read_text())
    if mutation=='candidate':Path('candidate.txt').write_text('changed')
    elif mutation=='legacy':Path('runtime/research-google-acceptance-usage.json').write_text('{}')
    elif mutation=='cases':d['cases']=[]
    elif mutation=='status':d['status']='PASS_WITHOUT_OWNER_GATE'
    else:d['maximum_calls']=6
    p.write_text(json.dumps(d))
    with pytest.raises(Fault):m.validate_final_gate()
    assert not Path('runtime/research-google-final-three-usage.json').exists()


def test_two_distinct_cases_survive_restarts_and_preserve_old_six(final_workspace):
    m=module();legacy,before=final_workspace
    for i in range(2):
        ledger,case=m.prepare_final_acceptance(request_for(i),CASES[i]['tool'],True)
        n=ledger.reserve_case('gemini-3.8-flash',case);assert n==i+1
        ledger.finish(n,{'response_received':True,'search_queries':1 if i==0 else 0,'thought_tokens':3})
    ledger=m.FinalThreeLedger();d=json.loads(ledger.path.read_text());assert d['maximum_calls']==3 and len(d['calls'])==2
    with pytest.raises(Fault):ledger.reserve_case('gemini-3.8-flash','public_scientific')
    assert legacy.path.read_bytes()==before


def test_duplicate_case_never_consumes_second_attempt(final_workspace):
    m=module();ledger,case=m.prepare_final_acceptance(request_for(),'google_search',True)
    n=ledger.reserve_case('gemini-3.8-flash',case);ledger.finish(n,{})
    with pytest.raises(Fault) as e:m.FinalThreeLedger().reserve_case('gemini-3.8-flash',case)
    assert e.value.code=='RESEARCH_FINAL_CASE_ALREADY_ATTEMPTED'
    assert len(json.loads(ledger.path.read_text())['calls'])==1


def test_failure_stops_final_round_without_reopening_legacy(final_workspace):
    m=module();ledger,case=m.prepare_final_acceptance(request_for(),'google_search',True)
    n=ledger.reserve_case('gemini-3.8-flash',case);ledger.finish(n,{},'RESEARCH_PROVIDER_ERROR')
    with pytest.raises(Fault) as e:m.FinalThreeLedger().reserve_case('gemini-3.8-flash','public_url_context')
    assert e.value.code=='RESEARCH_REVALIDATION_REQUIRED'
    assert final_workspace[0].path.read_bytes()==final_workspace[1]


def test_competing_duplicate_case_has_one_reservation(final_workspace):
    m=module();ledger,case=m.prepare_final_acceptance(request_for(),'google_search',True)
    def reserve(_):
        try:return m.FinalThreeLedger().reserve_case('gemini-3.8-flash',case)
        except Fault:return None
    with ThreadPoolExecutor(2) as pool:rows=list(pool.map(reserve,range(2)))
    assert sum(x==1 for x in rows)==1 and len(json.loads(ledger.path.read_text())['calls'])==1


def test_sdk_url_context_shape_and_internal_usage():
    from google.genai._gaos.types.interactions.urlcontextresultstep import URLContextResultStep
    from backend.research.provider import normalize_interaction
    request=request_for(1);d=data();d['steps']=[URLContextResultStep(call_id='synthetic-url',result=[{'url':CASES[1]['urls'][0],'status':'success'}]).model_dump(mode='json',exclude_none=True),d['steps'][-1]]
    d['steps'][-1]['content'][0]['annotations'][0]['url']=CASES[1]['urls'][0]
    d['usage']={'total_thought_tokens':3,'total_tool_use_tokens':40,'total_tokens':100}
    result=normalize_interaction(d,request,'gemini_google_search','synthetic',1,'url_context')
    assert result.usage.search_queries==0 and result.usage.url_context_urls==1
    assert result.usage.thought_tokens==3 and result.usage.tool_use_tokens==40
    assert result.provider_display_artifact is None


def test_approved_profile_uses_separate_ledger_and_stops_after_two_mock_dispatches(final_workspace):
    m=module();captured=[]
    class Interaction:
        def create(self,**kw):
            captured.append(kw);payload=data()
            if kw['tools']==[{'type':'url_context'}]:
                from google.genai._gaos.types.interactions.urlcontextresultstep import URLContextResultStep
                payload['steps']=[URLContextResultStep(call_id='synthetic-url',result=[{'url':CASES[1]['urls'][0],'status':'success'}]).model_dump(mode='json',exclude_none=True),payload['steps'][-1]]
                payload['steps'][-1]['content'][0]['annotations'][0]['url']=CASES[1]['urls'][0]
            payload['usage']={'total_thought_tokens':3,'total_tool_use_tokens':40,'total_tokens':100}
            return SimpleNamespace(model_dump=lambda **_:payload)
    cfg=ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=2,acceptance_profile='FINAL_THREE',final_three_owner_approved=True)
    p=GeminiGoogleSearchProvider('synthetic',cfg,SimpleNamespace(interactions=Interaction()));p._real_transport=True
    p.url=SimpleNamespace(check=lambda url,resolve=False:url)
    assert p.search(request_for()).status=='COMPLETED' and not p.acceptance_halted
    assert p.inspect_urls(request_for(1)).status=='COMPLETED' and not p.acceptance_halted
    assert len(captured)==p.calls==2 and all(c['store'] is False for c in captured)
    rows=json.loads(m.FinalThreeLedger().path.read_text())['calls']
    assert [c['case_id'] for c in rows]==['public_scientific','public_url_context']
    assert all(c['thought_tokens']==3 and c['tool_use_tokens']==40 for c in rows)
    assert final_workspace[0].path.read_bytes()==final_workspace[1]
    with pytest.raises(Fault):p.search(request_for())
    assert len(captured)==2


def test_unapproved_case_cannot_trigger_dns_or_sdk_dispatch(final_workspace):
    cfg=ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=2,acceptance_profile='FINAL_THREE',final_three_owner_approved=True)
    def forbidden(*args,**kwargs):pytest.fail('Unapproved case reached external boundary')
    p=GeminiGoogleSearchProvider('synthetic',cfg,SimpleNamespace(interactions=SimpleNamespace(create=forbidden)));p._real_transport=True;p.url=SimpleNamespace(check=forbidden)
    with pytest.raises(Fault):p.inspect_urls(request_for().model_copy(update={'urls':['https://example.org/']}))
    assert p.calls==0 and not Path('runtime/research-google-final-three-usage.json').exists()


def test_unresolved_attempt_blocks_second_case_and_restart(final_workspace):
    m=module();ledger,case=m.prepare_final_acceptance(request_for(),'google_search',True)
    ledger.reserve_case('gemini-3.8-flash',case)
    status=m.final_status();assert status['halted'] and status['unresolved_attempt']
    with pytest.raises(Fault) as e:m.FinalThreeLedger().reserve_case('gemini-3.8-flash','public_url_context')
    assert e.value.code=='RESEARCH_FINAL_ATTEMPT_UNRESOLVED'
    assert len(json.loads(ledger.path.read_text())['calls'])==1
    assert final_workspace[0].path.read_bytes()==final_workspace[1]


def test_owner_authorized_third_cap_and_fourth_attempt_is_blocked(final_workspace):
    m=module();ledger_class=getattr(m,'FinalThreeLedger',None)
    assert ledger_class is not None and ledger_class.maximum_calls==3
    assert len(m.case_catalog())==3
    for c in m.case_catalog():
        ledger=ledger_class();n=ledger.reserve_case('gemini-3.8-flash',c['case_id']);ledger.finish(n,{})
    assert len(json.loads(ledger_class().path.read_text())['calls'])==3
    with pytest.raises(Fault) as e:ledger_class().reserve_case('gemini-3.8-flash','public_scientific')
    assert e.value.code=='RESEARCH_BUDGET_EXCEEDED'
    assert final_workspace[0].path.read_bytes()==final_workspace[1]


def test_superseded_two_call_ledger_cannot_add_budget(final_workspace):
    m=module();Path('runtime/research-google-final-two-usage.json').write_text(json.dumps({'maximum_calls':2,'calls':[{'status':'COMPLETED'}]}))
    with pytest.raises(Fault):m.validate_final_gate()
    assert not Path('runtime/research-google-final-three-usage.json').exists()


def test_gate_requires_the_new_owner_authorization(final_workspace):
    m=module();p=Path('reports/FASE_7F_D_A_FINAL_THREE_PRECHECK.json');d=json.loads(p.read_text());d['owner_approval_granted']=False;p.write_text(json.dumps(d))
    with pytest.raises(Fault):m.validate_final_gate()


def test_three_mock_model_calls_stop_at_authorized_cap(final_workspace):
    m=module();captured=[]
    class Interaction:
        def create(self,**kw):
            captured.append(kw);payload=data()
            if kw['tools']==[{'type':'url_context'}]:
                from google.genai._gaos.types.interactions.urlcontextresultstep import URLContextResultStep
                payload['steps']=[URLContextResultStep(call_id='synthetic-url',result=[{'url':CASES[1]['urls'][0],'status':'success'}]).model_dump(mode='json',exclude_none=True),payload['steps'][-1]]
                payload['steps'][-1]['content'][0]['annotations'][0]['url']=CASES[1]['urls'][0]
            return SimpleNamespace(model_dump=lambda **_:payload)
    cfg=ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=3,acceptance_profile='FINAL_THREE',final_three_owner_approved=True)
    p=GeminiGoogleSearchProvider('synthetic',cfg,SimpleNamespace(interactions=Interaction()));p._real_transport=True;p.url=SimpleNamespace(check=lambda url,resolve=False:url)
    p.search(request_for());p.inspect_urls(request_for(1));p.search(request_for(2))
    assert p.acceptance_halted and len(captured)==3
    with pytest.raises(Fault):p.search(request_for())
    assert len(captured)==3 and final_workspace[0].path.read_bytes()==final_workspace[1]


def test_optional_third_waits_for_both_required_cases(final_workspace):
    m=module();ledger=m.FinalThreeLedger()
    with pytest.raises(Fault) as e:ledger.reserve_case('gemini-3.8-flash','public_multi_source')
    assert e.value.code=='RESEARCH_FINAL_OPTIONAL_CASE_NOT_READY' and not ledger.path.exists()
    n=ledger.reserve_case('gemini-3.8-flash','public_scientific');ledger.finish(n,{})
    with pytest.raises(Fault):m.FinalThreeLedger().reserve_case('gemini-3.8-flash','public_multi_source')
    assert len(json.loads(ledger.path.read_text())['calls'])==1
