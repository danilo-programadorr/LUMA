from fastapi import Request
from pydantic import Field
from .app.models import Contract
from .app.errors import Fault
from .device_protocol import EnrollmentStart
class Approve(Contract):
    fingerprint:str=Field(pattern=r'^[a-f0-9]{64}$')
class Empty(Contract):pass
class SafeTest(Contract):
    confirmation:str=Field(pattern=r'^AUTHORIZE_SYNTHETIC_TEST_ONLY$')

def install(app,service):
    def owner(request):
        value=getattr(request.state,'owner',None)
        if value is None:raise Fault('UNAUTHORIZED',401)
        return value
    async def body_json(request):
        try:return await request.json()
        except Exception:raise Fault('DEVICE_REQUEST_INVALID',400) from None
    @app.get('/v1/devices')
    def listing(request:Request):return service.listing(owner(request))
    @app.post('/v1/devices/enrollment/start')
    def start(body:EnrollmentStart,request:Request):return service.start(owner(request),body.display_name)
    @app.post('/v1/devices/enrollment/complete')
    async def complete(request:Request):return service.complete(await body_json(request))
    @app.post('/v1/devices/{did}/approve')
    def approve(did:str,body:Approve,request:Request):return service.change(owner(request),did,'approve',body.fingerprint)
    @app.post('/v1/devices/{did}/revoke')
    def revoke(did:str,body:Empty,request:Request):return service.change(owner(request),did,'revoke')
    @app.post('/v1/devices/{did}/rename')
    def rename(did:str,body:EnrollmentStart,request:Request):return service.change(owner(request),did,'rename',body.display_name)
    @app.post('/v1/devices/{did}/test-job')
    def test_job(did:str,body:SafeTest,request:Request):return service.test_job(owner(request),did)
    @app.post('/v1/device-runtime/heartbeat')
    @app.post('/v1/device-runtime/poll')
    @app.post('/v1/device-runtime/result')
    async def signed(request:Request):return service.handle(request.url.path,await body_json(request))
