"""Runtime composition root; does not import canonical DB or Control Plane services."""
import os
from types import SimpleNamespace
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .app import __version__
from .runtime_processor import RuntimeTaskProcessor,IntelligenceHandler
def create_local_runtime(provider=None,knowledge=None,device_id=None,registry_version=None):
    forbidden=('LUMA_OWNER_TOKEN','LUMA_TOKEN','LUMA_ADMIN_CONFIRM_TOKEN','LUMA_DATABASE_URL','LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD','DATABASE_URL','PGPASSWORD')
    if any(os.environ.get(key) for key in forbidden):raise ValueError('RUNTIME_AUTHORITY_CREDENTIAL_DENIED')
    from .app.model_config import ModelSettings
    from .app.model_provider import GeminiModelProvider
    from .app.knowledge import KnowledgeClient
    from .app.adk_bridge import run_workflow
    settings=SimpleNamespace(token='',runtime_token=os.environ.get('LUMA_RUNTIME_TOKEN',''),admin_confirmation_token='',
        knowledge_token=os.environ.get('LUMA_KNOWLEDGE_TOKEN',''),knowledge_endpoint=os.environ.get('LUMA_KNOWLEDGE_ENDPOINT','http://127.0.0.1:8765'),timeout=3)
    from urllib.parse import urlsplit
    endpoint=urlsplit(settings.knowledge_endpoint)
    if endpoint.scheme!='http' or endpoint.hostname!='127.0.0.1' or not endpoint.port or endpoint.username or endpoint.password or endpoint.query:raise ValueError('INVALID_LOCAL_KNOWLEDGE_ENDPOINT')
    cfg=ModelSettings.from_env(settings)
    provider=provider or GeminiModelProvider(cfg)
    knowledge=knowledge or KnowledgeClient(settings)
    processor=RuntimeTaskProcessor(IntelligenceHandler(provider,knowledge,run_workflow),
        device_id=device_id or os.environ.get('LUMA_DEVICE_ID','local-dev'),
        registry_version=registry_version or os.environ.get('LUMA_REGISTRY_VERSION','unbound'))
    @asynccontextmanager
    async def lifespan(app):
        try:yield
        finally:provider.close();knowledge.close()
    app=FastAPI(title='LUMA Local Runtime',docs_url=None,redoc_url=None,lifespan=lifespan)
    app.state.processor=processor
    @app.get('/health')
    def health():return dict(mode='LOCAL_RUNTIME',version=__version__,gemini_configured=cfg.configured,
        knowledge_available=False,knowledge_probe='NOT_PROBED',adk_version='2.12.0')
    return app
