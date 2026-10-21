import json,secrets,time,os
from types import SimpleNamespace
import pytest,httpx
from google import genai
from google.genai import types
from backend.app.model_provider import GeminiModelProvider,worker_environment
from backend.app.model_config import ModelSettings
from backend.app.model_contracts import ModelInputContext,ModelDecision
from backend.app.generation import ModelResult
from backend.app.errors import Fault
from backend.model_worker.adapter import GeminiAdapter

@pytest.fixture
def config():return ModelSettings(provider='gemini',api_key=secrets.token_urlsafe(32),model='gemini-test',timeout=1)

def context():return ModelInputContext(user_message='hello',project_id='meu-gestor',session_id='synthetic')

def result():return ModelResult(decision=ModelDecision(assistant_message='Hello',intent='greeting',confidence=.5),model_name='gemini-test')

@pytest.mark.parametrize('scenario,code', [('crash','MODEL_INVALID_RESPONSE'),('invalid','MODEL_INVALID_RESPONSE'),('large','MODEL_INVALID_RESPONSE'),
    ('timeout','MODEL_TIMEOUT'),('wrong_id','MODEL_INVALID_RESPONSE'),('eof','MODEL_INVALID_RESPONSE')])
def test_worker_faults_and_cleanup(tmp_path,config,scenario,code):
    scripts={'crash':'raise RuntimeError("synthetic")','invalid':'print("not-json")','large':'print("x"*150000)',
        'timeout':'import time;time.sleep(10)','wrong_id':'print(json.dumps({"correlation_id":"wrong","result":'+repr(result().model_dump(mode='json'))+'}))','eof':'pass'}
    worker=tmp_path/'worker.py';worker.write_text('import json,sys\n'+scripts[scenario],encoding='utf8')
    provider=GeminiModelProvider(config);provider.worker=worker
    with pytest.raises(Fault,match=code):provider.generate(context(),'correlation')
    assert not provider.active and provider.status()['available'] is False
    provider.close()

def test_sanitized_environment_and_recovery(tmp_path,config,monkeypatch):
    for key in ('LUMA_OWNER_TOKEN','LUMA_RUNTIME_TOKEN','LUMA_ADMIN_CONFIRM_TOKEN','LUMA_KNOWLEDGE_TOKEN','LUMA_DATABASE_URL','GOOGLE_API_KEY','HTTP_PROXY'):
        monkeypatch.setenv(key,secrets.token_urlsafe(32))
    provider=GeminiModelProvider(config)
    worker=tmp_path/'worker.py'
    reply=result().model_dump(mode='json')
    worker.write_text('import json,sys,os\nr=json.loads(sys.stdin.buffer.readline())\nassert set(os.environ)<= {"GEMINI_API_KEY","SYSTEMROOT","WINDIR","LC_CTYPE"}\nprint(json.dumps({"correlation_id":r["correlation_id"],"result":'+repr(reply)+'}))\n',encoding='utf8')
    provider.worker=worker
    for i in range(2):assert provider.generate(context(),'correlation-'+str(i)).model_name=='gemini-test'
    assert not provider.active
    provider.close()
    with pytest.raises(Fault,match='MODEL_UNAVAILABLE'):provider.generate(context(),'after-close')

@pytest.mark.parametrize('status,code',[(401,'MODEL_AUTH_ERROR'),(403,'MODEL_AUTH_ERROR'),(429,'MODEL_RATE_LIMIT'),(503,'MODEL_UNAVAILABLE'),(400,'MODEL_ERROR')])
def test_real_sdk_error_mapping_without_network(config,status,code):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(status,json={'error':{'code':status,'message':'synthetic','status':'UNAVAILABLE'}})
    transport=httpx.Client(transport=httpx.MockTransport(handler))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport,retry_options=types.HttpRetryOptions(attempts=1)))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,max_output_tokens=2048,temperature=.2),client=client)
    try:
        with pytest.raises(Fault,match=code):adapter.generate(context())
        assert len(calls)==1
    finally:adapter.close();transport.close()

def test_real_sdk_structured_request_without_tools(config):
    captured=[]
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':result().decision.model_dump_json()}]},'finishReason':'STOP'}],
            'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':20}})
    transport=httpx.Client(transport=httpx.MockTransport(handler))
    client=genai.Client(api_key=config.api_key,http_options=types.HttpOptions(httpx_client=transport,retry_options=types.HttpRetryOptions(attempts=1)))
    adapter=GeminiAdapter(config.api_key,dict(model=config.model,timeout=1,max_output_tokens=2048,temperature=.2),client=client)
    try:
        response=adapter.generate(context());assert response.usage.input_tokens==10
        body=captured[0];assert not body.get('tools')
        assert body['generationConfig']['responseMimeType']=='application/json'
        assert body['generationConfig']['maxOutputTokens']==2048
        assert config.api_key not in json.dumps(body)
    finally:adapter.close();transport.close()

@pytest.mark.parametrize('change',[{'attempts':2},{'timeout':100},{'max_output_tokens':99999},{'model':'http://evil.test'},{'max_conversation_chars':9000}])
def test_server_limits(config,change):
    from dataclasses import replace
    with pytest.raises(ValueError):replace(config,**change)
