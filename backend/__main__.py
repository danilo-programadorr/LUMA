import logging
import uvicorn
from .app.config import Settings
from .app.main import create_app


def main():
    settings=Settings.from_env()
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    # Do not emit outbound HTTP URLs/headers from httpx diagnostics.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    uvicorn.run(create_app(settings),host=settings.host,port=settings.port,proxy_headers=False,
        access_log=False,log_level='warning')


if __name__=='__main__': main()
