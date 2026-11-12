from fastapi import Request
from backend.app.errors import Fault
from .contracts import ResearchCreate,ResearchGrant

def install(app,service):
    def owner(request):
        p=getattr(request.state,'owner',None)
        if p is None:raise Fault('UNAUTHORIZED',401)
        return p
    @app.get('/research-display/{ticket}')
    def display(ticket:str):
        from fastapi.responses import Response
        body,headers=service.open_display(ticket)
        return Response(content=body,media_type='text/html',headers=headers)
    @app.post('/v1/research')
    def create(body:ResearchCreate,request:Request):return service.create(owner(request),body.model_dump())
    @app.get('/v1/research/devices')
    def devices(request:Request):return service.available_devices(owner(request))
    @app.post('/v1/research/devices/{did}/capability')
    def grant(did:str,body:ResearchGrant,request:Request):return service.grant(owner(request),did,body.enabled)
    @app.get('/v1/research/{rid}')
    def get(rid:str,request:Request):return service.get(owner(request),rid)
    @app.get('/v1/research/{rid}/sources')
    def sources(rid:str,request:Request):return (service.get(owner(request),rid,live=False).get('result') or {}).get('sources',[])
    @app.post('/v1/research/{rid}/cancel')
    def cancel(rid:str,request:Request):return service.get(owner(request),rid,True)
    @app.post('/v1/research-runtime/{operation}')
    async def runtime(operation:str,request:Request):
        try:data=await request.json()
        except Exception:raise Fault('RESEARCH_REQUEST_INVALID',400) from None
        return service.handle(request.url.path,data)
