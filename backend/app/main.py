from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,Security
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from . import __version__
from .config import Settings
from .auth import LocalAuthenticator
from .errors import Fault
from .models import KnowledgeRequest,KnowledgeContext,Contract,ident
from .trust import Control
from .admin import install
from .knowledge import KnowledgeClient,KnowledgeService
from .audit import emit


class ErrorDetail(Contract):
    code:str


class ErrorResponse(Contract):
    correlation_id:str
    error:ErrorDetail


def failure(request,error):
    request.state.result=error.code
    return JSONResponse({'correlation_id':request.state.correlation_id,'error':{'code':error.code}},
        status_code=error.status,headers={'WWW-Authenticate':'Bearer'} if error.status==401 else None)


def create_app(settings=None,client=None,model_provider=None,model_settings=None,*,execution_sandbox=False):
    settings=settings or Settings.from_env()
    from .model_config import ModelSettings
    from .model_provider import GeminiModelProvider
    from .conversation import ConversationService,install_conversation
    model_settings=model_settings or ModelSettings.from_env(settings)
    model_settings.check_separation(settings)
    provider=model_provider or GeminiModelProvider(model_settings)
    control=Control(settings)
    control.model_api_key=model_settings.api_key
    projects=policy=control
    client=client or KnowledgeClient(settings)
    service=KnowledgeService(settings,projects,policy,client)
    auth=LocalAuthenticator(settings,control)

    @asynccontextmanager
    async def lifespan(app):
        # Remote knowledge availability is independent of LUMA readiness.
        try: yield
        finally:
            provider.close()
            client.close()
            control.close()

    app=FastAPI(title='LUMA Backend',version=__version__,docs_url=None,redoc_url=None,lifespan=lifespan,
        responses={'default':{'model':ErrorResponse,'description':'Fail-closed structured error'}})
    app.state.policy,app.state.projects,app.state.service=policy,projects,service
    app.state.model_provider=provider
    app.state.conversation=ConversationService(control,service,provider,model_settings)
    install_conversation(app,app.state.conversation)
    from .execution import ExecutionService
    from .execution_api import install_execution
    app.state.execution=ExecutionService(control,sandbox=execution_sandbox)
    control.device_registry=app.state.execution.devices
    install_execution(app,app.state.execution)
    from .orchestration import Orchestrator,install_orchestration
    app.state.orchestrator=Orchestrator(control,service,provider,model_settings,app.state.execution)
    install_orchestration(app,app.state.orchestrator)
    app.state.control=control
    app.state.local=control
    install(app,control,settings)
    from .runtime import install_runtime
    install_runtime(app,control,service)
    bearer=HTTPBearer(auto_error=False)

    @app.middleware('http')
    async def boundary(request,call_next):
        request.state.correlation_id=ident()
        request.state.principal=None
        request.state.project_id=None
        request.state.result='OK'
        response=None
        try:
            if request.headers.get('host','').split(':')[0] not in ('127.0.0.1','localhost'):
                raise Fault('HOST_DENIED',403)
            if request.url.path.startswith('/v1/'):
                request.state.principal=auth.authenticate(request)
            body=bytearray()
            async for part in request.stream():
                body.extend(part)
                if len(body)>16384: raise Fault('INVALID_REQUEST',413)
            request._body=bytes(body)
            response=await call_next(request)
        except Fault as e: response=failure(request,e)
        except Exception: response=failure(request,Fault('INTERNAL_ERROR',500))
        finally:
            p=request.state.principal
            known={'/health':'HEALTH','/v1/luma/status':'STATUS','/v1/projects':'PROJECTS',
                '/v1/knowledge/query':'KNOWLEDGE_QUERY','/v1/tools':'TOOLS','/v1/agents':'AGENTS'}
            emit(p.principal_id if p else None,request.state.project_id,known.get(request.url.path,'HTTP'),
                request.state.result if request.state.result!='OK' else str(response.status_code if response else 500),
                request.state.correlation_id,tool_id='knowledge' if request.url.path=='/v1/knowledge/query' else None)
        try:
            control.http_event(request.state.principal,request.state.project_id,known.get(request.url.path,'ADMIN_HTTP' if request.url.path.startswith('/v1/admin/') else 'HTTP'),request.state.result if request.state.result!='OK' else str(response.status_code),request.state.correlation_id)
        except Fault:
            response=failure(request,Fault('AUDIT_UNAVAILABLE',503))
        response.headers['X-Correlation-ID']=request.state.correlation_id
        response.headers['Cache-Control']='no-store'
        return response

    @app.exception_handler(Fault)
    async def fault(request,error): return failure(request,error)

    @app.exception_handler(RequestValidationError)
    async def invalid(request,error):
        fields={str(x) for e in error.errors() for x in e['loc']}
        elevation={'access_level','sensitivity','project_scope','project_scopes','principal_id','capabilities','roles','approval_level','origin_type','origin_id','approved','grant','unlock','identity','permission_override'}
        return failure(request,Fault('PRIVILEGE_ESCALATION' if fields&elevation else 'INVALID_REQUEST',403 if fields&elevation else 400))

    @app.get('/health')
    def health(): return {'status':'ok','service_version':__version__}

    def project_status(principal,correlation):
        rows=[]
        for project in projects.items.values():
            if project.project_id not in principal.project_scopes: continue
            state='UNAVAILABLE'
            try:
                resolved=projects.resolve(project.project_id,principal)
                policy.check(principal,resolved,'knowledge','knowledge.read')
                routed=service.resolve_client(resolved)
                routed.health(correlation)
                routed.status(project.project_id,correlation)
                state='AVAILABLE'
            except Fault: pass
            rows.append({**project.model_dump(mode='json'),'knowledge_status':state})
        return rows

    @app.get('/v1/luma/status',dependencies=[Security(bearer)])
    def status(request:Request):
        rows=project_status(request.state.principal,request.state.correlation_id)
        return {'service_version':__version__,'state':policy.state,'status':'READY' if rows and all(p['knowledge_status']=='AVAILABLE' for p in rows) else 'DEGRADED',
            'principal':request.state.principal.model_dump(mode='json'),'projects':rows,
            'generative_ai_enabled':model_settings.configured,'model':provider.status(),'external_execution_enabled':False}

    @app.get('/v1/projects',dependencies=[Security(bearer)])
    def project_list(request:Request): return project_status(request.state.principal,request.state.correlation_id)

    @app.get('/v1/tools',dependencies=[Security(bearer)])
    def tools(request:Request):
        return [{**t,'enabled':t['enabled'] and policy.state=='RUNNING'} for t in control.listing(request.state.principal,'tools')]

    @app.get('/v1/agents',dependencies=[Security(bearer)])
    def agents(request:Request): return control.listing(request.state.principal,'agents')

    @app.post('/v1/knowledge/query',response_model=KnowledgeContext,dependencies=[Security(bearer)])
    def query(body:KnowledgeRequest,request:Request):
        control.safe(body.model_dump(mode='json'))
        principal=request.state.principal
        projects.resolve(body.project_id,principal)
        request.state.project_id=body.project_id
        return service.query(principal,body,request.state.correlation_id)

    return app
