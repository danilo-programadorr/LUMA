import hashlib,time,uuid,random,threading
from urllib.parse import urlsplit
import requests
from backend.device_protocol import EnrollmentComplete,enrollment_bytes,encode,SignedDeviceRequest,request_bytes,canonical,CAPABILITIES
class ChannelError(Exception):pass
def endpoint(url):
    u=urlsplit(url)
    if u.username or u.password or u.query or u.fragment or u.path not in ('','/') or not u.hostname:raise ValueError('DEVICE_ENDPOINT_INVALID')
    if u.scheme!='https' and not (u.scheme=='http' and u.hostname in ('localhost','127.0.0.1')):raise ValueError('DEVICE_HTTPS_REQUIRED')
    return url.rstrip('/')
class DeviceClient:
    def __init__(self,identity,base,transport=None,*,timeout=15):
        if not isinstance(timeout,(int,float)) or not 1<=timeout<=15:raise ValueError('DEVICE_TIMEOUT_INVALID')
        self.timeout=timeout
        self.identity=identity;self.base=endpoint(base);self.transport=transport or requests.Session();self.stop=threading.Event();self.lease=None
        did,bound=self.identity.binding()
        if bound and bound!=self.base:raise ValueError('DEVICE_ENDPOINT_REBIND_DENIED')
    def send(self,path,data):
        try:r=self.transport.post(self.base+path,json=data,timeout=self.timeout,allow_redirects=False)
        except requests.RequestException:raise ChannelError('DEVICE_NETWORK_UNAVAILABLE') from None
        if r.status_code!=200:
            code='DEVICE_REQUEST_REJECTED'
            try:
                value=r.json().get('error',{}).get('code','')
                if isinstance(value,str) and len(value)<80 and all(x.isupper() or x=='_' for x in value):code=value
            except Exception:pass
            raise ChannelError(code)
        try:
            if len(r.content)>16384:raise ValueError()
            return r.json()
        except Exception:raise ChannelError('DEVICE_RESPONSE_INVALID') from None
    def enroll(self,challenge_id,code):
        if self.identity.binding()[0]:raise ChannelError('DEVICE_ALREADY_ENROLLED')
        body=EnrollmentComplete(challenge_id=challenge_id,code=code,public_key=self.identity.public(),signature='A'*88)
        body=body.model_copy(update={'signature':encode(self.identity.key().sign(enrollment_bytes(body)))})
        result=self.send('/v1/devices/enrollment/complete',body.model_dump())
        if result.get('key_fingerprint')!=self.identity.fingerprint() or result.get('status')!='PENDING_ENROLLMENT':raise ChannelError('DEVICE_RESPONSE_INVALID')
        self.identity.bind(result['device_id'],self.base);return result
    def signed(self,operation,payload):
        from .transport_lock import locked_identity
        with locked_identity(self.identity):return self._signed(operation,payload)
    def _signed(self,operation,payload):
        did,_=self.identity.binding()
        if not did:raise ChannelError('DEVICE_ENROLLMENT_REQUIRED')
        path='/v1/device-runtime/'+operation
        body=SignedDeviceRequest(device_id=did,timestamp=int(time.time()),sequence=self.identity.reserve(),nonce=uuid.uuid4().hex,payload_hash=hashlib.sha256(canonical(payload)).hexdigest(),payload=payload,signature='A'*88)
        body=body.model_copy(update={'signature':encode(self.identity.key().sign(request_bytes(path,body)))})
        result=self.send(path,body.model_dump())
        if result.get('request_nonce')!=body.nonce or result.get('device_id')!=did:raise ChannelError('DEVICE_RESPONSE_CORRELATION_INVALID')
        return result
    def once(self):
        self.signed('heartbeat',{'runtime_version':'0.6.0rc1','capabilities':list(CAPABILITIES),'health':'OK','current_load':0})
        result=self.signed('poll',{})
        job=result.get('job')
        if job:
            if job.get('tool')!='SAFE_TEST_TOOL' or job.get('operation')!='SYNTHETIC_OK' or job.get('device_id')!=self.identity.binding()[0] or job.get('device_protocol_version')!='1':raise ChannelError('DEVICE_UNSUPPORTED_JOB')
            self.lease={'job_id':job['job_id'],'lease_id':job['lease_id']}
            if self.stop.is_set():return
            self.signed('result',{**self.lease,'outcome':'SYNTHETIC_OK'});self.lease=None
        return {'heartbeat':'ACCEPTED','synthetic_job_completed':bool(job)}
    def run(self):
        failures=0
        try:
            while not self.stop.is_set():
                try:self.once();failures=0
                except ChannelError as e:
                    if str(e) in ('DEVICE_REVOKED','OWNER_BINDING_INACTIVE','DEVICE_OWNER_MISMATCH'):raise
                    failures=min(failures+1,5)
                self.stop.wait(min(60,10*2**failures)+random.uniform(0,2))
        finally:
            if self.lease:
                try:self.signed('result',{**self.lease,'outcome':'RELEASE'})
                except ChannelError:pass
