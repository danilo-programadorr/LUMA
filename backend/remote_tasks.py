"""Owner-facing tasks. All authority remains in the 7E execution service."""
from datetime import timedelta
import math
from typing import Literal
from pydantic import Field,model_validator
from .app.models import Contract,ident
from .app.control import digest,date
from .app.errors import Fault
from .app.execution_contracts import AuthorizationRequest
from .codex.contracts import ExecutionProfile

class TaskCreate(Contract):
 project_id:str=Field(min_length=1,max_length=64)
 task_type:Literal['INFORMATIONAL','ANALYTICAL','RESEARCH','PLANNING','ACTION_ORIENTED']
 input:str=Field(min_length=1,max_length=2000)
 idempotency_key:str=Field(pattern=r'^[a-zA-Z0-9_-]{8,128}$')
 target_device_id:str|None=Field(default=None,pattern=r'^[a-zA-Z0-9_-]{1,64}$')
 operation:Literal['record','review','sensitive','critical']='record'
 executor:Literal['SYNTHETIC','CODEX']='SYNTHETIC'
 codex_profile:ExecutionProfile|None=None
 priority:Literal['LOW','NORMAL','HIGH','URGENT']='NORMAL'
 ttl_seconds:int=Field(default=300,ge=30,le=600)
 @model_validator(mode='after')
 def target(self):
  if self.task_type=='ACTION_ORIENTED' and not self.target_device_id:raise ValueError('DEVICE_REQUIRED')
  if self.executor=='CODEX' and (self.task_type!='ACTION_ORIENTED' or self.codex_profile is None):raise ValueError('CODEX_ACTION_REQUIRED')
  if self.executor!='CODEX' and self.codex_profile is not None:raise ValueError('CODEX_ACTION_REQUIRED')
  return self
class Decision(Contract):
 decision:Literal['APPROVE','REJECT']
 proposal_hash:str=Field(pattern=r'^[0-9a-f]{64}$')
 confirmation:Literal['AUTHORIZE_EXACT_ACTION']|None=None

