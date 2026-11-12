"""Authority-only composition root. No intelligence adapters."""
import os,secrets
from dataclasses import dataclass,field
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .app import __version__
from .app.models import Principal,ident
from .app.database import DEFAULT_URL,validate_database,version
from .app.trust import Control
from .app.execution import ExecutionService
from .app.auth import LocalAuthenticator
from .app.admin import install
from .app.execution_api import install_execution
from .app.errors import Fault
from .control_plane_tasks import RuntimeTaskService
@dataclass(frozen=True)
class ControlPlaneSettings:
    token:str=field(default='',repr=False)
    owner_auth_mode:str='LOCAL_TOKEN'
    identity_project:str=''
    research_enabled:bool=False
    library_enabled:bool=False
    devices_enabled:bool=False
    device_test_tool:bool=False
    codex_enabled:bool=False
    allowed_origins:tuple=('http://localhost:5173','http://127.0.0.1:5173')
    runtime_token:str=field(default='',repr=False)
    admin_confirmation_token:str=field(default='',repr=False)
    database_url:str=field(default=DEFAULT_URL,repr=False)
    database_backend:str='sqlite'
    principal:Principal=field(default_factory=Principal)
    knowledge_token:str=field(default='',repr=False)
    knowledge_endpoint:str=''
    history:bool=False
    packages:tuple=()
    host:str='127.0.0.1'
    port:int=8770
    def __post_init__(self):
        if self.owner_auth_mode not in ('LOCAL_TOKEN','IDENTITY_PLATFORM'):raise ValueError('INVALID_OWNER_AUTH_MODE')
        if self.owner_auth_mode=='IDENTITY_PLATFORM' and not self.identity_project:raise ValueError('IDENTITY_PROJECT_REQUIRED')
        if any(x not in ('http://localhost:5173','http://127.0.0.1:5173') for x in self.allowed_origins):raise ValueError('INVALID_WEB_ORIGIN')
        if self.devices_enabled and self.owner_auth_mode!='IDENTITY_PLATFORM':raise ValueError('DEVICE_OWNER_IDENTITY_REQUIRED')
        if self.research_enabled and not self.devices_enabled:raise ValueError('RESEARCH_DEVICE_CHANNEL_REQUIRED')
        if self.library_enabled and not self.devices_enabled:raise ValueError('LIBRARY_DEVICE_CHANNEL_REQUIRED')
        if self.device_test_tool and not self.devices_enabled:raise ValueError('DEVICE_CHANNEL_REQUIRED')
        if self.codex_enabled and not self.devices_enabled:raise ValueError('CODEX_DEVICE_CHANNEL_REQUIRED')
        validate_database(self.database_url,self.database_backend)
        values=[v for v in (self.token,self.runtime_token,self.admin_confirmation_token) if v]
        if (self.owner_auth_mode=='LOCAL_TOKEN' and not self.token) or any(not 32<=len(v)<=256 or not v.isascii() or any(c.isspace() for c in v) for v in values) or len(values)!=len(set(values)):raise ValueError('INVALID_CONTROL_CREDENTIALS')
    @classmethod
    def from_env(cls):
        return cls(codex_enabled=os.environ.get('LUMA_CODEX_ENABLED')=='1',library_enabled=os.environ.get('LUMA_PRIVATE_LIBRARY_ENABLED')=='1',research_enabled=os.environ.get('LUMA_RESEARCH_ENABLED')=='1',devices_enabled=os.environ.get('LUMA_DEVICES_ENABLED')=='1',device_test_tool=os.environ.get('LUMA_DEVICE_TEST_TOOL')=='1',owner_auth_mode=os.environ.get('LUMA_OWNER_AUTH_MODE','LOCAL_TOKEN'),identity_project=os.environ.get('LUMA_IDENTITY_PROJECT',''),token=os.environ.get('LUMA_OWNER_TOKEN',''),runtime_token=os.environ.get('LUMA_RUNTIME_TOKEN',''),
            admin_confirmation_token=os.environ.get('LUMA_ADMIN_CONFIRM_TOKEN',''),
            database_url=os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL),database_backend=os.environ.get('LUMA_DATABASE_BACKEND','sqlite'))
