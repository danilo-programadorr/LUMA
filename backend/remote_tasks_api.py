from fastapi import Request,Query
from typing import Literal
from .remote_tasks import RemoteTasks,TaskCreate,Decision
from .app.models import Contract
from pydantic import Field
from .app.errors import Fault
from .owner_auth import require_recent_auth
class Empty(Contract):pass
class TestCapability(Contract):
 enabled:bool
 confirmation:Literal['SYNTHETIC_TEST_ONLY']

def install(app,execution,devices):
 service=RemoteTasks(execution);service.device_service=devices;app.state.remote_tasks=service
 def owner(request):
  identity=getattr(request.state,'owner',None)
  if identity is None:raise Fault('UNAUTHORIZED',401)
  with service.store.read() as r:devices.owner(r,identity)
  return request.state.principal
 @app.post('/v1/tasks')
 def create(body:TaskCreate,request:Request):return service.create(owner(request),body.model_dump(),request.state.correlation_id)
 @app.get('/v1/tasks')
 def listing(request:Request,limit:int=Query(default=50,ge=1,le=100)):return service.listing(owner(request),limit)
 @app.get('/v1/tasks/{tid}')
 def detail(tid:str,request:Request):return service.get(owner(request),tid)
 @app.post('/v1/tasks/{tid}/decision')
 def decide(tid:str,body:Decision,request:Request):
  p=owner(request);recent=False
  try:
   if body.decision=='APPROVE':require_recent_auth(request.state.owner);recent=True
   return service.decide(p,tid,body.model_dump(),request.state.correlation_id,recent)
  except Fault as exc:
   with service.store.transaction() as r:
    task=r.get('agent_tasks',tid)
    visible=task if task and task.get('principal_id')==p.principal_id else {}
    execution.event(r,'REMOTE_TASK_DECISION_REJECTED',{**visible,'correlation_id':request.state.correlation_id},exc.code)
   raise
 @app.post('/v1/tasks/{tid}/cancel')
 def cancel(tid:str,body:Empty,request:Request):return service.cancel(owner(request),tid,request.state.correlation_id)
 @app.post('/v1/tasks/{tid}/revoke')
 def revoke(tid:str,body:Empty,request:Request):return service.revoke(owner(request),tid,request.state.correlation_id)
 @app.get('/v1/remote-approvals')
 def approvals(request:Request):return service.listing(owner(request),50,approvals=True)

 @app.get('/v1/remote-task-devices')
 def eligible_devices(request:Request):
  p=owner(request)
  with service.store.read() as r:
   out=[]
   for d in r.rows('execution_devices'):
    if d['owner_principal_id']!=p.principal_id or d['project_id']!='meu-gestor':continue
    identity=r.get('device_identities',d['device_id'])
    state=devices.public(identity)['connection_status'] if identity else 'OFFLINE'
    out.append({'device_id':d['device_id'],'name':d['name'],'status':state,'eligible':d['enabled'] and not d['revoked_at'] and 'sandbox-test' in d['capabilities'],'active':d['enabled'] and not d['revoked_at']})
   return out

 @app.post('/v1/remote-task-devices/{did}/test-capability')
 def test_capability(did:str,body:TestCapability,request:Request):
  p=owner(request);require_recent_auth(request.state.owner)
  if not execution.sandbox:raise Fault('TEST_TOOL_DISABLED',403)
  with service.store.transaction() as r:
   devices.owner(r,request.state.owner,True);devices.rate(r,'remote-grant-'+p.principal_id,10)
   identity=r.get('device_identities',did);d=r.get('execution_devices',did)
   if not identity or not d or identity['status']!='ACTIVE' or d['owner_principal_id']!=p.principal_id or d['project_id']!='meu-gestor':raise Fault('DEVICE_SCOPE_MISMATCH',403)
   devices.binding(r,identity)
   caps=set(d['capabilities']);caps.discard('sandbox-test')
   if body.enabled:caps.add('sandbox-test')
   d['capabilities']=sorted(caps);d['reported_capabilities']=[]
   r.put('execution_devices',did,d)
   if not r.get('tools','sandbox-test'):r.add('tools','sandbox-test',dict(tool_id='sandbox-test',enabled=True,capabilities=['record','review','sensitive','critical']))
   service.control.event(r,p.principal_id,d['project_id'],'REMOTE_SYNTHETIC_CAPABILITY_CHANGED','ENABLED' if body.enabled else 'DISABLED',request.state.correlation_id)
   return {'device_id':did,'synthetic_capability_enabled':body.enabled}

 @app.get('/v1/remote-approvals/summary')
 def approval_summary(request:Request):
  p=owner(request)
  with service.store.read() as r:
   tasks=[t for t in r.rows('agent_tasks',principal_id=p.principal_id) if t.get('task_protocol')=='REMOTE_TASK_V1' and t['principal_id']==p.principal_id and t.get('action_request_id')]
   return {'pending':sum(service.view(r,t,include_timeline=False)['status']=='WAITING_AUTHORIZATION' for t in tasks)}
 class Page(Contract):
  offset:int=Field(default=0,ge=0,le=100000)
  limit:int=Field(default=50,ge=1,le=100)
  approvals:bool=False
 @app.post('/v1/task-pages')
 def pages(body:Page,request:Request):return service.listing(owner(request),body.limit,body.offset,body.approvals)
 class RuntimeClaim(Contract):
  device_id:str=Field(min_length=1,max_length=64,pattern=r'^[a-zA-Z0-9_-]+$')
 @app.post('/v1/runtime/tasks/{tid}/claim')
 def runtime_claim(tid:str,body:RuntimeClaim,request:Request):
  if len(body.device_id)>64:raise Fault('INVALID_REQUEST',400)
  return app.state.runtime_tasks.claim(request.state.principal,tid,body.device_id).model_dump(mode='json')
 @app.post('/v1/runtime/tasks/result')
 async def runtime_result(request:Request):
  from .remote_protocol import RuntimeResultEnvelope,decode
  from pydantic import ValidationError
  raw=await request.body()
  try:result=decode(RuntimeResultEnvelope,raw)
  except (ValidationError,ValueError):raise Fault('RUNTIME_PROTOCOL_ERROR',400) from None
  return app.state.runtime_tasks.accept(request.state.principal,result.device_id,raw)

 @app.post('/v1/runtime/tasks/poll')
 def runtime_poll(body:RuntimeClaim,request:Request):
  p=request.state.principal
  if p.principal_type!='SERVICE_RUNTIME':raise Fault('RUNTIME_IDENTITY_REQUIRED',403)
  with service.store.transaction() as r:
   devices.rate(r,'remote-runtime-'+p.principal_id,120)
   for t in r.rows('agent_tasks',projects=p.project_scopes):
    if t.get('task_protocol')=='REMOTE_TASK_V1' and t.get('envelope') and t.get('device_id')==body.device_id and t['status']=='QUEUED':
     from .app.control import date
     if date(t['envelope']['expires_at'])<=execution.clock():
      t['status']='EXPIRED';r.put('agent_tasks',t['task_id'],t);service.event(r,t,'REMOTE_TASK_EXPIRED');continue
     return {'task':app.state.runtime_tasks.claim(p,t['task_id'],body.device_id,_repo=r).model_dump(mode='json')}
   return {'task':None}
