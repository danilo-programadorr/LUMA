"""Only this test harness imports the external service to launch it; LUMA uses HTTP only."""
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
import httpx
import pytest
import uvicorn
from backend.app.config import Settings
from backend.app.main import create_app


class Server:
    def __init__(self,app):
        self.socket=socket.socket()
        self.socket.bind(('127.0.0.1',0))
        self.port=self.socket.getsockname()[1]
        self.server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=self.port,access_log=False,proxy_headers=False,log_level='error'))
        self.thread=threading.Thread(target=self.server.run,kwargs={'sockets':[self.socket]})
    def start(self):
        self.thread.start()
        deadline=time.monotonic()+15
        while not self.server.started and self.thread.is_alive() and time.monotonic()<deadline: time.sleep(.01)
        assert self.server.started
        return self
    def stop(self):
        self.server.should_exit=True
        self.thread.join(timeout=15)
        self.socket.close()
        assert not self.thread.is_alive()


def test_real_http_integration(tmp_path):
    brain=os.environ.get('LUMA_TEST_KNOWLEDGE_WORKSPACE')
    if not brain: pytest.skip('Set LUMA_TEST_KNOWLEDGE_WORKSPACE for authorized local integration')
    sys.dont_write_bytecode=True
    sys.path.insert(0,brain)
    from knowledge_api.app.config import Settings as KSettings,Principal as KPrincipal
    from knowledge_api.app.main import create_app as knowledge_app
    token=secrets.token_urlsafe(32)
    ka=knowledge_app(KSettings(token,KPrincipal('luma-consumer',('meu-gestor',),'INTERNO',('INTERNO',))))
    knowledge=Server(ka).start()
    settings=Settings(secrets.token_urlsafe(32),token,knowledge_endpoint=f'http://127.0.0.1:{knowledge.port}')
    from backend.migrate import migrate
    from dataclasses import replace
    settings=replace(settings,runtime_token=secrets.token_urlsafe(32),database_url='sqlite:///'+(tmp_path/'live.db').as_posix())
    migrate(settings.database_url)
    luma=None
    comparisons=[]
    try:
        app=create_app(settings)
        luma=Server(app).start()
        with httpx.Client(base_url=f'http://127.0.0.1:{luma.port}',timeout=15,trust_env=False,
                          headers={'Authorization':'Bearer '+settings.token}) as c, httpx.Client(
                          base_url=settings.knowledge_endpoint,timeout=15,trust_env=False,
                          headers={'Authorization':'Bearer '+token}) as direct:
            assert c.get('/v1/luma/status').json()['status']=='READY'
            session_response=c.post('/v1/admin/sessions',json={'project_id':'meu-gestor'},headers={'Idempotency-Key':secrets.token_hex(12)})
            assert session_response.status_code==200,session_response.text
            session_id=session_response.json()['session_id']
            for question in ['arquitetura técnica','privacidade e dados pessoais','riscos atuais','permissão atual para executar',
                             'histórico de autorização','revogação parada e restauração','funcionalidades produto','segurança de ferramentas']:
                body={'project_id':'meu-gestor','query':question}
                expected=direct.post('/v1/knowledge/query',json=body)
                actual=c.post('/v1/knowledge/query',json=body)
                assert actual.status_code==expected.status_code==200,actual.text
                runtime=c.post('/v1/runtime/knowledge/query',json={**body,'session_id':session_id},headers={'Authorization':'Bearer '+settings.runtime_token})
                assert runtime.status_code==200,runtime.text
                result=actual.json()
                for field in ('project_id','results','sources','warnings','permission_status','status','confidence'):
                    assert result[field]==expected.json()[field]==runtime.json()[field],field
                assert result['brain_version']=='0.6.0' and result['engine_version']=='1.4.0'
                assert result['content_trust']=='UNTRUSTED_DATA' and 'answer' not in result
                comparisons.append({'category':question,'owner_equivalent':True,'runtime_equivalent':True,'chunks':len(result['results'])})
            schema=c.get('/openapi.json').json()
            (tmp_path/'openapi.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf8')
            knowledge.stop()
            assert ka.state.adapter.process.poll() is not None
            assert c.get('/health').status_code==200
            status=c.get('/v1/luma/status').json()
            assert status['status']=='DEGRADED' and status['projects'][0]['knowledge_status']=='UNAVAILABLE'
            assert c.post('/v1/knowledge/query',json={'project_id':'meu-gestor','query':'arquitetura'}).status_code==503
    finally:
        if luma: luma.stop()
        if knowledge.thread.is_alive(): knowledge.stop()
    evidence={'http_only':True,'loopback_only':True,'cases':comparisons,'knowledge_worker_stopped':ka.state.adapter.process.poll() is not None,
              'luma_stopped':not luma.thread.is_alive(),'degraded_without_knowledge':True}
    (tmp_path/'integration.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
