"""Official authority service; local paths and model credentials never enter here."""
import hashlib
from datetime import timedelta
from pydantic import ValidationError
from .contracts import ExecutionProfile,WorkspaceManifest,ExecutionResult
from ..app.errors import Fault
from ..app.models import ident
from ..app.control import digest,date
from ..app.trust_data import grant
from ..device_protocol import SignedDeviceRequest

TOOL='codex-executor'
class CodexService:
 def __init__(self,devices):
  self.devices=devices;self.execution=devices.execution;self.control=devices.control;self.store=devices.store
 def workspace_key(self,did,wid):return digest({'device':did,'workspace':wid})
 def workspaces(self,p):
  with self.store.read() as r:
   self.execution.owner(r,p)
   return [x for x in r.rows('codex_workspaces',principal_id=p.principal_id) if x['principal_id']==p.principal_id]
 def register(self,p,manifest):
  b=WorkspaceManifest.model_validate(manifest);data=b.model_dump()
  with self.store.transaction() as r:
   self.execution.owner(r,p,b.project_id)
   self.devices.rate(r,'codex-register-'+p.principal_id,10)
   d=r.get('execution_devices',b.target_device_id);identity=r.get('device_identities',b.target_device_id)
   if not d or not identity or identity['status']!='ACTIVE' or d['owner_principal_id']!=p.principal_id or d['project_id']!=b.project_id:raise Fault('CODEX_DEVICE_SCOPE',403)
   self.devices.binding(r,identity)
   key=self.workspace_key(b.target_device_id,b.workspace_id);old=r.get('codex_workspaces',key)
   if old and (old['mapping_fingerprint']!=b.mapping_fingerprint or old['mapping_version']!=b.mapping_version) and b.mapping_version<=old['mapping_version']:raise Fault('CODEX_MAPPING_CHANGED',409)
   row={**data,'principal_id':p.principal_id,'status':'ACTIVE' if b.enabled else 'DISABLED','updated_at':self.devices.stamp()}
   if old:r.put('codex_workspaces',key,row)
   else:r.add('codex_workspaces',key,row)
   self.control.event(r,p.principal_id,b.project_id,'CODEX_WORKSPACE_REGISTERED','ENABLED' if b.enabled else 'DISABLED',b.workspace_id)
   return data
 def capability(self,p,did,enabled):
  with self.store.transaction() as r:
   self.execution.owner(r,p,'meu-gestor')
   self.devices.rate(r,'codex-grant-'+p.principal_id,10)
   d=r.get('execution_devices',did);identity=r.get('device_identities',did)
   if not d or not identity or identity['status']!='ACTIVE' or d['owner_principal_id']!=p.principal_id:raise Fault('CODEX_DEVICE_SCOPE',403)
   self.devices.binding(r,identity)
   caps=set(d['capabilities']);caps.discard(TOOL)
   if enabled:caps.add(TOOL)
   d.update(capabilities=sorted(caps),codex_ready=False,codex_workspaces=[])
   r.put('execution_devices',did,d)
   tool=r.get('tools',TOOL)
   if not tool:r.add('tools',TOOL,dict(tool_id=TOOL,enabled=True,capabilities=['READ_ONLY','WORKSPACE_WRITE'],risk_level='MEDIUM'))
   if enabled:grant(r,p.principal_id,'CODEX_EXECUTION',d['project_id'],TOOL)
   self.control.event(r,p.principal_id,d['project_id'],'CODEX_CAPABILITY_CHANGED','ENABLED' if enabled else 'DISABLED',did)
   return dict(device_id=did,codex_execution_enabled=enabled)
 def validate_action(self,r,action):
  if action['execution_target']!='LOCAL_DEVICE' or not action.get('target_device_id'):raise Fault('CODEX_LOCAL_DEVICE_REQUIRED',403)
  try:profile=ExecutionProfile.model_validate(action['parameters'])
  except ValidationError:raise Fault('CODEX_PROFILE_INVALID',400) from None
  if profile.execution_mode!=action['operation'] or action['resource']!=profile.workspace_id or action['allowed_paths']!=profile.allowed_paths:raise Fault('CODEX_PROFILE_MISMATCH',403)
  w=r.get('codex_workspaces',self.workspace_key(action['target_device_id'],profile.workspace_id))
  if not w or not w['enabled']:raise Fault('CODEX_WORKSPACE_UNKNOWN',403)
  d=r.get('execution_devices',action['target_device_id']);identity=r.get('device_identities',action['target_device_id'])
  if not d or not identity or identity['status']!='ACTIVE' or not d['enabled'] or d['revoked_at'] or d['owner_principal_id']!=w['principal_id']:raise Fault('CODEX_DEVICE_SCOPE',403)
  self.devices.binding(r,identity)
  if TOOL not in d['capabilities']:raise Fault('CODEX_CAPABILITY_DENIED',403)
  owner=self.control._principal(r,w['principal_id'])
  if not self.control.granted(r,owner,'CODEX_EXECUTION',action['project_id'],TOOL):raise Fault('CODEX_CAPABILITY_DENIED',403)
  if w['project_id']!=action['project_id'] or w['mapping_version']!=profile.mapping_version or w['mapping_fingerprint']!=profile.mapping_fingerprint or profile.execution_mode not in w['allowed_execution_modes']:raise Fault('CODEX_MAPPING_CHANGED',403)
  if w['binary_sha256']!=profile.binary_sha256 or w['model']!=profile.model:raise Fault('CODEX_BINARY_OR_MODEL_CHANGED',403)
  if w.get('snapshot_hash','0'*64)!=profile.snapshot_hash:raise Fault('CODEX_WORKSPACE_CHANGED',409)
  if __import__('os').environ.get('LUMA_ENV')!='test' and profile.snapshot_hash=='0'*64:raise Fault('CODEX_PREFLIGHT_REQUIRED',403)
  if profile.binary_sha256=='0'*64 or not profile.model:raise Fault('CODEX_PREFLIGHT_REQUIRED',403)
  return profile
 def handle(self,path,data):
  error=None;out=None
  with self.store.transaction() as r:
   try:
    request=SignedDeviceRequest.model_validate(data)
    principal,row=self.devices.auth.authenticate(r,path,request)
    self.devices.rate(r,'codex-'+row['device_id'],60)
    op=path.rsplit('/',1)[-1];payload=request.payload
    if op=='discovery':out=self.discovery(r,row,payload)
    elif op=='heartbeat':out=self.heartbeat(r,row,payload)
    elif op=='poll':
     if payload:raise Fault('CODEX_REQUEST_INVALID',400)
     out=self.poll(r,row)
    elif op=='progress':out=self.progress(r,row,payload)
    elif op=='check':out=self.check(r,row,payload)
    elif op=='result':out=self.result(r,row,payload)
    else:raise Fault('NOT_FOUND',404)
    out={**out,'request_nonce':request.nonce,'device_id':principal.device_id}
   except (Fault,ValidationError,ValueError) as exc:
    error=exc if isinstance(exc,Fault) else Fault('CODEX_REQUEST_INVALID',400)
    self.devices.event(r,'CODEX_REQUEST_REJECTED',error.code)
  if error:raise error
  return out
 def discovery(self,r,row,payload):
  if set(payload)!={'manifest'}:raise Fault('CODEX_REQUEST_INVALID',400)
  manifest=WorkspaceManifest.model_validate(payload['manifest'])
  if manifest.enabled:raise Fault('CODEX_OWNER_GRANT_REQUIRED',403)
  if manifest.target_device_id!=row['device_id'] or manifest.project_id!=row['project_id']:raise Fault('CODEX_DEVICE_SCOPE',403)
  key=self.workspace_key(row['device_id'],manifest.workspace_id);old=r.get('codex_workspaces',key)
  if old and old['enabled']:
   if any(old.get(k)!=v for k,v in manifest.model_dump().items() if k not in ('enabled','snapshot_hash')):raise Fault('CODEX_MAPPING_CHANGED',409)
   old['snapshot_hash']=manifest.snapshot_hash;r.put('codex_workspaces',key,old)
   return {'status':'ALREADY_OWNER_REGISTERED'}
  candidate={**manifest.model_dump(),'principal_id':row['principal_id'],'status':'PENDING_OWNER_GRANT','source':'DEVICE_DECLARED_NOT_AUTHORITY'}
  if old:r.put('codex_workspaces',key,candidate)
  else:r.add('codex_workspaces',key,candidate)
  self.control.event(r,row['principal_id'],manifest.project_id,'CODEX_WORKSPACE_DISCOVERED','PENDING_OWNER_GRANT',manifest.workspace_id)
  return {'status':'PENDING_OWNER_GRANT'}
 def heartbeat(self,r,row,payload):
  if set(payload)!={'binary_sha256','workspace_ids'} or not isinstance(payload['workspace_ids'],list) or len(payload['workspace_ids'])>20:raise Fault('CODEX_REQUEST_INVALID',400)
  binary=payload['binary_sha256']
  if not isinstance(binary,str) or len(binary)!=64 or any(x not in '0123456789abcdef' for x in binary):raise Fault('CODEX_REQUEST_INVALID',400)
  d=r.get('execution_devices',row['device_id'])
  if TOOL not in d['capabilities']:raise Fault('CODEX_CAPABILITY_DENIED',403)
  if any(not isinstance(x,str) or not r.get('codex_workspaces',self.workspace_key(row['device_id'],x)) for x in payload['workspace_ids']):raise Fault('CODEX_WORKSPACE_UNKNOWN',403)
  d.update(codex_ready=True,codex_seen_at=self.devices.stamp(),codex_binary_sha256=binary,codex_workspaces=payload['workspace_ids'])
  r.put('execution_devices',row['device_id'],d)
  return {'status':'ACCEPTED'}
 def poll(self,r,row):
  d=r.get('execution_devices',row['device_id'])
  if TOOL not in d['capabilities']:raise Fault('CODEX_CAPABILITY_DENIED',403)
  if not self.devices.public(row)['online'] or not d.get('codex_ready') or (self.execution.clock()-date(d['codex_seen_at'])).total_seconds()>45:return {'job':None,'status':'WAITING_FOR_DEVICE'}
  jobs=[j for j in r.rows('jobs') if j['action']['tool_id']==TOOL and j['action']['target_device_id']==row['device_id']]
  for j in jobs:
   if j['status']=='RUNNING':
    if date(j['lease_until'])<=self.execution.clock():self.execution.finish(r,j,'BLOCKED','CODEX_EXECUTION_AMBIGUOUS')
    return {'job':None,'status':'BUSY' if j['status']=='RUNNING' else 'RECONCILIATION_REQUIRED'}
  for job in jobs:
   if job['status'] not in ('SCHEDULED','READY','WAITING_FOR_DEVICE') or date(job['scheduled_at'])>self.execution.clock():continue
   auth=r.get('execution_authorizations',job['authorization_id'])
   try:
    self.execution.validate(r,auth,job['action']);self.execution.late(auth,job)
    profile=self.validate_action(r,job['action'])
    if profile.binary_sha256!=d['codex_binary_sha256']:raise Fault('CODEX_BINARY_CHANGED',403)
    if profile.workspace_id not in d['codex_workspaces']:raise Fault('CODEX_WORKSPACE_UNKNOWN',403)
   except Fault as exc:self.execution.finish(r,job,'BLOCKED',exc.code);continue
   lease=ident();auth['executions_reserved']+=1;r.put('execution_authorizations',auth['authorization_id'],auth)
   job.update(status='RUNNING',device_lease_id=lease,lease_device_id=row['device_id'],lease_owner='device-'+row['device_id'],lease_until=(self.execution.clock()+timedelta(seconds=30)).isoformat(),started_at=self.devices.stamp(),attempt_count=job['attempt_count']+1,codex_profile_hash=digest(profile.model_dump()))
   r.put('jobs',job['job_id'],job);self.execution.event(r,'CODEX_JOB_PREPARED',job)
   return {'job':dict(job_id=job['job_id'],lease_id=lease,lease_until=job['lease_until'],expires_at=auth['expires_at'],device_id=row['device_id'],project_id=job['project_id'],profile=profile.model_dump(),profile_hash=job['codex_profile_hash'],extension_version='CODEX_DEVICE_EXTENSION_V1')}
  return {'job':None}
 def leased(self,r,row,payload):
  if set(payload)-{'job_id','lease_id','result','phase','execution_kind'}:raise Fault('CODEX_REQUEST_INVALID',400)
  job=r.get('jobs',payload.get('job_id'))
  if not job or job['action']['tool_id']!=TOOL or job['action']['target_device_id']!=row['device_id'] or job.get('device_lease_id')!=payload.get('lease_id'):raise Fault('CODEX_DEVICE_SCOPE',403)
  return job
 def continuing(self,r,row,job):
  if job['status']!='RUNNING':return 'CODEX_JOB_NOT_RUNNING'
  if date(job['lease_until'])<=self.execution.clock():return 'CODEX_EXECUTION_AMBIGUOUS'
  if job.get('cancel_requested'):return 'CODEX_CANCELLED'
  try:
   auth=r.get('execution_authorizations',job['authorization_id']);self.execution.validate(r,auth,job['action'],reserved=True)
   profile=self.validate_action(r,job['action'])
   if digest(profile.model_dump())!=job['codex_profile_hash']:return 'CODEX_PROFILE_CHANGED'
   if job.get('cancel_requested'):return 'CODEX_CANCELLED'
   if not self.devices.public(row)['online']:return 'DEVICE_OFFLINE'
  except Fault as exc:return exc.code
  return None
 def check(self,r,row,payload):
  if set(payload)!={'job_id','lease_id'}:raise Fault('CODEX_REQUEST_INVALID',400)
  job=self.leased(r,row,payload);code=self.continuing(r,row,job)
  if not code:
   job['lease_until']=(self.execution.clock()+timedelta(seconds=30)).isoformat();r.put('jobs',job['job_id'],job)
  return {'continue':not code,'code':code,'lease_until':job['lease_until']}
 def progress(self,r,row,payload):
  if set(payload)!={'job_id','lease_id','phase','execution_kind'}:raise Fault('CODEX_REQUEST_INVALID',400)
  job=self.leased(r,row,payload)
  phases=('BINARY_VALIDATED','PROCESS_STARTED','PROCESS_EXITED','VERIFIED')
  phase=payload['phase'];kind=payload['execution_kind']
  if phase not in phases or kind not in ('CODEX_REAL','SIMULATED_TEST'):raise Fault('CODEX_REQUEST_INVALID',400)
  if kind=='SIMULATED_TEST' and __import__('os').environ.get('LUMA_ENV')!='test':raise Fault('CODEX_SIMULATED_RESULT_DENIED',403)
  previous=job.get('codex_phase')
  if previous and phases.index(phase)<phases.index(previous):raise Fault('CODEX_PHASE_REGRESSION',409)
  if previous!=phase:
   job['codex_phase']=phase
   self.execution.event(r,'CODEX_'+('SIMULATED_' if kind=='SIMULATED_TEST' else '')+phase,job)
   r.put('jobs',job['job_id'],job)
  return self.check(r,row,{'job_id':job['job_id'],'lease_id':job['device_lease_id']})
 def result(self,r,row,payload):
  if set(payload)!={'job_id','lease_id','result'}:raise Fault('CODEX_REQUEST_INVALID',400)
  job=self.leased(r,row,payload);result=ExecutionResult.model_validate(payload.get('result'))
  if result.execution_kind=='SIMULATED_TEST' and __import__('os').environ.get('LUMA_ENV')!='test':raise Fault('CODEX_SIMULATED_RESULT_DENIED',403)
  body=result.model_dump()
  # Usage is already an allowlisted dict of nonnegative ints, never credential text.
  # Keep all other fields under the existing sensitive-payload screening.
  self.control.safe({k:v for k,v in body.items() if k!='usage'})
  rh=digest(body)
  if job.get('codex_result_hash'):
   if job['codex_result_hash']!=rh:raise Fault('CODEX_RESULT_CONFLICT',409)
   return {'status':job['status'],'duplicate':True}
  profile=ExecutionProfile.model_validate(job['action']['parameters'])
  if result.job_id!=job['job_id'] or result.workspace_id!=profile.workspace_id or result.profile_hash!=job['codex_profile_hash'] or result.binary_sha256!=profile.binary_sha256:raise Fault('CODEX_RESULT_SCOPE',403)
  if not set(result.changed_files)<=set(profile.allowed_paths) or len(result.changed_files)>profile.max_changed_files or result.changed_bytes>profile.max_changed_bytes or (profile.execution_mode=='READ_ONLY' and result.changed_files):raise Fault('CODEX_SCOPE_EXCEEDED',403)
  code=self.continuing(r,row,job)
  job.update(codex_result_hash=rh,codex_result=body)
  auth=r.get('execution_authorizations',job['authorization_id'])
  auth['executions_reserved']=max(0,auth['executions_reserved']-1);auth['executions_used']+=1;r.put('execution_authorizations',auth['authorization_id'],auth)
  success=not code and bool(result.summary.strip()) and result.status=='SUCCEEDED' and result.exit_code==0 and result.validation_pass and result.code=='CODEX_VERIFIED'
  if success:
   rid=ident();r.add('execution_records',rid,dict(execution_id=rid,job_id=job['job_id'],authorization_id=auth['authorization_id'],principal_id=auth['principal_id'],project_id=job['project_id'],status='SUCCEEDED',synthetic=result.execution_kind=='SIMULATED_TEST',result_hash=rh))
  cancelled=bool(job.get('cancel_requested')) and result.status=='CANCELLED'
  self.execution.finish(r,job,'SUCCEEDED' if success else 'CANCELLED' if cancelled else 'BLOCKED' if code or result.status=='RECONCILIATION_REQUIRED' else 'CANCELLED' if result.status=='CANCELLED' else 'FAILED',code or result.code)
  return {'status':job['status'],'duplicate':False}
