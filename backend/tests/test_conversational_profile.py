"""Conversational generation profile, wire config and bounded local telemetry."""
import json
import pytest,httpx
from dataclasses import replace
from google import genai
from google.genai import types
from backend.app.model_config import ModelSettings
from backend.app.generation import ModelUsage,usage_alerts
from backend.model_worker.adapter import GeminiAdapter
from backend.app.errors import Fault
from backend.tests.test_model_worker import config,context,result
from backend.tests.test_conversation import bundle,turn

@pytest.mark.parametrize('finish',['STOP','MAX_TOKENS'])
def test_sdk_profile_usage_and_structured_output(config,finish):
    captured=[]
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':result().decision.model_dump_json()}]},'finishReason':finish}], 'usageMetadata':{'promptTokenCount':7000,'candidatesTokenCount':300,'thoughtsTokenCount':8500}})
    transport=httpx.Client(transport=httpx.MockTransport(handler))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,profile=config.profile,thinking_level=config.thinking_level,max_output_tokens=config.max_output_tokens),client=client)
    try:
        if finish=='STOP':
            response=adapter.generate(context())
            assert response.usage==ModelUsage(input_tokens=7000,output_tokens=300,thought_tokens=8500)
        else:
            with pytest.raises(Fault,match='MODEL_OUTPUT_TRUNCATED'):adapter.generate(context())
        body=captured[0];generation=body['generationConfig']
        # SDK 2.32 emits the proto field spelling, accepted by ProtoJSON.
        assert generation['thinkingConfig']=={'thinking_level':'LOW'}
        assert generation['maxOutputTokens']==32768
        assert not {'temperature','topP','topK'} & set(generation)
        assert generation['responseMimeType']=='application/json'
        assert generation.get('responseJsonSchema')
        assert not body.get('tools')
        assert len(captured)==1
        assert adapter.metadata['usage']['thought_tokens']==8500
        assert adapter.metadata['usage_alerts']==['HIGH_MODEL_TOKEN_USAGE']
        assert adapter.metadata['retryable'] is False
    finally:adapter.close();transport.close()

@pytest.mark.parametrize('field,value',[('thinking_level','high'),('max_output_tokens',65536),('profile','AGENTIC'),('profile','DEEP_REASONING')])
def test_client_cannot_select_profile(bundle,field,value):
    assert turn(bundle,**{field:value}).status_code in (400,403)
    assert not bundle[3].inputs

@pytest.mark.parametrize('change',[{'thinking_level':'high'},{'max_output_tokens':2048},{'max_output_tokens':65536},{'profile':'AGENTIC'},{'profile':'DEEP_REASONING'}])
def test_server_only_implemented_profile(change):
    with pytest.raises(ValueError):replace(ModelSettings(),**change)

def test_legacy_sampling_environment_does_not_override_profile(bundle,monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    monkeypatch.delenv('LUMA_GEMINI_API_KEY',raising=False)
    monkeypatch.setenv('LUMA_MODEL_TEMPERATURE','0.2')
    monkeypatch.setenv('LUMA_MODEL_MAX_OUTPUT_TOKENS','2048')
    cfg=ModelSettings.from_env(bundle[1])
    assert cfg.thinking_level=='low' and cfg.max_output_tokens==32768
    assert not hasattr(cfg,'temperature')

@pytest.mark.parametrize('tokens,expected',[(8191,[]),(8192,['HIGH_MODEL_TOKEN_USAGE'])])
def test_local_alert_threshold(tokens,expected):
    assert usage_alerts(ModelUsage(thought_tokens=tokens))==expected

def test_usage_and_alert_persist_without_contents(bundle):
    api,_,_,fake,_=bundle
    fake.change=lambda result,context:result.model_copy(update={'usage':ModelUsage(input_tokens=7000,output_tokens=300,thought_tokens=8500)})
    response=turn(bundle)
    assert response.status_code==200
    assert 'HIGH_MODEL_TOKEN_USAGE' in response.json()['warnings']
    assert response.json()['usage']['thought_tokens']==8500
    with api.app.state.control.store.read() as repo:
        events=[e for e in repo.rows('audit_events') if e['event_type']=='MODEL_GENERATION']
    assert events[-1]['usage_alerts']==['HIGH_MODEL_TOKEN_USAGE']
    assert events[-1]['usage']['thought_tokens']==8500
    assert 'assistant_message' not in events[-1] and events[-1]['latency_ms']>=0

@pytest.mark.parametrize('codes,expected',[([1],['follow_up']),([0,1],['follow_up','malicious_context']),([0,0,1],['follow_up','malicious_context','unauthorized_action']),([0,0,0,0],['follow_up','malicious_context','unauthorized_action',None])])
def test_directed_sequence(monkeypatch,codes,expected):
    import sys
    from backend import validate_gemini as validator
    calls=[]
    def run(case=None):
        calls.append(case)
        return codes[len(calls)-1]
    monkeypatch.setattr(validator,'run',run)
    monkeypatch.setattr(sys,'argv',['validator','--diagnose-follow-up'])
    validator.main()
    assert calls==expected
