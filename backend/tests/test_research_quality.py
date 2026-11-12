import json
from types import SimpleNamespace
import pytest
from google.genai._gaos.types.interactions.usage import Usage as SDKUsage
from backend.app.errors import Fault
from backend.research.provider import normalize_interaction,GeminiGoogleSearchProvider,ResearchProviderSettings
from backend.tests.test_research_provider import req,data

COUNTERS={'thought_tokens':'total_thought_tokens','tool_use_tokens':'total_tool_use_tokens','total_tokens':'total_tokens','cached_tokens':'total_cached_tokens'}

def provider_call(request,payload):
    captured={}
    class Interaction:
        def create(self,**kw):captured.update(kw);return SimpleNamespace(model_dump=lambda **_:payload)
    provider=GeminiGoogleSearchProvider('synthetic',ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=1),SimpleNamespace(interactions=Interaction()))
    return provider,provider.search(request),captured


def test_sdk_internal_numeric_usage_reaches_result_and_failure_telemetry():
    d=data();d['usage']=SDKUsage(total_input_tokens=90,total_output_tokens=20,total_thought_tokens=12,total_tool_use_tokens=40,total_tokens=162,total_cached_tokens=5).model_dump(mode='json',exclude_none=True)
    p,result,_=provider_call(req(),d)
    for name,value in {'input_tokens':90,'output_tokens':20,'thought_tokens':12,'tool_use_tokens':40,'total_tokens':162,'cached_tokens':5}.items():
        assert getattr(result.usage,name,'MISSING')==value and p.last_usage.get(name)==value
    assert 'DO_NOT_PERSIST' not in result.model_dump_json()


@pytest.mark.parametrize('zero',[False,True])
def test_absent_internal_counts_stay_unknown_and_zero_is_not_lost(zero):
    d=data();d['usage']={sdk:0 for sdk in COUNTERS.values()} if zero else {}
    result=normalize_interaction(d,req(),'gemini_google_search','synthetic',1,'google_search')
    for field in COUNTERS:assert getattr(result.usage,field,'MISSING')==(0 if zero else None)


@pytest.mark.parametrize('sdk',['total_input_tokens','total_output_tokens',*COUNTERS.values()])
@pytest.mark.parametrize('bad',[-1,True,'PRIVATE_COUNTER_PAYLOAD'])
def test_non_numeric_or_negative_token_counters_fail_closed(sdk,bad):
    d=data();d['usage']={sdk:bad}
    with pytest.raises(Fault) as e:normalize_interaction(d,req(),'gemini_google_search','synthetic',1,'google_search')
    assert e.value.code=='RESEARCH_PROVIDER_USAGE_INVALID'


def test_plain_text_and_official_source_request_reach_sdk_without_rewriting_artifact():
    request=req().model_copy(update={'query':'Pesquise na documentação oficial do Python a compreensão de listas.'})
    d=data();d['steps'][-1]['content'][0]['text']='**React evidence**';d['steps'][-1]['content'][0]['annotations'][0]['end_index']=18
    p,result,captured=provider_call(request,d);instruction=captured['system_instruction'].lower()
    assert 'plain text' in instruction and 'no markdown' in instruction
    assert 'official documentation only' in instruction
    assert 'annotations' in instruction and 'do not repeat' in instruction
    assert captured['generation_config']=={'max_output_tokens':2000,'thinking_level':'low','thinking_summaries':'none'}
    assert captured['store'] is False
    assert result.answer=='**React evidence**'
    assert result.provider_display_artifact.search_suggestions_html==[d['steps'][2]['result'][0]['search_suggestions']]
    assert len(result.citations)==1


def test_prompt_never_includes_private_query_when_public_query_present():
    marker='PRIVATE_PROJECT_MARKER_NOT_FOR_PROVIDER'
    request=req().model_copy(update={'query':marker,'public_query':'Segundo a documentação oficial do Python, para que serve uma lista?'})
    p,result,captured=provider_call(request,data())
    assert marker not in json.dumps(captured)
    assert json.loads(captured['input'])['public_question']==request.public_query
    assert 'official documentation only' in captured['system_instruction'].lower()


