import secrets
from fastapi import APIRouter,Request,Query,Security
from fastapi.security import HTTPBearer
from .execution_contracts import ActionCandidate,AuthorizationRequest,JobRequest,DeviceRegistration,DeviceHeartbeat
from .admin import Empty
from .errors import Fault

def install_execution(app,execution):
    router=APIRouter(prefix='/v1',dependencies=[Security(HTTPBearer(auto_error=False))])
    def key(request):
        keys=request.headers.getlist('idempotency-key')
        if len(keys)!=1:raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        return keys[0]
    @router.post('/action-requests')
    def candidate(body:ActionCandidate,request:Request):
        return execution.candidate(request.state.principal,body.model_dump(mode='json'),key(request),request.state.correlation_id)
    @router.post('/action-requests/{aid}/authorize')
    def authorize(aid:str,body:AuthorizationRequest,request:Request):
        values=request.headers.getlist('x-admin-confirmation');secret=execution.control.settings.admin_confirmation_token
        confirmed=bool(secret and len(values)==1 and values[0].isascii() and len(values[0])<=256 and secrets.compare_digest(secret,values[0]))
        return execution.authorize(request.state.principal,aid,body.model_dump(),key(request),request.state.correlation_id,confirmed)
    @router.post('/execution-authorizations/{authid}/revoke')
    def revoke(authid:str,body:Empty,request:Request):return execution.revoke(request.state.principal,authid,key(request),request.state.correlation_id)
    @router.post('/jobs')
    def job(body:JobRequest,request:Request):return execution.job(request.state.principal,body.model_dump(mode='json'),key(request),request.state.correlation_id)
    @router.post('/jobs/{jid}/cancel')
    def cancel(jid:str,body:Empty,request:Request):return execution.cancel(request.state.principal,jid,key(request),request.state.correlation_id)
    def reader(table):
        def read(request:Request,limit:int=Query(100,ge=1,le=100),offset:int=Query(0,ge=0,le=10000)):
            with execution.store.read() as repo:
                p=execution.owner(repo,request.state.principal)
                return [execution.devices.public(r) for r in repo.rows(table,projects=p.project_scopes) if r.get('principal_id')==p.principal_id][offset:offset+limit]
        return read
    def detail(table):
        def read(object_id:str,request:Request):
            with execution.store.read() as repo:return execution.devices.public(execution.owned(repo,table,object_id,request.state.principal))
        return read
    for route,table in [('execution-authorizations','execution_authorizations'),('jobs','jobs'),('execution-records','execution_records'),('execution-devices','execution_devices')]:
        router.add_api_route('/'+route,reader(table),methods=['GET'])
        router.add_api_route('/'+route+'/{object_id}',detail(table),methods=['GET'])
    @router.post('/execution-devices')
    def register(body:DeviceRegistration,request:Request):return execution.devices.register(request.state.principal,body.model_dump(),key(request),request.state.correlation_id)
    @router.post('/execution-devices/{device_id}/revoke')
    def revoke_device(device_id:str,body:Empty,request:Request):
        key(request)
        return execution.devices.revoke(request.state.principal,device_id)
    @router.post('/device/heartbeat')
    def heartbeat(body:DeviceHeartbeat,request:Request):
        if body.device_id!=request.state.device_id:raise Fault('DEVICE_UNAUTHORIZED',401)
        return execution.devices.heartbeat(body.model_dump(mode='json'),request.headers['authorization'].split(' ')[1])
    @router.post('/device/poll')
    def poll(body:Empty,request:Request):
        device=request.state.device_id
        return execution.claim('device-'+device,device,request.headers['authorization'].split(' ')[1])
    @router.post('/device/jobs/{jid}/sandbox')
    def sandbox(jid:str,body:Empty,request:Request):
        if not execution.sandbox:raise Fault('TEST_TOOL_DISABLED',403)
        with execution.store.read() as repo:
            row=repo.get('jobs',jid)
            if not row or row['action']['target_device_id']!=request.state.device_id:raise Fault('DEVICE_SCOPE_MISMATCH',403)
        return execution.execute(jid,'device-'+request.state.device_id)
    app.include_router(router)
