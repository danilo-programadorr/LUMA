import hashlib,time,uuid,threading
from device_agent.client import DeviceClient,ChannelError
from backend.device_protocol import SignedDeviceRequest,canonical,request_bytes,encode,CAPABILITIES
from backend.research.contracts import ResearchRequest
class ResearchClient(DeviceClient):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.transport_lock=threading.RLock()
    def research(self,operation,payload):
        with self.transport_lock:return self._research(operation,payload)
    def _research(self,operation,payload):
        from device_agent.transport_lock import locked_identity
        with locked_identity(self.identity):return self._research_unlocked(operation,payload)
    def _research_unlocked(self,operation,payload):
        path='/v1/research-runtime/'+operation;did,_=self.identity.binding()
        if not did:raise ChannelError('DEVICE_ENROLLMENT_REQUIRED')
        b=SignedDeviceRequest(device_id=did,timestamp=int(time.time()),sequence=self.identity.reserve(),nonce=uuid.uuid4().hex,payload_hash=hashlib.sha256(canonical(payload)).hexdigest(),payload=payload,signature='A'*88)
        b=b.model_copy(update={'signature':encode(self.identity.key().sign(request_bytes(path,b)))})
        result=self.send(path,b.model_dump())
        if result.get('request_nonce')!=b.nonce or result.get('device_id')!=did:raise ChannelError('DEVICE_RESPONSE_CORRELATION_INVALID')
        return result
    def heartbeat(self):
        with self.transport_lock:self._heartbeat()
    def _heartbeat(self):
        self.signed('heartbeat',{'runtime_version':'0.6.0rc1','capabilities':list(CAPABILITIES),'health':'OK','current_load':0})
        self.research('heartbeat',{'protocol_version':'1','capability':'WEB_RESEARCH'})
    def cycle(self,processor):
        self.heartbeat();response=self.research('poll',{})
        if not response.get('request'):return {'status':'IDLE'}
        request=ResearchRequest.model_validate(response['request'])
        if request.target_device_id!=self.identity.binding()[0]:raise ChannelError('RESEARCH_SCOPE')
        lease={'research_id':request.research_id,'lease_id':response['lease_id']}
        def check():
            if self.stop.is_set():raise ChannelError('RESEARCH_CANCELLED')
            self.heartbeat();self.research('check',lease)
        finished=threading.Event();heartbeat_error=[]
        def keepalive():
            while not finished.wait(10):
                try:self.heartbeat();self.research('check',lease)
                except ChannelError as error:heartbeat_error.append(error);return
        worker=threading.Thread(target=keepalive,daemon=True);worker.start()
        try:result=processor.process(request,progress=lambda stage:self.research('progress',{**lease,'stage':stage}),check=check)
        finally:finished.set();worker.join(timeout=35)
        if heartbeat_error:raise heartbeat_error[0]
        check();return self.research('result',{**lease,'result':result.model_dump()})