class RemoteTasks:
 def __init__(self,execution):
  self.execution=execution;self.control=execution.control;self.store=execution.store
 def event(self,r,t,kind):self.execution.event(r,kind,t)
 def owned(self,r,p,tid):
  t=self.execution.owned(r,'agent_tasks',tid,p)
  if t.get('task_protocol')!='REMOTE_TASK_V1':raise Fault('NOT_FOUND',404)
  if hasattr(self,'device_service') and t.get('owner_binding_fingerprint'):self.device_service.binding(r,{'owner_binding_fingerprint':t['owner_binding_fingerprint']})
  return t
 def snapshot(self,action):
  return {'action_id':action['action_id'],'envelope':action['envelope'],'risk':action['risk_level'],'origin':action['origin_id']}
 def view(self,r,t,include_timeline=True):
  out={k:v for k,v in t.items() if k not in ('principal_id','authorization_id','snapshot','owner_binding_id','owner_binding_fingerprint','envelope','runtime_id','session_id','result_hash','response')}
  if t['status'] in ('WAITING_AUTHORIZATION','NEEDS_CLARIFICATION') and date(t['expires_at'])<=self.execution.clock():out['status']='EXPIRED'
  if t.get('response'):out['summary']=t['response'].get('answer','');out['safe_error']=t['response'].get('error_code')
  if t.get('action_request_id'):out['proposal']=t['snapshot']
  if t.get('job_id') and t['status'] not in ('CANCELLED','EXPIRED','REJECTED','BLOCKED'):
   j=r.get('jobs',t['job_id']);auth=r.get('execution_authorizations',t['authorization_id'])
   if j['status']=='SUCCEEDED':out['status']='COMPLETED'
   elif j['status']=='CANCELLED':out['status']='CANCELLED'
   elif j['status']=='FAILED':out['status']='FAILED'
   elif auth['status']!='ACTIVE':out['status']='BLOCKED'
   elif date(auth['expires_at'])<=self.execution.clock() and j['status']!='SUCCEEDED':out['status']='EXPIRED'
   else:
    status={'SUCCEEDED':'COMPLETED','RUNNING':'EXECUTING','SCHEDULED':'QUEUED','READY':'QUEUED'}
    out['status']=status.get(j['status'],j['status'])
    if j['status']=='SCHEDULED':
     try:
      if not self.execution.devices.eligibility(r,auth,j['action']):out['status']='WAITING_FOR_DEVICE'
     except Fault as exc:out.update(status='BLOCKED',safe_error=exc.code)
   out['result_code']=j.get('result_code')
   if j.get('codex_result'):out['codex_result']=j['codex_result']
   if j['action']['tool_id']=='codex-executor' and j['status']=='RUNNING' and auth['status']!='ACTIVE':out['status']='CANCELLING'
  out['timeline']=[{k:e.get(k) for k in ('event_type','timestamp','result')} for e in (r.rows('audit_events') if include_timeline else []) if e.get('correlation_id')==t['correlation_id']][-50:]
  return out
 def create(self,p,data,correlation):
  b=TaskCreate.model_validate(data);body=b.model_dump();self.control.safe(body)
  with self.store.transaction() as r:
   self.execution.owner(r,p,b.project_id)
   if hasattr(self,'device_service'):self.device_service.rate(r,'remote-create-'+p.principal_id,30)
   if p.principal_type!='HUMAN_OWNER':raise Fault('HUMAN_OWNER_REQUIRED',403)
   def insert():
    now=self.execution.clock();t=dict(task_id=ident(),task_protocol='REMOTE_TASK_V1',principal_id=p.principal_id,project_id=b.project_id,created_by=p.principal_id,origin='OWNER',task_type=b.task_type,input=b.input,priority=b.priority,target_type='LOCAL_DEVICE' if b.target_device_id else 'EITHER',target_device_id=b.target_device_id,created_at=now.isoformat(),updated_at=now.isoformat(),expires_at=(now+timedelta(seconds=b.ttl_seconds)).isoformat(),correlation_id=ident(),status='NEEDS_CLARIFICATION',decision=None,action_request_id=None,job_id=None,summary='O processamento por agentes requer um runtime autorizado; nenhuma chamada externa foi feita.')
    if hasattr(self,'device_service'):
     binding,fingerprint=self.device_service.binding(r);t.update(owner_binding_id=binding['id'],owner_binding_fingerprint=fingerprint)
    if b.task_type=='ACTION_ORIENTED':
     device=r.get('execution_devices',b.target_device_id)
     if not device or device['owner_principal_id']!=p.principal_id or device['project_id']!=b.project_id:raise Fault('DEVICE_SCOPE_MISMATCH',403)
     if not device['enabled'] or device['revoked_at']:raise Fault('DEVICE_REVOKED',403)
     if b.executor=='CODEX':
      if not b.codex_profile or not hasattr(self.execution,'codex'):raise Fault('CODEX_DISABLED',403)
      self._codex_proposal(r,p,b,t)
     else:
      if 'sandbox-test' not in device['capabilities']:raise Fault('DEVICE_CAPABILITY_DENIED',403)
      self._synthetic_proposal(r,p,b,t)
    from .research.policy import KnowledgeRouter,ExternalQueryPolicy
    route=KnowledgeRouter().route(b.input,allow_web=False)
    t['knowledge_route']=route.model_dump()
    if b.task_type!='ACTION_ORIENTED' and route.route=='PRIVATE_LIBRARY_FUTURE':
     t.update(status='BLOCKED',safe_error='PRIVATE_LIBRARY_USE_KNOWLEDGE',summary='Utilize o fluxo autorizado da Biblioteca privada. A tarefa não reativa a fonte nem envia o documento ao runtime.')
    elif b.task_type=='RESEARCH':
     ExternalQueryPolicy().check(b.input)
     t.update(status='NEEDS_CLARIFICATION',safe_error='RESEARCH_USE_EXISTING_FLOW',summary='Pesquisa pública exige o fluxo de Pesquisa, suas permissões e limite de chamadas. Nenhuma pesquisa ou chamada paga foi iniciada por esta tarefa.')
    if b.task_type not in ('ACTION_ORIENTED','RESEARCH') and b.target_device_id and t['status']!='BLOCKED':
     from .control_plane_tasks import RuntimeTaskService
     self.control._admin(r,p,'admin.sessions.manage',b.project_id)
     session=self.control._apply(r,p,'session',{'project_id':b.project_id},None,False,t['correlation_id'])
     gateway=RuntimeTaskService(self.control,self.execution,clock=self.execution.clock)
     envelope=gateway.create(p,project_id=b.project_id,session_id=session['session_id'],device_id=b.target_device_id,message=b.input,key=ident(),correlation=t['correlation_id'],_repo=r,ttl_seconds=min(300,b.ttl_seconds))
     original=r.get('agent_tasks',envelope.task_id)
     t.update(task_id=envelope.task_id,status='QUEUED',summary='Tarefa encaminhada ao runtime local autorizado; aguarda processamento.',expires_at=envelope.expires_at.isoformat())
     original.update(t);t=original;r.put('agent_tasks',t['task_id'],t)
    else:r.add('agent_tasks',t['task_id'],t)
    self.event(r,t,'REMOTE_TASK_CREATED');return t
   t=self.execution.idempotent(r,p,b.idempotency_key,'remote-owner-task',body,insert)
   return self.view(r,self.owned(r,p,t['task_id']))
 def _synthetic_proposal(self,r,p,b,t):
  a=self.execution.candidate(p,dict(project_id=b.project_id,tool_id='sandbox-test',operation=b.operation,parameters={},resource='synthetic-ledger',destination='',execution_target='LOCAL_DEVICE',target_device_id=b.target_device_id),digest({'task_key':b.idempotency_key}),t['correlation_id'],_repo=r)
  a['remote_task_id']=t['task_id'];r.put('actions',a['action_id'],a)
  t.update(status='WAITING_AUTHORIZATION',action_request_id=a['action_id'],effective_risk=a['risk_level'],risk_hint=None,snapshot=self.snapshot(a),proposal_hash=digest(self.snapshot(a)),summary='Proposta de efeito sintético no ledger; sem operações reais no computador.')
 def _codex_proposal(self,r,p,b,t):
  profile=b.codex_profile
  a=self.execution.candidate(p,dict(project_id=b.project_id,tool_id='codex-executor',operation=profile.execution_mode,parameters=profile.model_dump(),allowed_paths=profile.allowed_paths,resource=profile.workspace_id,execution_target='LOCAL_DEVICE',target_device_id=b.target_device_id),digest({'task_key':b.idempotency_key}),t['correlation_id'],_repo=r)
  a['remote_task_id']=t['task_id'];r.put('actions',a['action_id'],a)
  t.update(status='WAITING_AUTHORIZATION',action_request_id=a['action_id'],effective_risk=a['risk_level'],snapshot=self.snapshot(a),proposal_hash=digest(self.snapshot(a)),summary='Execução Codex real no workspace autorizado; exige aprovação separada.')
 def get(self,p,tid):
  with self.store.transaction() as r:
   t=self.owned(r,p,tid)
   if date(t['expires_at'])<=self.execution.clock() and t['status'] in ('WAITING_AUTHORIZATION','NEEDS_CLARIFICATION'):
    t['status']='EXPIRED';r.put('agent_tasks',tid,t);self.event(r,t,'REMOTE_TASK_EXPIRED')
   return self.view(r,t)
 def listing(self,p,limit=50,offset=0,approvals=False):
  with self.store.read() as r:
   self.execution.owner(r,p)
   items=[t for t in r.rows('agent_tasks',principal_id=p.principal_id) if t.get('task_protocol')=='REMOTE_TASK_V1' and t['principal_id']==p.principal_id and (not approvals or t.get('action_request_id'))]
   selected=list(reversed(items))[offset:offset+limit]
   timelines={t['correlation_id']:[] for t in selected}
   if selected:
    for event in r.rows('audit_events'):
     cid=event.get('correlation_id')
     if cid in timelines:timelines[cid].append({k:event.get(k) for k in ('event_type','timestamp','result')})
   return [{**self.view(r,t,include_timeline=False),'timeline':timelines[t['correlation_id']][-50:]} for t in selected]
 def decide(self,p,tid,data,correlation,recent):
  b=Decision.model_validate(data)
  with self.store.transaction() as r:
   t=self.owned(r,p,tid)
   self.control._admin(r,p,'admin.approvals.manage',t['project_id'])
   if hasattr(self,'device_service'):self.device_service.rate(r,'remote-decision-'+p.principal_id,60)
   if t['status'] in ('CANCELLED','EXPIRED'):raise Fault('TASK_TERMINAL',409)
   if t.get('decision'):
    if t['decision']!=b.decision or t['proposal_hash']!=b.proposal_hash:raise Fault('DECISION_FINAL',409)
    return self.view(r,t)
   if t['status']!='WAITING_AUTHORIZATION' or date(t['expires_at'])<=self.execution.clock():raise Fault('TASK_NOT_APPROVABLE',409)
   a=r.get('actions',t['action_request_id'])
   if b.proposal_hash!=t['proposal_hash'] or digest(self.snapshot(a))!=t['proposal_hash']:raise Fault('PROPOSAL_CHANGED',409)
   if p.principal_type!='HUMAN_OWNER':raise Fault('HUMAN_OWNER_REQUIRED',403)
   if b.decision=='APPROVE':
    if not recent:raise Fault('RECENT_AUTH_REQUIRED',403)
    if a['risk_level']=='HIGH' and b.confirmation!='AUTHORIZE_EXACT_ACTION':raise Fault('HIGH_CONFIRMATION_REQUIRED',403)
    now=self.execution.clock();spec=AuthorizationRequest(valid_from=now.isoformat(),expires_at=t['expires_at'],max_executions=1,confirmation='AUTHORIZE_EXACT_ACTION',late_execution_policy='RUN_LATE_WITHIN_GRACE',grace_seconds=max(0,math.ceil((date(t['expires_at'])-now).total_seconds()))).model_dump()
    auth=self.execution.authorize(p,a['action_id'],spec,tid+'-authorization',t['correlation_id'],confirmed=recent,_repo=r)
    approval=r.get('approvals',auth['created_from_approval_id']);approval.update(proposal_hash=t['proposal_hash'],snapshot=t['snapshot']);r.put('approvals',approval['approval_id'],approval)
    job=self.execution.job(p,dict(authorization_id=auth['authorization_id'],action=auth['action_template']),tid+'-job',t['correlation_id'],_repo=r)
    t.update(decision='APPROVE',authorization_id=auth['authorization_id'],job_id=job['job_id'],status='QUEUED')
   else:
    a['status']='REJECTED';r.put('actions',a['action_id'],a)
    aid=ident();r.add('approvals',aid,dict(approval_id=aid,principal_id=p.principal_id,project_id=t['project_id'],action_id=a['action_id'],decision='REJECT',scope=t['proposal_hash'],snapshot=t['snapshot'],created_at=self.execution.clock().isoformat()))
    t.update(decision='REJECT',status='REJECTED')
   r.put('agent_tasks',tid,t);self.event(r,t,'APPROVAL_GRANTED' if b.decision=='APPROVE' else 'APPROVAL_REJECTED');return self.view(r,t)
 def cancel(self,p,tid,correlation):
  with self.store.transaction() as r:
   t=self.owned(r,p,tid)
   if t['status'] in ('REJECTED','EXPIRED'):raise Fault('TASK_TERMINAL',409)
   if t.get('authorization_id'):self.execution.revoke(p,t['authorization_id'],tid+'-revoke',correlation,_repo=r)
   if t.get('job_id'):
    j=r.get('jobs',t['job_id'])
    if j['status']=='SUCCEEDED':raise Fault('TASK_TERMINAL',409)
    if j['status'] not in ('RUNNING','FAILED','CANCELLED','EXPIRED','BLOCKED'):self.execution.cancel(p,j['job_id'],tid+'-cancel',correlation,_repo=r)
   if t.get('action_request_id'):
    a=r.get('actions',t['action_request_id']);a['status']='CANCELLED';r.put('actions',a['action_id'],a)
   if t.get('job_id') and j['action']['tool_id']=='codex-executor' and j['status']=='RUNNING':
    j['cancel_requested']=True;r.put('jobs',j['job_id'],j)
   t.update(status='CANCELLING' if t.get('job_id') and j['action']['tool_id']=='codex-executor' and j['status']=='RUNNING' else 'CANCELLED',cancelled_at=self.execution.clock().isoformat());r.put('agent_tasks',tid,t);self.event(r,t,'REMOTE_TASK_CANCELLED');return self.view(r,t)

 def revoke(self,p,tid,correlation):
  with self.store.transaction() as r:
   t=self.owned(r,p,tid)
   if not t.get('authorization_id'):raise Fault('AUTHORIZATION_NOT_CREATED',409)
   self.execution.revoke(p,t['authorization_id'],tid+'-revoke',correlation,_repo=r)
   self.event(r,t,'REMOTE_TASK_AUTHORIZATION_REVOKED')
   return self.view(r,t)
