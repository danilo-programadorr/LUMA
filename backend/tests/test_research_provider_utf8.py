import json
from types import SimpleNamespace
import pytest
from google.genai._gaos.types.interactions.textcontent import TextContent
from backend.app.errors import Fault
from backend.research.provider import normalize_interaction,GeminiGoogleSearchProvider,ResearchProviderSettings
from backend.tests.test_research_provider import req,data


def sdk_block(text,segment):
    start=text.index(segment);end=start+len(segment)
    return TextContent(text=text,annotations=[{'type':'url_citation','url':'https://react.dev/','title':'Synthetic official fixture','start_index':len(text[:start].encode('utf-8')),'end_index':len(text[:end].encode('utf-8'))}]).model_dump(mode='json',exclude_none=True)


@pytest.mark.parametrize('text,segment',[('A versão estável é pública.','versão estável'),('Evidência científica 🚀 confirmada.','científica 🚀'),('Ação e precisão.','Ação e precisão.')])
def test_sdk_utf8_citation_offsets_become_exact_character_ranges(text,segment):
    d=data();d['steps'][-1]['content']=[sdk_block(text,segment)]
    result=normalize_interaction(d,req(),'gemini_google_search','synthetic',1,'google_search')
    citation=result.citations[0]
    assert result.answer==text
    assert result.answer[citation.start_index:citation.end_index]==segment
    assert result.provider_display_artifact.search_suggestions_html==[d['steps'][2]['result'][0]['search_suggestions']]


def test_sdk_utf8_offsets_are_relative_to_each_text_block():
    d=data();d['steps'][-1]['content']=[sdk_block('Olá. ','Olá'),sdk_block('A versão estável 🚀.','versão estável 🚀')]
    result=normalize_interaction(d,req(),'gemini_google_search','synthetic',1,'google_search')
    assert result.answer=='Olá. A versão estável 🚀.'
    assert [result.answer[c.start_index:c.end_index] for c in result.citations]==['Olá','versão estável 🚀']


@pytest.mark.parametrize('field',['start_index','end_index'])
def test_optional_sdk_offset_is_rejected_explicitly_without_inventing_ranges(field):
    d=data();block=sdk_block('Ação pública.','Ação');block['annotations'][0].pop(field);d['steps'][-1]['content']=[block]
    with pytest.raises(Fault) as caught:normalize_interaction(d,req(),'gemini_google_search','synthetic',1,'google_search')
    assert caught.value.code=='RESEARCH_CITATION_OFFSETS_MISSING'


def test_invalid_utf8_boundary_is_rejected_without_rewriting_text():
    d=data();block=sdk_block('Ação pública.','Ação');block['annotations'][0]['end_index']=2;d['steps'][-1]['content']=[block]
    with pytest.raises(Fault) as caught:normalize_interaction(d,req(),'gemini_google_search','synthetic',1,'google_search')
    assert caught.value.code=='RESEARCH_CITATION_RANGE_INVALID'


def test_generic_failure_records_only_bounded_stage_and_kind(monkeypatch):
    import backend.research.provider as module
    secret='PRIVATE_PAYLOAD_MUST_NOT_BE_LOGGED'
    def fail(*args):raise TypeError(secret)
    monkeypatch.setattr(module,'normalize_interaction',fail)
    class Interaction:
        def create(self,**kw):return SimpleNamespace(model_dump=lambda **_:data())
    p=GeminiGoogleSearchProvider('synthetic',ResearchProviderSettings(real_calls_approved=True,attribution_approved=True,max_session_calls=1),SimpleNamespace(interactions=Interaction()))
    with pytest.raises(Fault):p.search(req())
    assert p.last_usage['failure_stage']=='NORMALIZATION'
    assert p.last_usage['error_kind']=='SHAPE'
    assert secret not in json.dumps(p.last_usage) and p.acceptance_halted and p.calls==1


def test_ledger_persists_only_allowlisted_diagnostic_metadata(tmp_path):
    from backend.research.acceptance import AcceptanceLedger
    l=AcceptanceLedger(tmp_path/'ledger.json');n=l.reserve('synthetic')
    l.finish(n,{'failure_stage':'NORMALIZATION','error_kind':'SCHEMA','exception_message':'NEVER_STORE','raw_response':'NEVER_STORE'},'RESEARCH_PROVIDER_ERROR')
    row=json.loads(l.path.read_text())['calls'][0]
    assert row['failure_stage']=='NORMALIZATION' and row['error_kind']=='SCHEMA'
    assert 'NEVER_STORE' not in json.dumps(row)
    l2=AcceptanceLedger(tmp_path/'other.json');n=l2.reserve('synthetic')
    l2.finish(n,{'failure_stage':'UNTRUSTED_SECRET','error_kind':'UNTRUSTED_SECRET'},'RESEARCH_PROVIDER_ERROR')
    assert 'UNTRUSTED_SECRET' not in l2.path.read_text()
