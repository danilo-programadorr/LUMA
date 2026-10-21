"""Safe diagnostic boundary and validator evidence regressions (no vendor network)."""
import json
import pytest
from backend.app.errors import Fault
from backend.app.model_provider import GeminiModelProvider
from backend.tests.test_model_worker import config,context

@pytest.mark.parametrize('detail',['HTTP_400','MAX_TOKENS','secret-must-not-pass'])
def test_worker_diagnostic_allowlist(tmp_path,config,detail):
    diagnostic=dict(failure_stage='first generation',credential_present=True,generation_attempted=True,safe_error_type='APIError',safe_detail=detail)
    worker=tmp_path/'worker.py'
    worker.write_text('import sys,json\nr=json.loads(sys.stdin.buffer.readline())\nprint(json.dumps(dict(correlation_id=r["correlation_id"],error="MODEL_ERROR",diagnostic='+repr(diagnostic)+')))\n',encoding='utf8')
    provider=GeminiModelProvider(config);provider.worker=worker
    try:
        with pytest.raises(Fault):provider.generate(context(),'diagnostic')
        assert 'secret-must-not-pass' not in json.dumps(provider.diagnostic)
        if detail!='secret-must-not-pass':assert provider.diagnostic==diagnostic
        assert not provider.active
    finally:provider.close()

def test_missing_credential_preserves_previous_report(tmp_path,monkeypatch):
    from backend import validate_gemini as validator
    (tmp_path/'reports').mkdir()
    report=tmp_path/'reports/FASE_7D_GEMINI_REAL.json'
    report.write_text('{"status":"FAILED"}',encoding='utf8')
    monkeypatch.setattr(validator,'ROOT',tmp_path)
    for name in ('LUMA_GEMINI_API_KEY','GEMINI_API_KEY'):monkeypatch.delenv(name,raising=False)
    assert validator.run()==2
    result=json.loads(report.read_text(encoding='utf8'))
    assert result['failure_stage']=='configuration'
    assert result['credential_present'] is False and result['real_model_tested'] is False
    assert len(list(report.parent.glob('*HISTORY*')))==1

@pytest.mark.parametrize('finish,text,stage,detail',[
    ('MAX_TOKENS','{}','response validation','MAX_TOKENS'),
    ('STOP','{"unexpected":"secret-must-not-pass"}','schema validation','NONE')])
def test_adapter_failure_detail(config,finish,text,stage,detail):
    import httpx
    from google import genai
    from google.genai import types
    from backend.model_worker.adapter import GeminiAdapter
    transport=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':text}]},'finishReason':finish}]})))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,max_output_tokens=2048,temperature=.2),client=client)
    try:
        with pytest.raises(Fault) as caught:adapter.generate(context())
        assert adapter.stage==stage and adapter.safe_detail==detail
        assert adapter.generation_attempted is True
        assert 'secret-must-not-pass' not in str(caught.value)
    finally:adapter.close();transport.close()

def test_validator_worker_failure_is_safe_and_cleans_servers(tmp_path,monkeypatch):
    from backend import validate_gemini as validator
    (tmp_path/'reports').mkdir();(tmp_path/'runtime').mkdir()
    monkeypatch.setattr(validator,'ROOT',tmp_path)
    monkeypatch.setenv('LUMA_GEMINI_API_KEY','synthetic-model-credential-for-test')
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    monkeypatch.setenv('LUMA_MODEL_PROVIDER','gemini')
    monkeypatch.setenv('LUMA_GEMINI_MODEL','gemini-test')
    class FailingProvider:
        diagnostic=dict(failure_stage='schema validation',generation_attempted=True,credential_present=True,safe_error_type='ValidationError',safe_detail='NONE')
        def __init__(self,config):pass
        def generate(self,*args):raise ValueError('secret-must-not-pass')
        def close(self):pass
    monkeypatch.setattr(validator,'GeminiModelProvider',FailingProvider)
    assert validator.run()==1
    raw=(tmp_path/'reports/FASE_7D_GEMINI_REAL.json').read_text(encoding='utf8')
    result=json.loads(raw)
    assert result['failure_stage']=='schema validation'
    assert result['real_model_tested'] is True and result['cases_executed']==0
    assert result['servers_stopped'] is True
    assert 'secret-must-not-pass' not in raw and 'synthetic-model-credential-for-test' not in raw
