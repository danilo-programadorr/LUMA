"""Owner-approved device channel. All policy/replay/job transitions share the DB lock."""
import hashlib,secrets,time
from datetime import timedelta
from sqlalchemy import select
from pydantic import ValidationError
from . import device_schema
from .owner_schema import owner_bindings
from .owner_auth import require_recent_auth
from .device_protocol import *
from .app.models import ident
from .app.control import date
from .app.execution_contracts import CanonicalActionEnvelope

SKEW_SECONDS=180
ONLINE_SECONDS=45
ENROLLMENT_SECONDS=300
LEASE_SECONDS=30

class DeviceAuthenticator:
    def __init__(self,service):self.service=service
    def authenticate(self,repo,path,body):
        s=self.service;row=repo.get('device_identities',body.device_id)
        if not row:raise Fault('DEVICE_UNKNOWN',401)
        s.rate(repo,'device-'+body.device_id,120)
        if row['status']=='REVOKED':raise Fault('DEVICE_REVOKED',403)
        if row['status']!='ACTIVE':raise Fault('DEVICE_NOT_ACTIVE',403)
        s.binding(repo,row)
        verify(row['public_key'],body.signature,request_bytes(path,body))
        if hashlib.sha256(canonical(body.payload)).hexdigest()!=body.payload_hash:raise Fault('DEVICE_SIGNATURE_INVALID',401)
        if abs(s.seconds()-body.timestamp)>SKEW_SECONDS:raise Fault('DEVICE_CLOCK_SKEW',401)
        if body.sequence<=row['sequence'] or body.nonce in row['nonces']:raise Fault('DEVICE_REPLAY_DETECTED',409)
        row.update(sequence=body.sequence,nonces=(row['nonces']+[body.nonce])[-1024:])
        repo.put('device_identities',row['device_id'],row)
        return AuthenticatedDevicePrincipal(row['device_id'],row['owner_binding_id'],row['key_fingerprint'],body.sequence),row

