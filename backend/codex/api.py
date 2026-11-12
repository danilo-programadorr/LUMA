from typing import Literal
from fastapi import Request
from .contracts import Strict,WorkspaceManifest
from ..owner_auth import require_recent_auth
from ..app.errors import Fault
class WorkspaceRegistration(Strict):
 manifest:WorkspaceManifest
 confirmation:Literal['APPROVE_CODEX_WORKSPACE']
class Grant(Strict):
 enabled:bool
 confirmation:Literal['CODEX_EXECUTION_ONE_SHOT_ONLY']
def install(app,service):
 def owner(request,recent=False):
  identity=getattr(request.state,'owner',None)
  if identity is None:raise Fault('UNAUTHORIZED',401)
  if recent:require_recent_auth(identity)
  with service.store.read() as r:service.devices.owner(r,identity)
  return request.state.principal
 @app.get('/v1/codex/workspaces')
 def listing(request:Request):return service.workspaces(owner(request))
 @app.post('/v1/codex/workspaces')
 def register(body:WorkspaceRegistration,request:Request):return service.register(owner(request,True),body.manifest.model_dump())
 @app.post('/v1/codex/devices/{did}/grant')
 def grant(did:str,body:Grant,request:Request):return service.capability(owner(request,True),did,body.enabled)
 @app.post('/v1/device-runtime/codex/discovery')
 @app.post('/v1/device-runtime/codex/heartbeat')
 @app.post('/v1/device-runtime/codex/poll')
 @app.post('/v1/device-runtime/codex/check')
 @app.post('/v1/device-runtime/codex/progress')
 @app.post('/v1/device-runtime/codex/result')
 async def signed(request:Request):
  try:body=await request.json()
  except Exception:raise Fault('CODEX_REQUEST_INVALID',400) from None
  return service.handle(request.url.path,body)
