from fastapi import Request
from backend.app.errors import Fault
from .contracts import LibraryGrant, LibraryQueryCreate, Empty

def install(app, service):
    def owner(request):
        value = getattr(request.state, 'owner', None)
        if value is None:
            raise Fault('UNAUTHORIZED', 401)
        return value

    @app.get('/v1/library/devices')
    def devices(request: Request):
        return service.devices_for(owner(request))

    @app.post('/v1/library/devices/{did}/capability')
    def grant(did: str, body: LibraryGrant, request: Request):
        return service.grant(owner(request), did, body.enabled)

    @app.get('/v1/library/projects/{project}/sources')
    def sources(project: str, request: Request):
        return service.sources(owner(request), project)

    @app.post('/v1/library/projects/{project}/sources/{sid}/archive')
    def archive(project: str, sid: str, body: Empty, request: Request):
        return service.archive(owner(request), project, sid)

    @app.post('/v1/library/queries')
    def create(body: LibraryQueryCreate, request: Request):
        return service.create(owner(request), body.model_dump())

    @app.get('/v1/library/queries/{qid}')
    def get(qid: str, request: Request):
        return service.get(owner(request), qid)

    @app.post('/v1/library/queries/{qid}/cancel')
    def cancel(qid: str, body: Empty, request: Request):
        return service.get(owner(request), qid, cancel=True)

    @app.post('/v1/library-runtime/{operation}')
    async def runtime(operation: str, request: Request):
        try:
            data = await request.json()
        except Exception:
            raise Fault('LIBRARY_REQUEST_INVALID', 400) from None
        return service.handle(request.url.path, data)