class DeviceService:
    def __init__(self,control,execution):
        self.control=control;self.store=control.store;self.execution=execution;self.auth=DeviceAuthenticator(self)
    def seconds(self):return int(self.execution.clock().timestamp())
    def stamp(self):return self.execution.clock().isoformat()
    def event(self,r,kind,result='OK',correlation='device'):
        self.control.event(r,None,None,kind,result,correlation)
    def rate(self,r,key,maximum):
        now=self.seconds();row=r.get('device_rate_limits',key)
        if not row:row={'window':now,'count':0};r.add('device_rate_limits',key,row)
        if now-row['window']>=60:row.update(window=now,count=0)
        if row['count']>=maximum:raise Fault('DEVICE_RATE_LIMITED',429)
        row['count']+=1;r.put('device_rate_limits',key,row)
    def binding(self,r,row=None,owner=None):
        b=r.connection.execute(select(owner_bindings).where(owner_bindings.c.id==1)).mappings().first()
        if not b or b['status']!='ACTIVE':raise Fault('OWNER_BINDING_INACTIVE',403)
        digest=hashlib.sha256(canonical({'uid':b['subject_uid'],'owner':b['internal_owner_id'],'bound_at':b['bound_at']})).hexdigest()
        if row and row['owner_binding_fingerprint']!=digest:raise Fault('DEVICE_OWNER_MISMATCH',403)
        if owner and owner.internal_owner_id!=b['internal_owner_id']:raise Fault('DEVICE_OWNER_MISMATCH',403)
        return b,digest
    def owner(self,r,owner,recent=False):
        if owner is None:raise Fault('UNAUTHORIZED',401)
        self.binding(r,owner=owner)
        p=self.control._principal(r,owner.internal_owner_id)
        if p.principal_type!='HUMAN_OWNER':raise Fault('FORBIDDEN',403)
        self.execution.owner(r,p,'meu-gestor')
        if recent:require_recent_auth(owner)
        return p
    def public(self,row):
        keys=('device_id','display_name','device_type','platform','status','enrollment_status','key_algorithm','key_fingerprint','created_at','enrolled_at','last_seen_at','last_heartbeat_at','last_poll_at','revoked_at','revocation_reason','protocol_version','runtime_version','capabilities','key_version')
        out={k:row.get(k) for k in keys}
        online=row['status']=='ACTIVE' and row.get('last_heartbeat_at') is not None and 0<=self.seconds()-int(date(row['last_heartbeat_at']).timestamp())<=ONLINE_SECONDS and row.get('health')=='OK'
        out.update(online=online,connection_status='ONLINE' if online else 'OFFLINE',future_capabilities={x:False for x in FUTURE_CAPABILITIES})
        if row['status']=='ACTIVE' and not online:out['status']='ERROR' if row.get('last_heartbeat_at') and row.get('health')=='ERROR' else 'OFFLINE'
        return out
    def listing(self,owner):
        with self.store.read() as r:
            self.owner(r,owner)
            return [self.public(x) for x in r.rows('device_identities',limit=100)]
    def start(self,owner,name):
        with self.store.transaction() as r:
            self.owner(r,owner,True);self.rate(r,'enrollment-start',5)
            if len(r.rows('device_identities',limit=100))>=100:raise Fault('DEVICE_LIMIT',409)
            b,fp=self.binding(r);cid=ident();code=secrets.token_urlsafe(32)
            row=dict(challenge_id=cid,display_name=name,owner_binding_id=1,owner_binding_fingerprint=fp,principal_id=b['internal_owner_id'],project_id='meu-gestor',status='PENDING',expires_at=self.seconds()+ENROLLMENT_SECONDS,attempts=0,code_digest=hashlib.sha256(code.encode()).hexdigest())
            r.add('device_enrollments',cid,row);self.event(r,'DEVICE_ENROLLMENT_STARTED')
            return dict(challenge_id=cid,code=code,expires_at=row['expires_at'])
    def complete(self,data):
        error=None;result=None
        with self.store.transaction() as r:
            try:
                self.rate(r,'enrollment-complete',30)
                body=EnrollmentComplete.model_validate(data);row=r.get('device_enrollments',body.challenge_id)
                if not row:raise Fault('DEVICE_ENROLLMENT_UNKNOWN',401)
                if row['status']!='PENDING':raise Fault('DEVICE_ENROLLMENT_USED',409)
                if row['expires_at']<=self.seconds():raise Fault('DEVICE_ENROLLMENT_EXPIRED',403)
                if row['attempts']>=5:raise Fault('DEVICE_ENROLLMENT_LOCKED',403)
                row['attempts']+=1;r.put('device_enrollments',body.challenge_id,row)
                self.binding(r,row)
                if not secrets.compare_digest(row['code_digest'],hashlib.sha256(body.code.encode()).hexdigest()):raise Fault('DEVICE_ENROLLMENT_INVALID',401)
                verify(body.public_key,body.signature,enrollment_bytes(body));fp=fingerprint(body.public_key)
                if any(x['key_fingerprint']==fp for x in r.rows('device_identities')):raise Fault('DEVICE_KEY_ALREADY_USED',409)
                did=ident();record=dict(device_id=did,owner_binding_id=1,owner_binding_fingerprint=row['owner_binding_fingerprint'],principal_id=row['principal_id'],project_id='meu-gestor',display_name=row['display_name'],device_type='PC',platform='WINDOWS',status='PENDING_ENROLLMENT',enrollment_status='AWAITING_OWNER',public_key=body.public_key,key_algorithm='Ed25519',key_fingerprint=fp,key_version=1,rotation_policy='NEW_OWNER_APPROVED_ENROLLMENT_REQUIRED',created_at=self.stamp(),approval_expires_at=self.seconds()+ENROLLMENT_SECONDS,enrolled_at=None,last_seen_at=None,last_heartbeat_at=None,last_poll_at=None,revoked_at=None,revocation_reason=None,protocol_version='1',runtime_version=None,capabilities=list(CAPABILITIES),sequence=0,nonces=[],health='ERROR',current_load=0)
                r.add('device_identities',did,record);row.update(status='USED');r.put('device_enrollments',body.challenge_id,row)
                self.event(r,'DEVICE_ENROLLMENT_REQUESTED',correlation=did);result=self.public(record)
            except (Fault,ValidationError) as exc:
                error=exc if isinstance(exc,Fault) else Fault('DEVICE_REQUEST_INVALID',400)
                if error.code!='DEVICE_RATE_LIMITED':self.event(r,'DEVICE_ENROLLMENT_DENIED',error.code)
        if error:raise error
        return result
    def change(self,owner,did,operation,value=None):
        with self.store.transaction() as r:
            self.owner(r,owner,operation=='approve');row=r.get('device_identities',did)
            if not row:raise Fault('DEVICE_UNKNOWN',404)
            self.binding(r,row)
            if operation=='approve':
                if row['approval_expires_at']<=self.seconds():raise Fault('DEVICE_ENROLLMENT_EXPIRED',403)
                if row['status']!='PENDING_ENROLLMENT' or value!=row['key_fingerprint']:raise Fault('DEVICE_APPROVAL_MISMATCH',409)
                row.update(status='ACTIVE',enrollment_status='APPROVED',enrolled_at=self.stamp())
                legacy=dict(device_id=did,name=row['display_name'],device_type='WINDOWS',owner_principal_id=owner.internal_owner_id,principal_id=owner.internal_owner_id,project_id='meu-gestor',status='OFFLINE',last_seen_at=None,capabilities=['sandbox-test'] if self.execution.sandbox else [],reported_capabilities=[],enabled=True,revoked_at=None,current_job_count=0,auth_scheme='Ed25519')
                r.add('execution_devices',did,legacy);kind='DEVICE_ENROLLMENT_APPROVED'
            elif operation=='revoke':
                row.update(status='REVOKED',revoked_at=self.stamp(),revocation_reason='OWNER_REVOKED');kind='DEVICE_REVOKED'
                legacy=r.get('execution_devices',did)
                if legacy:legacy.update(status='REVOKED',enabled=False,revoked_at=self.stamp());r.put('execution_devices',did,legacy)
            elif operation=='rename':row['display_name']=value;kind='DEVICE_RENAMED'
            else:raise Fault('DEVICE_OPERATION_INVALID',400)
            r.put('device_identities',did,row);self.event(r,kind,correlation=did);return self.public(row)
    def handle(self,path,data):
        error=None;result=None
        with self.store.transaction() as r:
            try:
                self.rate(r,'signed-global',600)
                if isinstance(data,dict) and data.get('device_protocol_version')!='1':raise Fault('DEVICE_PROTOCOL_UNSUPPORTED',400)
                body=SignedDeviceRequest.model_validate(data)
                model={'heartbeat':Heartbeat,'poll':Poll,'result':Result}[path.rsplit('/',1)[-1]]
                payload=model.model_validate(body.payload)
                principal,row=self.auth.authenticate(r,path,body)
                if r.get('system_state','global')['state']!='RUNNING':raise Fault('DEVICE_KILL_SWITCH',403)
                if isinstance(payload,Heartbeat):
                    if len(set(payload.capabilities))!=len(payload.capabilities) or not set(payload.capabilities)<=set(row['capabilities']):raise Fault('DEVICE_CAPABILITY_MISMATCH',403)
                    row.update(last_seen_at=self.stamp(),last_heartbeat_at=self.stamp(),runtime_version=payload.runtime_version,health=payload.health,current_load=payload.current_load,reported_capabilities=payload.capabilities)
                    legacy=r.get('execution_devices',row['device_id']);legacy.update(status='ONLINE' if payload.health=='OK' else 'OFFLINE',last_seen_at=self.stamp(),current_job_count=payload.current_load,reported_capabilities=legacy['capabilities'] if payload.health=='OK' and 'OUTBOUND_POLLING' in payload.capabilities else [])
                    r.put('execution_devices',row['device_id'],legacy);result={'status':'ACCEPTED'}
                elif isinstance(payload,Poll):
                    row['last_poll_at']=self.stamp();result=self.poll(r,row)
                else:result=self.result(r,row,payload)
                r.put('device_identities',row['device_id'],row)
                result={**result,'request_nonce':body.nonce,'device_id':principal.device_id}
                self.event(r,'DEVICE_'+path.rsplit('/',1)[-1].upper()+'_ACCEPTED',correlation=principal.device_id)
            except (Fault,ValidationError) as exc:
                error=exc if isinstance(exc,Fault) else Fault('DEVICE_REQUEST_INVALID',400)
                if error.code!='DEVICE_RATE_LIMITED':self.event(r,'DEVICE_'+path.rsplit('/',1)[-1].upper()+'_REJECTED',error.code)
        if error:raise error
        return result
    def poll(self,r,row):
        if 'OUTBOUND_POLLING' not in row['capabilities'] or 'OUTBOUND_POLLING' not in row.get('reported_capabilities',[]):raise Fault('DEVICE_CAPABILITY_MISMATCH',403)
        if not self.public(row)['online']:
            for job in r.rows('jobs',limit=100):
                if job['action']['execution_target']=='LOCAL_DEVICE' and job['action']['target_device_id']==row['device_id'] and job['status'] in ('SCHEDULED','READY') and date(job['scheduled_at'])<=self.execution.clock():
                    job['status']='WAITING_FOR_DEVICE';r.put('jobs',job['job_id'],job)
            return {'job':None,'status':'WAITING_FOR_DEVICE'}
        for job in r.rows('jobs',limit=100):
            action=job['action']
            if action['tool_id']=='codex-executor':continue
            if action['execution_target']!='LOCAL_DEVICE' or action['target_device_id']!=row['device_id']:continue
            if job['status'] not in ('SCHEDULED','WAITING_FOR_DEVICE','READY','LEASED'):continue
            if date(job['scheduled_at'])>self.execution.clock():continue
            if job['trigger_type']=='CONDITION' and not job['condition_satisfied']:continue
            if job['status']=='LEASED' and date(job['lease_until'])>self.execution.clock():continue
            auth=r.get('execution_authorizations',job['authorization_id'])
            try:
                self.execution.validate(r,auth,action);self.execution.late(auth,job)
                if not self.execution.devices.eligibility(r,auth,action):job['status']='WAITING_FOR_DEVICE';r.put('jobs',job['job_id'],job);continue
                if not self.execution.sandbox or action['tool_id']!='sandbox-test' or action['operation']!='record':raise Fault('EXTERNAL_EXECUTION_DISABLED',403)
            except Fault as exc:self.execution.finish(r,job,'BLOCKED',exc.code);continue
            if job['status']=='LEASED':self.event(r,'DEVICE_LEASE_RECONCILED','EXPIRED_NO_EFFECT')
            lease=ident();job.update(status='LEASED',lease_owner='device-'+row['device_id'],lease_device_id=row['device_id'],device_lease_id=lease,lease_until=(self.execution.clock()+timedelta(seconds=LEASE_SECONDS)).isoformat())
            r.put('jobs',job['job_id'],job);self.event(r,'DEVICE_JOB_CLAIMED',correlation=job['job_id'])
            return {'job':{'job_id':job['job_id'],'device_id':row['device_id'],'lease_id':lease,'lease_until':job['lease_until'],'tool':'SAFE_TEST_TOOL','operation':'SYNTHETIC_OK','device_protocol_version':'1'}}
        return {'job':None}
    def result(self,r,row,payload):
        job=r.get('jobs',payload.job_id)
        if not job or job['action']['target_device_id']!=row['device_id']:raise Fault('DEVICE_JOB_SCOPE',403)
        if job.get('completed_lease_id')==payload.lease_id and job['status']=='SUCCEEDED':return {'status':'SUCCEEDED','duplicate':True}
        if job['status']!='LEASED' or job.get('device_lease_id')!=payload.lease_id or job.get('lease_device_id')!=row['device_id'] or date(job['lease_until'])<=self.execution.clock():raise Fault('DEVICE_LEASE_INVALID',409)
        if payload.outcome=='RELEASE':
            job.update(status='READY',lease_owner=None,lease_until=None,device_lease_id=None);r.put('jobs',job['job_id'],job);return {'status':'RELEASED'}
        auth=r.get('execution_authorizations',job['authorization_id']);self.execution.validate(r,auth,job['action']);self.execution.late(auth,job)
        if not self.execution.devices.eligibility(r,auth,job['action']):raise Fault('DEVICE_OFFLINE',403)
        if not self.execution.sandbox or job['action']['tool_id']!='sandbox-test' or job['action']['operation']!='record':raise Fault('EXTERNAL_EXECUTION_DISABLED',403)
        if not r.get('sandbox_effects',job['idempotency_key']):
            r.add('sandbox_effects',job['idempotency_key'],dict(job_id=job['job_id'],project_id=job['project_id'],operation_id=ident(),synthetic=True))
            auth['executions_used']+=1;r.put('execution_authorizations',auth['authorization_id'],auth)
            rid=ident();r.add('execution_records',rid,dict(execution_id=rid,job_id=job['job_id'],principal_id=row['principal_id'],project_id=job['project_id'],status='SUCCEEDED',synthetic=True))
        job['completed_lease_id']=payload.lease_id;self.execution.finish(r,job,'SUCCEEDED','SYNTHETIC_OK')
        return {'status':'SUCCEEDED','duplicate':False}
    def test_job(self,owner,did):
        if not self.execution.sandbox:raise Fault('TEST_TOOL_DISABLED',403)
        with self.store.transaction() as r:
            p=self.owner(r,owner,True);row=r.get('device_identities',did)
            if not row or row['status']!='ACTIVE':raise Fault('DEVICE_NOT_ACTIVE',403)
            self.binding(r,row)
            if not r.get('tools','sandbox-test'):r.add('tools','sandbox-test',dict(tool_id='sandbox-test',enabled=True,capabilities=['record']))
        e=self.execution;action=CanonicalActionEnvelope(project_id='meu-gestor',tool_id='sandbox-test',operation='record',execution_target='LOCAL_DEVICE',target_device_id=did).model_dump()
        a=e.candidate(p,action,ident(),'safe-test')
        auth=e.authorize(p,a['action_id'],dict(mode='ONE_SHOT',valid_from=e.clock().isoformat(),expires_at=(e.clock()+timedelta(minutes=5)).isoformat(),max_executions=1,confirmation='AUTHORIZE_EXACT_ACTION',late_execution_policy='RUN_LATE_WITHIN_GRACE',grace_seconds=300),ident(),'safe-test',confirmed=True)
        job=e.job(p,dict(authorization_id=auth['authorization_id'],action=action),ident(),'safe-test')
        e.tick()
        with self.store.read() as r:return r.get('jobs',job['job_id'])
