"""Test-only process harness with graceful private-stdin shutdown."""
import threading
import sys
import uvicorn
from backend.app.config import Settings
from backend.app.main import create_app

if __name__=='__main__':
    settings=Settings.from_env()
    server=uvicorn.Server(uvicorn.Config(create_app(settings),host=settings.host,port=settings.port,proxy_headers=False,access_log=False,log_level='error'))
    def stop():
        sys.stdin.readline()
        server.should_exit=True
    threading.Thread(target=stop,daemon=True).start()
    server.run()
