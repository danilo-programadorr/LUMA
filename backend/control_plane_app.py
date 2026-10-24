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
    token:str=field(repr=False)
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
        validate_database(self.database_url,self.database_backend)
        values=[v for v in (self.token,self.runtime_token,self.admin_confirmation_token) if v]
        if not self.token or any(not 32<=len(v)<=256 or not v.isascii() or any(c.isspace() for c in v) for v in values) or len(values)!=len(set(values)):raise ValueError('INVALID_CONTROL_CREDENTIALS')
    @classmethod
    def from_env(cls):
        return cls(token=os.environ.get('LUMA_OWNER_TOKEN',''),runtime_token=os.environ.get('LUMA_RUNTIME_TOKEN',''),
            admin_confirmation_token=os.environ.get('LUMA_ADMIN_CONFIRM_TOKEN',''),
            database_url=os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL),database_backend=os.environ.get('LUMA_DATABASE_BACKEND','sqlite'))
def create_control_plane(settings=None):
    settings=settings or ControlPlaneSettings.from_env()
    control=Control(settings);execution=ExecutionService(control);control.device_registry=execution.devices
    auth=LocalAuthenticator(settings,control)
    @asynccontextmanager
    async def lifespan(app):
        try:yield
        finally:control.close()
    app=FastAPI(title='LUMA Control Plane',version=__version__,docs_url=None,redoc_url=None,lifespan=lifespan)
    app.state.control=control;app.state.execution=execution;app.state.runtime_tasks=RuntimeTaskService(control,execution)
    @app.middleware('http')
    async def boundary(request,call_next):
        request.state.correlation_id=ident();request.state.principal=None;request.state.project_id=None
        try:
            if request.headers.get('host','').split(':')[0] not in ('localhost','127.0.0.1'):raise Fault('HOST_DENIED',403)
            if request.url.path.startswith('/v1/'):request.state.principal=auth.authenticate(request)
            body=bytearray()
            async for part in request.stream():
                body.extend(part)
                if len(body)>16384:raise Fault('INVALID_REQUEST',413)
            request._body=bytes(body)
            response=await call_next(request)
            if request.url.path.startswith('/v1/'):control.http_event(request.state.principal,None,'CONTROL_HTTP',str(response.status_code),request.state.correlation_id)
        except Fault as exc:response=JSONResponse({'error':{'code':exc.code},'correlation_id':request.state.correlation_id},status_code=exc.status)
        except Exception:response=JSONResponse({'error':{'code':'INTERNAL_ERROR'}},status_code=500)
        response.headers['Cache-Control']='no-store';return response
    @app.exception_handler(Fault)
    async def fault(request,error):return JSONResponse({'error':{'code':error.code}},status_code=error.status)
    @app.exception_handler(RequestValidationError)
    async def invalid(request,error):return JSONResponse({'error':{'code':'INVALID_REQUEST'}},status_code=400)
    @app.get('/health')
    def health():
        from sqlalchemy import select
        with control.store.read() as r:
            revision=r.connection.execute(select(version.c.version)).scalar_one()
        return dict(mode='CONTROL_PLANE',version=__version__,database_status='AVAILABLE',migration_status='CURRENT' if revision==4 else 'MIGRATION_REQUIRED')
    install(app,control,settings);install_execution(app,execution)
    return app