def create_control_plane(settings=None, *, _test_verifier=None):
    settings=settings or ControlPlaneSettings.from_env()
    if _test_verifier is not None and os.environ.get('LUMA_ENV')!='test':raise ValueError('TEST_ADAPTER_DENIED')
    control=Control(settings);execution=ExecutionService(control,sandbox=settings.device_test_tool);control.device_registry=execution.devices
    auth=LocalAuthenticator(settings,control)
    owner_auth=None
    if settings.owner_auth_mode=='IDENTITY_PLATFORM':
        from .owner_auth import OwnerAuthenticator
        owner_auth=OwnerAuthenticator(control,settings,_test_verifier)
    device_service=None
    if settings.devices_enabled:
        from .device_service import DeviceService
        with control.store.read() as r:
            from sqlalchemy import select
            if r.connection.execute(select(version.c.version)).scalar_one() not in (6,7,8,9):raise ValueError('DEVICE_MIGRATION_REQUIRED')
        device_service=DeviceService(control,execution)
    if settings.codex_enabled:
        from .codex.service import CodexService
        with control.store.read() as r:
            if r.connection.execute(select(version.c.version)).scalar_one()!=9:raise ValueError('CODEX_MIGRATION_REQUIRED')
        execution.codex=CodexService(device_service)
    @asynccontextmanager
    async def lifespan(app):
        try:yield
        finally:control.close()
    app=FastAPI(title='LUMA Control Plane',version=__version__,docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    app.state.device_service=device_service
    app.state.owner_auth=owner_auth
    app.state.control=control;app.state.execution=execution;app.state.runtime_tasks=RuntimeTaskService(control,execution)
    @app.middleware('http')
    async def boundary(request,call_next):
        request.state.correlation_id=ident();request.state.principal=None;request.state.project_id=None
        try:
            if request.headers.get('host','').split(':')[0] not in ('localhost','127.0.0.1'):raise Fault('HOST_DENIED',403)
            if request.headers.get('origin') and request.headers['origin'] not in settings.allowed_origins:raise Fault('ORIGIN_DENIED',403)
            if request.url.path.startswith('/v1/'):
                if device_service and (((settings.research_enabled and request.url.path.startswith('/v1/research-runtime/')) or (settings.library_enabled and request.url.path.startswith('/v1/library-runtime/'))) or (settings.codex_enabled and request.url.path.startswith('/v1/device-runtime/codex/')) or request.url.path in ('/v1/device-runtime/heartbeat','/v1/device-runtime/poll','/v1/device-runtime/result','/v1/devices/enrollment/complete')):
                    if request.headers.get('authorization'):raise Fault('DEVICE_CREDENTIAL_TYPE_DENIED',401)
                elif owner_auth and request.url.path=='/v1/owner/bootstrap':request.state.bootstrap_identity=owner_auth.identity(request)
                elif owner_auth and not request.url.path.startswith(('/v1/runtime/','/v1/device/')):request.state.principal=owner_auth.authenticate(request)
                else:request.state.principal=auth.authenticate(request)
            body=bytearray()
            async for part in request.stream():
                body.extend(part)
                if len(body)>(65536 if (settings.research_enabled and request.url.path.startswith('/v1/research-runtime/')) or (settings.library_enabled and request.url.path.startswith('/v1/library-runtime/')) else 16384):raise Fault('INVALID_REQUEST',413)
            request._body=bytes(body)
            response=await call_next(request)
            if request.url.path.startswith('/v1/'):control.http_event(request.state.principal,None,'CONTROL_HTTP',str(response.status_code),request.state.correlation_id)
        except Fault as exc:response=JSONResponse({'error':{'code':exc.code},'correlation_id':request.state.correlation_id},status_code=exc.status)
        except Exception:response=JSONResponse({'error':{'code':'INTERNAL_ERROR'}},status_code=500)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer';response.headers['X-Frame-Options']='DENY'
        return response
    @app.exception_handler(Fault)
    async def fault(request,error):return JSONResponse({'error':{'code':error.code}},status_code=error.status)
    @app.exception_handler(RequestValidationError)
    async def invalid(request,error):return JSONResponse({'error':{'code':'INVALID_REQUEST'}},status_code=400)
    @app.get('/health')
    def health():
        from sqlalchemy import select
        with control.store.read() as r:
            revision=r.connection.execute(select(version.c.version)).scalar_one()
        return dict(mode='CONTROL_PLANE',version=__version__,database_status='AVAILABLE',migration_status='CURRENT' if revision in (4,5,6,7,8,9) else 'MIGRATION_REQUIRED')
    if owner_auth:
        from pydantic import BaseModel,ConfigDict,Field
        class BootstrapBody(BaseModel):
            model_config=ConfigDict(extra='forbid')
            code:str=Field(min_length=1,max_length=256)
        @app.post('/v1/owner/bootstrap')
        def bind(body:BootstrapBody,request:Request):
            return owner_auth.bind(request.state.bootstrap_identity,body.code,request.state.correlation_id)
        @app.get('/v1/owner/me')
        def me(request:Request):
            owner=request.state.owner
            return dict(internal_owner_id=owner.internal_owner_id,provider=owner.identity_provider,status='ACTIVE',auth_time=owner.auth_time,auth_age_seconds=max(0,int(__import__('time').time())-owner.auth_time))
    install(app,control,settings);install_execution(app,execution)
    if device_service:
        from .device_api import install as install_devices
        install_devices(app,device_service)
        from .remote_tasks_api import install as install_remote_tasks
        install_remote_tasks(app,execution,device_service)
    if settings.codex_enabled:
        from .codex.api import install as install_codex
        install_codex(app,execution.codex);app.state.codex=execution.codex
    if settings.research_enabled:
        from .research.service import ResearchService
        from .research.api import install as install_research
        with control.store.read() as r:
            from sqlalchemy import select
            if r.connection.execute(select(version.c.version)).scalar_one() not in (7,8,9):raise ValueError('RESEARCH_MIGRATION_REQUIRED')
        app.state.research=ResearchService(control,device_service)
        install_research(app,app.state.research)
    if settings.library_enabled:
        from .private_library.service import LibraryService
        from .private_library.api import install as install_library
        app.state.library=LibraryService(control,device_service)
        install_library(app,app.state.library)
    from starlette.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware,allow_origins=list(settings.allowed_origins),allow_methods=['GET','POST','PATCH'],allow_headers=['Authorization','Content-Type','X-Correlation-ID','Idempotency-Key'],allow_credentials=False)

    return app
