import json
"""Device identity is independent of owner/runtime; only credential digests persist."""
import secrets,hashlib
from .models import ident
from .control import date
from .errors import Fault
from .execution_contracts import DeviceHeartbeat

class DeviceRegistry:
    def __init__(self,execution):self.execution=execution;self.store=execution.store
    def public(self,row):return {k:v for k,v in row.items() if k!='credential_digest'}
    def register(self,p,data,key,correlation):
        self.execution.control.safe(data)
        with self.store.transaction() as repo:
            self.execution.owner(repo,p)
            if repo.get('execution_devices',data['device_id']):raise Fault('DEVICE_ALREADY_REGISTERED',409)
            if not key or len(key)<8:raise Fault('IDEMPOTENCY_KEY_REQUIRED')
            secret=secrets.token_urlsafe(48)
            row=dict(**data,owner_principal_id=p.principal_id,principal_id=p.principal_id,project_id='meu-gestor',status='OFFLINE',registered_at=self.execution.clock().isoformat(),
                     last_seen_at=None,capabilities=['sandbox-test'] if self.execution.sandbox else [],planned_capabilities=['codex','filesystem','git','browser','desktop'],
                     executor_version=None,enabled=True,revoked_at=None,current_job_count=0,credential_id=ident(),credential_digest=hashlib.sha256(secret.encode()).hexdigest(),correlation_id=correlation)
            repo.add('execution_devices',row['device_id'],row);self.execution.event(repo,'DEVICE_REGISTERED',row)
            return {**self.public(row),'device_credential':secret}
    def authenticate(self,repo,device_id,credential):
        row=repo.get('execution_devices',device_id)
        if not row or not isinstance(credential,str) or not 32<=len(credential)<=256 or not secrets.compare_digest(row['credential_digest'],hashlib.sha256(credential.encode()).hexdigest()):raise Fault('DEVICE_UNAUTHORIZED',401)
        if row['revoked_at'] or row['status']=='REVOKED':raise Fault('BLOCKED_DEVICE_REVOKED',403)
        if not row['enabled']:raise Fault('DEVICE_DISABLED',403)
        return row
    def heartbeat(self,body,credential):
        body=DeviceHeartbeat.model_validate_json(json.dumps(body)).model_dump(mode='json')
        with self.store.transaction() as repo:
            row=self.authenticate(repo,body['device_id'],credential)
            if not set(body['capabilities'])<=set(row['capabilities']):raise Fault('DEVICE_CAPABILITY_DENIED',403)
            row.update(executor_version=body['executor_version'],status=body['status'],current_job_count=body['current_job_count'],reported_capabilities=body['capabilities'],last_seen_at=self.execution.clock().isoformat())
            repo.put('execution_devices',row['device_id'],row);return self.public(row)
    def revoke(self,p,device_id):
        with self.store.transaction() as repo:
            row=repo.get('execution_devices',device_id)
            if not row:raise Fault('NOT_FOUND',404)
            self.execution.owner(repo,p,row['project_id'])
            if row['owner_principal_id']!=p.principal_id:raise Fault('OBJECT_SCOPE',403)
            row.update(status='REVOKED',enabled=False,revoked_at=self.execution.clock().isoformat());repo.put('execution_devices',device_id,row)
            self.execution.event(repo,'DEVICE_REVOKED',row);return self.public(row)
    def eligibility(self,repo,auth,action):
        if action['execution_target']!='LOCAL_DEVICE':return True
        row=repo.get('execution_devices',action['target_device_id'])
        if not row or row['owner_principal_id']!=auth['owner_principal_id']:raise Fault('DEVICE_SCOPE_MISMATCH',403)
        if row['revoked_at']:raise Fault('BLOCKED_DEVICE_REVOKED',403)
        if not row['enabled']:raise Fault('DEVICE_DISABLED',403)
        if action['tool_id'] not in row['capabilities']:raise Fault('DEVICE_CAPABILITY_DENIED',403)
        return action['tool_id'] in row.get('reported_capabilities',[]) and row['status']=='ONLINE' and row['current_job_count']==0 and row['last_seen_at'] is not None and (self.execution.clock()-date(row['last_seen_at'])).total_seconds()<=60
