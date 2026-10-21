"""Provider classification and pre-provider failure regressions; no vendor network."""
import json
import httpx
import pytest
from google import genai
from google.genai import types
from backend.model_worker.adapter import GeminiAdapter
from backend.app.provider_diagnostics import valid_metadata
from backend.app.errors import Fault
from backend.tests.test_model_worker import config,context,result
from backend.tests.test_conversation import bundle,turn

@pytest.mark.parametrize('status,code,retryable',[(400,'MODEL_INVALID_REQUEST',False),(401,'MODEL_AUTH_ERROR',False),(403,'MODEL_AUTH_ERROR',False),(408,'MODEL_TIMEOUT',True),(429,'MODEL_RATE_LIMIT',True),(500,'MODEL_UNAVAILABLE',True),(503,'MODEL_UNAVAILABLE',True),(404,'MODEL_PROVIDER_ERROR',False)])
def test_http_classification_sanitized(config,status,code,retryable):
    transport=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(status,json={'error':{'code':status,'status':'sensitive-arbitrary-value','message':'secret-not-for-diagnostic'}})))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport,retry_options=types.HttpRetryOptions(attempts=1)))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,max_output_tokens=2048,temperature=.2),client=client)
    try:
        with pytest.raises(Fault,match=code):adapter.generate(context())
        assert adapter.metadata['provider_status']==status
        assert adapter.metadata['provider_code']=='OTHER'
        assert adapter.metadata['retryable']==retryable
        assert valid_metadata(adapter.metadata)
        assert 'sensitive-arbitrary-value' not in json.dumps(adapter.metadata)
        assert 'secret-not-for-diagnostic' not in json.dumps(adapter.metadata)
    finally:adapter.close();transport.close()

@pytest.mark.parametrize('finish,text,code,schema',[
    ('SAFETY','{}','MODEL_SAFETY_REJECTION',None),('BLOCKLIST','{}','MODEL_SAFETY_REJECTION',None),
    ('MAX_TOKENS','{}','MODEL_INVALID_RESPONSE',None),('LANGUAGE','{}','MODEL_INVALID_RESPONSE',None),
    ('MALFORMED_FUNCTION_CALL','{}','MODEL_INVALID_RESPONSE',None),('OTHER','{}','MODEL_INVALID_RESPONSE',None),
    ('STOP','not json','MODEL_INVALID_RESPONSE',False),('STOP','{"extra":"secret-not-for-diagnostic"}','MODEL_INVALID_RESPONSE',False)])
def test_finish_and_schema(config,finish,text,code,schema):
    transport=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':text}]},'finishReason':finish}]})))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,max_output_tokens=2048,temperature=.2),client=client)
    try:
        with pytest.raises(Fault,match=code):adapter.generate(context())
        assert adapter.metadata['finish_reason']==finish
        assert adapter.metadata['schema_validation']==schema
        assert adapter.metadata['response_received'] is True
        assert valid_metadata(adapter.metadata)
        assert 'secret-not-for-diagnostic' not in json.dumps(adapter.metadata)
    finally:adapter.close();transport.close()

@pytest.mark.parametrize('reason',['SAFETY','BLOCKLIST','PROHIBITED_CONTENT'])
def test_prompt_block(config,reason):
    transport=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'promptFeedback':{'blockReason':reason}})))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,max_output_tokens=2048,temperature=.2),client=client)
    try:
        with pytest.raises(Fault,match='MODEL_SAFETY_REJECTION'):adapter.generate(context())
        assert adapter.metadata['blocked'] is True and adapter.metadata['block_reason']==reason
        assert adapter.metadata['retryable'] is False
    finally:adapter.close();transport.close()

def test_history_contract_failure_precedes_provider(bundle):
    api,_,_,fake,sid=bundle
    assert turn(bundle,'Quais os riscos?').status_code==200
    count=len(fake.inputs)
    with api.app.state.control.store.transaction() as repo:
        window=repo.get('conversation_windows',sid)
        window['turns']=[dict(user='synthetic',assistant='x'*2400)]
        repo.put('conversation_windows',sid,window)
    response=turn(bundle,'Marque uma reunião no Calendar amanhã.')
    assert response.status_code==503
    assert response.json()['error']['code']=='MODEL_INPUT_SCHEMA_INVALID'
    assert len(fake.inputs)==count

def test_metadata_rejects_unknown_fields_and_values():
    from backend.app.provider_diagnostics import empty_metadata
    data=empty_metadata();data['prompt']='secret'
    assert not valid_metadata(data)
    data=empty_metadata();data['finish_reason']='secret'
    assert not valid_metadata(data)

@pytest.mark.parametrize('isolated_code,expected',[(0,['unauthorized_action',None]),(1,['unauthorized_action']),(2,['unauthorized_action'])])
def test_directed_cli_stops_unless_isolated_passes(monkeypatch,isolated_code,expected):
    import sys
    from backend import validate_gemini as validator
    calls=[]
    def run(case=None):
        calls.append(case)
        return isolated_code if case else 0
    monkeypatch.setattr(validator,'run',run)
    monkeypatch.setattr(sys,'argv',['validator','--diagnose-unauthorized'])
    validator.main()
    assert calls==expected