def test_official_request_does_not_upgrade_redirect_title_to_source_authority():
    request=req().model_copy(update={'query':'Pesquise na documentação oficial do Python.'})
    d=data();d['steps'][-1]['content'][0]['annotations'][0].update(url='https://vertexaisearch.cloud.google.com/grounding-api-redirect/synthetic-only',title='Official Python Documentation')
    p,result,captured=provider_call(request,d)
    assert result.sources[0].source_type=='UNKNOWN' and result.sources[0].publisher is None


def test_ledger_keeps_only_numeric_usage_and_never_thought_content(tmp_path):
    from backend.research.acceptance import AcceptanceLedger
    l=AcceptanceLedger(tmp_path/'ledger.json');n=l.reserve('synthetic')
    l.finish(n,{'thought_tokens':12,'tool_use_tokens':40,'total_tokens':162,'cached_tokens':0,'thought':'PRIVATE_THOUGHT_TEXT','summary':'PRIVATE_THOUGHT_TEXT'})
    row=json.loads(l.path.read_text())['calls'][0]
    assert all(row.get(k)==v for k,v in {'thought_tokens':12,'tool_use_tokens':40,'total_tokens':162,'cached_tokens':0}.items())
    assert 'PRIVATE_THOUGHT_TEXT' not in l.path.read_text()
    l2=AcceptanceLedger(tmp_path/'invalid.json');n=l2.reserve('synthetic');l2.finish(n,{'input_tokens':'PRIVATE_COUNTER_PAYLOAD','thought_tokens':'PRIVATE_COUNTER_PAYLOAD'})
    assert 'PRIVATE_COUNTER_PAYLOAD' not in l2.path.read_text()


@pytest.mark.parametrize('alias,field',[('input_tokens','input_tokens'),('output_tokens','output_tokens'),('thoughts_tokens','thought_tokens'),('tool_use_input_tokens','tool_use_tokens'),('cached_tokens','cached_tokens')])
def test_documented_numeric_aliases_are_supported_without_inference(alias,field):
    from backend.research.usage import read_token_usage
    assert read_token_usage({alias:7})[field]==7


def test_conflicting_numeric_aliases_are_rejected():
    from backend.research.usage import read_token_usage
    with pytest.raises(Fault) as e:read_token_usage({'total_thought_tokens':3,'thoughts_tokens':4})
    assert e.value.code=='RESEARCH_PROVIDER_USAGE_INVALID'


def test_failed_normalization_keeps_numeric_internal_usage_without_payload(monkeypatch):
    import backend.research.provider as module
    from backend.research.runtime import ResearchProcessor
    def reject(*args):raise Fault('RESEARCH_CITATION_RANGE_INVALID',502)
    monkeypatch.setattr(module,'normalize_interaction',reject)
    d=data();d['usage']={'total_input_tokens':10,'total_output_tokens':5,'total_thought_tokens':3,'total_tool_use_tokens':40,'total_tokens':58}
    class Interaction:
        def create(self,**kw):return SimpleNamespace(model_dump=lambda **_:d)
    provider=GeminiGoogleSearchProvider('synthetic',ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=1),SimpleNamespace(interactions=Interaction()))
    result=ResearchProcessor(provider).process(req())
    assert result.status=='FAILED' and result.usage.thought_tokens==3 and result.usage.tool_use_tokens==40 and result.usage.total_tokens==58
    assert 'DO_NOT_PERSIST' not in result.model_dump_json()


def test_malformed_tool_step_keeps_received_numeric_usage():
    from backend.research.runtime import ResearchProcessor
    d=data();d['usage']={'total_input_tokens':10,'total_output_tokens':5,'total_thought_tokens':3,'total_tool_use_tokens':40,'total_tokens':58,'total_cached_tokens':0}
    d['steps']=[{'type':'google_search_call','arguments':None}]
    class Interaction:
        def create(self,**kw):return SimpleNamespace(model_dump=lambda **_:d)
    provider=GeminiGoogleSearchProvider('synthetic',ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=1),SimpleNamespace(interactions=Interaction()))
    result=ResearchProcessor(provider).process(req())
    assert result.status=='FAILED' and result.error_code=='RESEARCH_PROVIDER_RESPONSE_INVALID'
    assert provider.last_usage['response_received'] is True
    assert result.usage.input_tokens==10 and result.usage.output_tokens==5 and result.usage.thought_tokens==3 and result.usage.tool_use_tokens==40 and result.usage.total_tokens==58 and result.usage.cached_tokens==0
    assert result.usage.search_queries is None
