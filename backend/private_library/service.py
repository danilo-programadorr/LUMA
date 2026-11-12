import hashlib, json
from pydantic import ValidationError
from sqlalchemy import select
from backend.app.errors import Fault
from backend.app.models import ident
from backend.app.database import version
from backend.device_protocol import SignedDeviceRequest
from backend.research.transient import TransientDisplay
from .contracts import (SourceMetadata, LibraryHeartbeat, LibraryScope, LibraryRegister,
                        LibraryQueryCreate, LibraryDelivery, LibraryCheck, Empty)
from .contracts import source_id

TERMINAL = {'COMPLETED', 'FAILED', 'CANCELLED'}

class LibraryService:
    def __init__(self, control, devices):
        self.control, self.devices, self.store = control, devices, control.store
        self.display = TransientDisplay(ttl=120)
        with self.store.read() as r:
            if r.connection.execute(select(version.c.version)).scalar_one() not in (8,9):
                raise ValueError('LIBRARY_MIGRATION_REQUIRED')

    def now(self):
        return self.devices.seconds()

    def event(self, r, kind, row=None, result='OK'):
        row = row or {}
        self.control.event(r, row.get('principal_id'), row.get('project_id'), kind, result,
                           row.get('query_id') or row.get('source_id') or 'private-library')

    def owner(self, r, owner, project, recent=False):
        p = self.devices.owner(r, owner, recent)
        self.control._check(r, p, project, 'knowledge', 'knowledge.read')
        return p

    def device(self, r, did):
        d = r.get('device_identities', did)
        if not d:
            raise Fault('DEVICE_UNKNOWN', 404)
        if d['status'] != 'ACTIVE':
            raise Fault('DEVICE_REVOKED' if d['status'] == 'REVOKED' else 'DEVICE_NOT_ACTIVE', 403)
        self.devices.binding(r, d)
        return d

    def current(self, r, d):
        self.devices.binding(r, d)
        if d['status'] != 'ACTIVE':
            raise Fault('DEVICE_REVOKED', 403)
        p = self.control._principal(r, d['principal_id'])
        self.devices.execution.owner(r, p, d['project_id'])
        self.control._check(r, p, d['project_id'], 'knowledge', 'knowledge.read')
        g = r.get('library_devices', d['device_id'])
        if not g or not g['enabled'] or g['principal_id'] != d['principal_id'] or g['project_id'] != d['project_id']:
            raise Fault('LIBRARY_CAPABILITY_REQUIRED', 403)
        return g

    def online(self, r, d):
        g = self.current(r, d)
        return self.devices.public(d)['online'] and g['reported'] and 0 <= self.now() - g['last_seen'] <= 45

    def devices_for(self, owner):
        with self.store.read() as r:
            self.devices.owner(r, owner)
            result=[]
            for d in r.rows('device_identities',principal_id=owner.internal_owner_id):
                if d['principal_id']!=owner.internal_owner_id:continue
                public=self.devices.public(d)
                grant=r.get('library_devices',d['device_id']) or {}
                enabled=bool(grant.get('enabled'))
                online=bool(public['online'] and enabled and grant.get('reported') and 0<=self.now()-grant.get('last_seen',0)<=45)
                result.append({**public,'private_library_approved':enabled,'private_library_online':online})
            return result

    def grant(self, owner, did, enabled):
        with self.store.transaction() as r:
            d = self.device(r, did)
            self.owner(r, owner, d['project_id'], recent=enabled)
            if d['principal_id'] != owner.internal_owner_id:
                raise Fault('LIBRARY_SCOPE', 403)
            row = dict(device_id=did, principal_id=d['principal_id'], project_id=d['project_id'], enabled=enabled, reported=False, last_seen=0)
            (r.put if r.get('library_devices', did) else r.add)('library_devices', did, row)
            if not enabled:
                self.cancel_pending(r, d['principal_id'], did=did, code='LIBRARY_CAPABILITY_REQUIRED')
            self.event(r, 'LIBRARY_DEVICE_POLICY_CHANGED', row)
            return {'device_id': did, 'private_library_approved': enabled}

    def public_source(self, row):
        return {k: row[k] for k in SourceMetadata.model_fields} | {'status': row['status']}

    def sources(self, owner, project):
        with self.store.read() as r:
            self.owner(r, owner, project)
            return [self.public_source(s) for s in r.rows('library_sources', principal_id=owner.internal_owner_id, projects=(project,))
                    if s['principal_id'] == owner.internal_owner_id and s['project_id'] == project]

    def cancel_pending(self, r, owner_id, *, did=None, sid=None, code):
        for row in r.rows('library_queries', principal_id=owner_id):
            if row['principal_id'] != owner_id or (did and row['target_device_id'] != did) or (sid and sid not in row['source_ids']):
                continue
            if row['status'] not in TERMINAL:
                row.update(status='CANCELLED', error_code=code)
                r.put('library_queries', row['query_id'], row)
                self.event(r, 'LIBRARY_QUERY_CANCELLED', row, code)
            self.display.consume(row['query_id'], owner_id)

    def archive(self, owner, project, sid):
        with self.store.transaction() as r:
            self.owner(r, owner, project)
            row = r.get('library_sources', sid)
            if not row or row['principal_id'] != owner.internal_owner_id or row['project_id'] != project:
                raise Fault('NOT_FOUND', 404)
            if row['status'] != 'ARCHIVED':
                row.update(status='ARCHIVED')
                r.put('library_sources', sid, row)
                self.cancel_pending(r, owner.internal_owner_id, sid=sid, code='LIBRARY_SOURCE_ARCHIVED')
                self.event(r, 'LIBRARY_SOURCE_ARCHIVED', row)
            return self.public_source(row)

    def create(self, owner, data):
        self.control.safe(data)
        body = LibraryQueryCreate.model_validate(data)
        digest = hashlib.sha256(json.dumps(body.model_dump(), sort_keys=True).encode()).hexdigest()
        qid = hashlib.sha256((owner.internal_owner_id + ':' + body.project_id + ':' + body.idempotency_key).encode()).hexdigest()[:32]
        with self.store.transaction() as r:
            self.owner(r, owner, body.project_id)
            d = self.device(r, body.target_device_id)
            if d['principal_id'] != owner.internal_owner_id or d['project_id'] != body.project_id:
                raise Fault('LIBRARY_SCOPE', 403)
            online = self.online(r, d)
            existing = r.get('library_queries', qid)
            if existing:
                if existing['digest'] != digest:
                    raise Fault('IDEMPOTENCY_CONFLICT', 409)
                return self.view(existing)
            sources = [s for s in r.rows('library_sources', principal_id=owner.internal_owner_id, projects=(body.project_id,))
                       if s['status'] == 'ACTIVE' and s['device_id'] == d['device_id'] and s['project_id'] == body.project_id and s['principal_id'] == owner.internal_owner_id]
            allowed = {s['source_id'] for s in sources}
            if body.source_ids and not set(body.source_ids) <= allowed:
                raise Fault('LIBRARY_SOURCE_UNAVAILABLE', 403)
            selected = sorted(set(body.source_ids) if body.source_ids else allowed)
            if not selected:
                raise Fault('LIBRARY_NO_SOURCES', 400)
            self.devices.rate(r, 'library-owner-' + owner.internal_owner_id, 6)
            pending = [q for q in r.rows('library_queries', principal_id=owner.internal_owner_id) if q['status'] not in TERMINAL and q['expires_at'] > self.now()]
            if len(pending) >= 16:
                raise Fault('LIBRARY_QUERY_LIMIT', 429)
            row = dict(query_id=qid, digest=digest, principal_id=owner.internal_owner_id, project_id=body.project_id,
                       target_device_id=d['device_id'], query=body.query, source_ids=selected,
                       status='ANALYZING' if online else 'WAITING_FOR_DEVICE', error_code=None,
                       requested_at=self.now(), expires_at=self.now() + 180, lease_id=None, lease_until=0, attempts=0)
            r.add('library_queries', qid, row)
            self.event(r, 'LIBRARY_QUERY_REQUESTED', row)
            return self.view(row)

    def view(self, row):
        return {k: row.get(k) for k in ('query_id', 'project_id', 'target_device_id', 'status', 'error_code', 'requested_at')} | {'source_count': len(row['source_ids']), 'result': None}

    def expire(self, r, row):
        if row['status'] not in TERMINAL and (row['expires_at'] <= self.now() or row['lease_id'] and row['lease_until'] <= self.now()):
            row.update(status='FAILED', error_code='LIBRARY_QUERY_EXPIRED')
            r.put('library_queries', row['query_id'], row)
            self.event(r, 'LIBRARY_QUERY_FAILED', row, row['error_code'])
        return row

    def source_current(self, r, row, sid):
        s = r.get('library_sources', sid)
        if not s or s['status'] != 'ACTIVE' or s['source_id'] not in row['source_ids'] or s['principal_id'] != row['principal_id'] or s['project_id'] != row['project_id'] or s['device_id'] != row['target_device_id']:
            raise Fault('LIBRARY_SOURCE_UNAVAILABLE', 403)
        return s

    def get(self, owner, qid, cancel=False):
        with self.store.transaction() as r:
            row = r.get('library_queries', qid)
            if not row or row['principal_id'] != owner.internal_owner_id:
                raise Fault('NOT_FOUND', 404)
            self.owner(r, owner, row['project_id'])
            d = self.device(r, row['target_device_id'])
            self.current(r, d)
            self.expire(r, row)
            if cancel and row['status'] not in TERMINAL:
                row.update(status='CANCELLED', error_code=None)
                r.put('library_queries', qid, row)
                self.display.consume(qid, owner.internal_owner_id)
                self.event(r, 'LIBRARY_QUERY_CANCELLED', row)
            view = self.view(row)
            if row['status'] == 'COMPLETED':
                data = self.display.consume(qid, owner.internal_owner_id)
                if data is not None:
                    try:
                        for sid in row['source_ids']:
                            self.source_current(r, row, sid)
                        data = {'matches': [{**m, 'source': self.public_source(self.source_current(r, row, m['source_id']))} for m in data['matches']]}
                    except Fault:
                        data = None
                view.update(result=data, display_status='LIVE' if data is not None else 'PRIVATE_RESULT_NOT_RETAINED')
            return view

    def poll(self, r, d):
        if not self.online(r, d):
            return {'request': None, 'status': 'WAITING_FOR_DEVICE'}
        for row in r.rows('library_queries', principal_id=d['principal_id'], projects=(d['project_id'],)):
            if row['target_device_id'] != d['device_id'] or row['project_id'] != d['project_id'] or row['principal_id'] != d['principal_id']:
                continue
            self.expire(r, row)
            if row['status'] in TERMINAL or row['lease_id']:
                continue
            for sid in row['source_ids']:
                self.source_current(r, row, sid)
            row.update(status='READING_SOURCES', lease_id=ident(), lease_until=self.now() + 60, attempts=row['attempts'] + 1)
            r.put('library_queries', row['query_id'], row)
            self.event(r, 'LIBRARY_QUERY_STARTED', row)
            request = {k: row[k] for k in ('query_id', 'project_id', 'query', 'source_ids', 'target_device_id', 'expires_at')}
            return {'request': request, 'lease_id': row['lease_id']}
        return {'request': None}

    def handle(self, path, data):
        error = None
        transient = None
        response = None
        with self.store.transaction() as r:
            try:
                body = SignedDeviceRequest.model_validate(data)
                _, d = self.devices.auth.authenticate(r, path, body)
                self.current(r, d)
                op = path.rsplit('/', 1)[-1]
                if op == 'check':
                    scope = LibraryCheck.model_validate(body.payload)
                    if scope.project_id != d['project_id']:
                        raise Fault('LIBRARY_SCOPE', 403)
                    if scope.query_id:
                        row=r.get('library_queries',scope.query_id)
                        if not row or row['target_device_id']!=d['device_id'] or row['project_id']!=d['project_id'] or row['principal_id']!=d['principal_id']:raise Fault('LIBRARY_SCOPE',403)
                        self.expire(r,row)
                        if row['status'] in TERMINAL or row['lease_id']!=scope.lease_id or row['lease_until']<=self.now():raise Fault('LIBRARY_LEASE_INVALID',409)
                        for sid in row['source_ids']:self.source_current(r,row,sid)
                    response = {'status': 'AUTHORIZED', 'project_id': d['project_id']}
                elif op == 'heartbeat':
                    LibraryHeartbeat.model_validate(body.payload)
                    row = r.get('library_devices', d['device_id'])
                    row.update(reported=True, last_seen=self.now())
                    r.put('library_devices', d['device_id'], row)
                    response = {'status': 'ACCEPTED'}
                elif op == 'register':
                    meta = LibraryRegister.model_validate(body.payload).source
                    self.control.safe(meta.model_dump())
                    if meta.device_id != d['device_id'] or meta.project_id != d['project_id'] or meta.source_id != source_id(meta.project_id, d['device_id'], meta.content_hash):
                        raise Fault('LIBRARY_SCOPE', 403)
                    old = r.get('library_sources', meta.source_id)
                    if old and old['status'] != 'ACTIVE':
                        raise Fault('LIBRARY_SOURCE_ARCHIVED', 409)
                    if not old:
                        if len([s for s in r.rows('library_sources', principal_id=d['principal_id'], projects=(d['project_id'],)) if s['device_id'] == d['device_id']]) >= 500:
                            raise Fault('LIBRARY_SOURCE_LIMIT', 429)
                        row = {**meta.model_dump(), 'principal_id': d['principal_id'], 'status': 'ACTIVE'}
                        r.add('library_sources', meta.source_id, row)
                        self.event(r, 'LIBRARY_SOURCE_REGISTERED', row)
                    response = {'status': 'REGISTERED', 'source_id': meta.source_id}
                elif op == 'poll':
                    Empty.model_validate(body.payload)
                    response = self.poll(r, d)
                elif op == 'result':
                    parsed = LibraryDelivery.model_validate(body.payload)
                    row = r.get('library_queries', parsed.query_id)
                    if not row or row['target_device_id'] != d['device_id'] or row['principal_id'] != d['principal_id'] or row['project_id'] != d['project_id']:
                        raise Fault('LIBRARY_SCOPE', 403)
                    self.expire(r, row)
                    if row['status'] in TERMINAL or row['lease_id'] != parsed.lease_id or row['lease_until'] <= self.now():
                        raise Fault('LIBRARY_LEASE_INVALID', 409)
                    for sid in row['source_ids']:
                        self.source_current(r, row, sid)
                    seen = set()
                    for m in parsed.matches:
                        source = self.source_current(r, row, m.source_id)
                        if m.source_hash != source['content_hash'] or m.line_end < m.line_start or (m.page is None) != (source['page_count'] == 0) or (m.page is not None and m.page > source['page_count']) or (m.source_id, m.chunk_id) in seen:
                            raise Fault('LIBRARY_EVIDENCE_INVALID', 400)
                        seen.add((m.source_id, m.chunk_id))
                    if parsed.error_code and parsed.matches:
                        raise Fault('LIBRARY_EVIDENCE_INVALID', 400)
                    row.update(status='FAILED' if parsed.error_code else 'COMPLETED', error_code=parsed.error_code)
                    r.put('library_queries', row['query_id'], row)
                    self.event(r, 'LIBRARY_QUERY_' + row['status'], row, parsed.error_code or 'OK')
                    if not parsed.error_code:
                        transient = (row['query_id'], row['principal_id'], {'matches': [m.model_dump() for m in parsed.matches]})
                    response = {'status': row['status']}
                else:
                    raise Fault('LIBRARY_OPERATION_INVALID', 400)
                response.update(request_nonce=body.nonce, device_id=d['device_id'])
            except (Fault, ValidationError) as exc:
                error = exc if isinstance(exc, Fault) else Fault('LIBRARY_REQUEST_INVALID', 400)
                self.event(r, 'LIBRARY_REQUEST_REJECTED', result=error.code)
        if error:
            raise error
        if transient:
            self.display.put(*transient)
        return response
