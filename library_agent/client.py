import hashlib, json, time, uuid
from urllib.parse import urlsplit
import requests
from pydantic import ValidationError
from backend.device_protocol import SignedDeviceRequest, canonical, request_bytes, encode, CAPABILITIES
from backend.app.errors import Fault
from backend.private_library.contracts import LibraryWork
from device_agent.client import DeviceClient, ChannelError
from device_agent.transport_lock import locked_identity

class LibraryClient(DeviceClient):
    def __init__(self, identity, base='http://127.0.0.1:8770', transport=None):
        u = urlsplit(base)
        if u.scheme != 'http' or u.hostname not in ('localhost', '127.0.0.1'):
            raise ValueError('LIBRARY_LOCAL_ENDPOINT_REQUIRED')
        super().__init__(identity, base, transport)
        if transport is None:
            self.transport.trust_env = False

    def send(self, path, data):
        try:
            r = self.transport.post(self.base + path, json=data, timeout=15, allow_redirects=False)
        except requests.RequestException:
            raise ChannelError('DEVICE_NETWORK_UNAVAILABLE') from None
        if r.status_code != 200:
            code = 'LIBRARY_REQUEST_REJECTED'
            try:
                value = r.json().get('error', {}).get('code', '')
                if isinstance(value, str) and len(value) < 80 and all(c.isupper() or c == '_' for c in value):
                    code = value
            except Exception:
                pass
            raise ChannelError(code)
        try:
            if len(r.content) > 65536:
                raise ValueError()
            return r.json()
        except Exception:
            raise ChannelError('DEVICE_RESPONSE_INVALID') from None

    def library(self, operation, payload):
        path = '/v1/library-runtime/' + operation
        with locked_identity(self.identity):
            did, _ = self.identity.binding()
            if not did:
                raise ChannelError('DEVICE_ENROLLMENT_REQUIRED')
            body = SignedDeviceRequest(device_id=did, timestamp=int(time.time()), sequence=self.identity.reserve(),
                                       nonce=uuid.uuid4().hex, payload_hash=hashlib.sha256(canonical(payload)).hexdigest(),
                                       payload=payload, signature='A' * 88)
            body = body.model_copy(update={'signature': encode(self.identity.key().sign(request_bytes(path, body)))})
            result = self.send(path, body.model_dump())
            if result.get('request_nonce') != body.nonce or result.get('device_id') != did:
                raise ChannelError('DEVICE_RESPONSE_CORRELATION_INVALID')
            return result

    def heartbeat(self):
        self.signed('heartbeat', {'runtime_version': '0.6.0rc1', 'capabilities': list(CAPABILITIES), 'health': 'OK', 'current_load': 0})
        self.library('heartbeat', {'protocol_version': '1', 'capability': 'PRIVATE_LIBRARY'})

    def cycle(self, store):
        self.heartbeat()
        response = self.library('poll', {})
        if not response.get('request'):
            return {'status': 'IDLE'}
        try:
            job = LibraryWork.model_validate(response['request'])
        except ValidationError:
            raise ChannelError('LIBRARY_REQUEST_INVALID') from None
        if job.target_device_id != self.identity.binding()[0] or job.expires_at <= int(time.time()):
            raise ChannelError('LIBRARY_SCOPE')
        lease = {'project_id': job.project_id, 'query_id': job.query_id, 'lease_id': response['lease_id']}
        self.library('check', lease)
        if self.stop.is_set():
            raise ChannelError('LIBRARY_CANCELLED')
        code = None
        matches = []
        try:
            matches = [m.model_dump() for m in store.retrieve(job.project_id, job.query, job.source_ids)]
        except Exception as exc:
            code = exc.code if isinstance(exc, Fault) and exc.code in ('LIBRARY_STORAGE_INTEGRITY', 'LIBRARY_SOURCE_UNAVAILABLE', 'LIBRARY_QUERY_INVALID') else 'LIBRARY_LOCAL_FAILURE'
        self.library('check', lease)
        if self.stop.is_set():
            raise ChannelError('LIBRARY_CANCELLED')
        return self.library('result', {'query_id': job.query_id, 'lease_id': response['lease_id'], 'matches': matches, 'error_code': code})
