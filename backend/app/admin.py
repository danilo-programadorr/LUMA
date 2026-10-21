import secrets
from fastapi import APIRouter,Request,Security,Query
from fastapi.security import HTTPBearer
from .admin_models import StateChange,ProjectChange,Revoke,ActionCreate,Decision,ActionTransition,SessionCreate,LearningCreate,LearningChange,GrantCreate
from .errors import Fault
from .models import Contract

class Empty(Contract):
    pass


def install(app,control,settings):
    router=APIRouter(prefix='/v1/admin',dependencies=[Security(HTTPBearer(auto_error=False))])
    def confirmation(request):
        values=request.headers.getlist('x-admin-confirmation')
        return bool(settings.admin_confirmation_token and len(values)==1 and values[0].isascii() and
            len(values[0])<=256 and secrets.compare_digest(values[0],settings.admin_confirmation_token))
    def change(request,operation,body,target=None):
        keys=request.headers.getlist('idempotency-key')
        if len(keys)!=1: raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        return control.mutate(request.state.principal,operation,body,keys[0],request.state.correlation_id,
            target=target,confirmed=confirmation(request))

    @router.get('/state')
    def state(request:Request): return control.listing(request.state.principal,'state')

    @router.get('/actions/{object_id}')
    def action(request:Request,object_id:str): return control.listing(request.state.principal,'actions',key=object_id)

    # Fixed paths and capability mappings; no client-selected database/table names.
    def reader(kind):
        def read(request:Request,limit:int=Query(100,ge=1,le=100),offset:int=Query(0,ge=0,le=10000)):
            return control.listing(request.state.principal,kind,limit,offset)
        return read
    for url,kind in [('projects','projects'),('tools','tools'),('agents','agents'),('actions','actions'),
        ('approvals','approvals'),('approval-requests','approval_requests'),('revocations','revocations'),
        ('sessions','sessions'),('learning','learning'),('audit','audit_events'),('grants','grants'),('retention','retention_policies'),('retention/preview','retention_preview'),('audit/verify','audit_verify')]:
        router.add_api_route('/'+url,reader(kind),methods=['GET'],name='admin_read_'+url)

    @router.post('/state')
    def state_change(body:StateChange,request:Request): return change(request,'state',body.model_dump())
    @router.patch('/projects/{project_id}')
    def project_change(project_id:str,body:ProjectChange,request:Request): return change(request,'project',body.model_dump(),project_id)
    @router.post('/tools/{tool_id}/enable')
    def enable(tool_id:str,request:Request,body:Empty | None=None): return change(request,'tool',{'enabled':True},tool_id)
    @router.post('/tools/{tool_id}/disable')
    def disable(tool_id:str,request:Request,body:Empty | None=None): return change(request,'tool',{'enabled':False},tool_id)
    @router.post('/revocations')
    def revoke(body:Revoke,request:Request): return change(request,'revoke',body.model_dump())
    @router.post('/actions')
    def action_create(body:ActionCreate,request:Request): return change(request,'action',body.model_dump())
    @router.post('/actions/{action_id}/transition')
    def transition(action_id:str,body:ActionTransition,request:Request): return change(request,'transition',body.model_dump(),action_id)
    @router.post('/approvals/{action_id}/decision')
    def decision(action_id:str,body:Decision,request:Request): return change(request,'decision',body.model_dump(),action_id)
    @router.post('/approvals/{approval_id}/consume')
    def consume(approval_id:str,request:Request,body:Empty | None=None): return change(request,'consume',{},approval_id)
    @router.post('/sessions')
    def session(body:SessionCreate,request:Request): return change(request,'session',body.model_dump())
    @router.post('/sessions/{session_id}/close')
    def close(session_id:str,request:Request,body:Empty | None=None): return change(request,'close_session',{},session_id)
    @router.post('/learning')
    def learning(body:LearningCreate,request:Request): return change(request,'learning',body.model_dump())
    @router.post('/learning/{candidate_id}/status')
    def learning_status(candidate_id:str,body:LearningChange,request:Request): return change(request,'learning_status',body.model_dump(),candidate_id)
    def grant_change(request,data,target=None):
        keys=request.headers.getlist('idempotency-key')
        if len(keys)!=1: raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        return control.manage_grant(request.state.principal,data,keys[0],request.state.correlation_id,target,confirmation(request))
    @router.post('/grants')
    def grant_create(body:GrantCreate,request:Request): return grant_change(request,body.model_dump())
    @router.post('/grants/{grant_id}/revoke')
    def grant_revoke(grant_id:str,request:Request,body:Empty | None=None): return grant_change(request,{},grant_id)
    app.include_router(router)
