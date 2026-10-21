"""Test-only process harness with graceful private-stdin shutdown."""
import os
import threading
import sys
import uvicorn
from backend.app.config import Settings
from backend.app.main import create_app

if __name__=='__main__':
    settings=Settings.from_env()
    app=create_app(settings)
    if os.environ.get('LUMA_TEST_FAKE_MODEL')=='1':
        import httpx
        from backend.tests.test_conversation import FakeModelProvider
        from backend.tests.test_foundation import transport
        from backend.app.knowledge import KnowledgeClient
        from backend.app.model_config import ModelSettings
        app.state.control.close()
        for client in app.state.service.clients.values(): client.close()
        app=create_app(settings,KnowledgeClient(settings,httpx.MockTransport(transport)),FakeModelProvider(),ModelSettings(provider='disabled',model='gemini-test'))
    server=uvicorn.Server(uvicorn.Config(app,host=settings.host,port=settings.port,proxy_headers=False,access_log=False,log_level='error'))
    def stop():
        sys.stdin.readline()
        server.should_exit=True
    threading.Thread(target=stop,daemon=True).start()
    server.run()
