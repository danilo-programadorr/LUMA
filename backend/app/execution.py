import json
"""Durable authority and queue. No model decision is executable authority."""
import re
from datetime import timedelta
from .models import now,ident
from .control import digest,date
from .errors import Fault
from .trust_data import append
from .execution_contracts import CanonicalActionEnvelope,AuthorizationRequest,JobRequest

POLICY_VERSION='execution-1'
LEASE_SECONDS=30
TERMINAL={'SUCCEEDED','FAILED','BLOCKED','CANCELLED','EXPIRED'}

class ExecutionService:
    def __init__(self,control,*,sandbox=False,clock=now):
        self.control=control;self.store=control.store;self.sandbox=sandbox;self.clock=clock
        from .devices import DeviceRegistry
        self.devices=DeviceRegistry(self)
    def event(self,repo,kind,row,code='OK'):
        append(repo,dict(event_id=ident(),timestamp=self.clock().isoformat(),event_type=kind,result=code,
            principal_id=row.get('principal_id'),project_id=row.get('project_id'),correlation_id=row.get('correlation_id'),
            job_id=row.get('job_id'),authorization_id=row.get('authorization_id'),action_id=row.get('action_id')))
    def owner(self,repo,p,project=None):
        return self.control._admin(repo,p,'admin.actions.manage',project)
    def owned(self,repo,table,key,p):
        row=repo.get(table,key)
        if not row:raise Fault('NOT_FOUND',404)
        self.owner(repo,p,row['project_id'])
        if row['principal_id']!=p.principal_id:raise Fault('OBJECT_SCOPE',403)
        return row
    def idempotent(self,repo,p,key,operation,payload,fn):
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key or ''):raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        rid=digest({'execution':p.principal_id,'key':key});fp=digest({'operation':operation,'payload':payload})
        old=repo.get('idempotency',rid)
        if old:
            if old['fingerprint']!=fp:raise Fault('IDEMPOTENCY_CONFLICT',409)
            return old['response']
        result=fn();repo.add('idempotency',rid,dict(principal_id=p.principal_id,fingerprint=fp,response=result));return result
    def definition(self,repo,action):
        tool=repo.get('tools',action['tool_id'])
        if not tool:raise Fault('UNKNOWN_TOOL',404)
        if action['tool_id']=='sandbox-test':
            if not self.sandbox:raise Fault('TEST_TOOL_DISABLED',403)
            risks={'record':'LOW','review':'MEDIUM','sensitive':'HIGH','critical':'CRITICAL'}
            if action['operation'] not in risks:raise Fault('UNKNOWN_OPERATION',400)
            risk=risks[action['operation']]
        else:
            if action['operation'] not in tool['capabilities']:raise Fault('UNKNOWN_OPERATION',400)
            risk=tool.get('risk_level','HIGH')
        return tool,risk
    def candidate(self,p,body,key,correlation,*,agent_id=None):
        action=CanonicalActionEnvelope.model_validate_json(json.dumps(body)).model_dump(mode="json")
        self.control.safe(action)
        def inspect(value):
            if isinstance(value,dict):
                if set(value)&{'approved','authorized','owner','execute_now','grant','capabilities','risk_level','project_id'}:raise Fault('PRIVILEGE_ESCALATION',403)
                for child in value.values():inspect(child)
            elif isinstance(value,list):
                for child in value:inspect(child)
        inspect(action['parameters'])
        with self.store.transaction() as repo:
            if agent_id:
                actual=self.control._principal(repo,p.principal_id)
                if actual.principal_type!='SERVICE_RUNTIME' or not self.control.granted(repo,actual,'runtime.actions.propose',action['project_id']):raise Fault('CAPABILITY_DENIED',403)
                owner=self.control._principal(repo,'local-owner')
                self.control._project(repo,action['project_id'],actual)
            else:owner=self.owner(repo,p,action['project_id'])
            self.control._project(repo,action['project_id'],owner)
            _,risk=self.definition(repo,action)
            def create():
                aid=ident();row=dict(action_id=aid,principal_id=owner.principal_id,project_id=action['project_id'],envelope=action,risk_level=risk,
                    origin_type='AGENT_PROPOSED' if agent_id else 'HUMAN_DIRECT',origin_id=agent_id or p.principal_id,
                    status='WAITING_AUTHORIZATION',created_at=self.clock().isoformat(),correlation_id=correlation)
                repo.add('actions',aid,row);self.event(repo,'ACTION_PROPOSED',row);return row
            return self.idempotent(repo,p,key,'candidate',action,create)
    def authorize(self,p,aid,request,key,correlation,confirmed=False):
        spec=AuthorizationRequest.model_validate_json(json.dumps(request)).model_dump(mode="json")
        with self.store.transaction() as repo:
            action=self.owned(repo,'actions',aid,p)
            self.control._admin(repo,p,'admin.approvals.manage',action['project_id'])
            def create():
                if action['status']!='WAITING_AUTHORIZATION' or 'envelope' not in action:raise Fault('ACTION_NOT_AUTHORIZABLE',409)
                start,end=date(spec['valid_from']),date(spec['expires_at']);time=self.clock()
                if end<=time or start>=end or end-start>timedelta(days=30):raise Fault('INVALID_EXPIRATION')
                tool,risk=self.definition(repo,action['envelope'])
                if not tool['enabled']:raise Fault('TOOL_DISABLED',403)
                self.control._project(repo,action['project_id'],p)
                if risk=='CRITICAL':raise Fault('CRITICAL_UNATTENDED_DENIED',403)
                if risk=='HIGH' and (spec['mode']!='ONE_SHOT' or spec['max_executions']!=1 or not confirmed or end-time>timedelta(minutes=10)):
                    raise Fault('HIGH_AUTHORIZATION_DENIED',403)
                if spec['mode']=='ONE_SHOT' and spec['max_executions']!=1:raise Fault('INVALID_QUOTA')
                if risk=='MEDIUM' and spec['mode']=='BOUNDED_WINDOW':raise Fault('MEDIUM_WINDOW_DENIED',403)
                if (spec['mode']=='RECURRING_POLICY') != (spec['interval_seconds'] is not None):raise Fault('INVALID_SCHEDULE')
                if spec['late_execution_policy']!='RUN_LATE_WITHIN_GRACE' and spec['grace_seconds']:raise Fault('INVALID_SCHEDULE')
                authid,approval=ident(),ident()
                envelope={**action['envelope'],'risk_level':risk,'policy_version':POLICY_VERSION,'schedule_constraint':spec}
                row=dict(authorization_id=authid,principal_id=p.principal_id,owner_principal_id=p.principal_id,project_id=action['project_id'],
                    tool_id=action['envelope']['tool_id'],operation=action['envelope']['operation'],action_template=action['envelope'],
                    normalized_parameter_constraints={'exact':action['envelope']['parameters']},resource_constraint=action['envelope']['resource'],
                    destination_constraint=action['envelope']['destination'],risk_level=risk,policy_version=POLICY_VERSION,
                    exact_action_hash=digest(envelope) if spec['mode']=='ONE_SHOT' else None,template_hash=digest(envelope),
                    executions_used=0,executions_reserved=0,status='ACTIVE',revoked_at=None,created_at=time.isoformat(),
                    created_from_approval_id=approval,created_from_action_request_id=aid,human_confirmation_strength='STEP_UP' if confirmed else 'LOCAL_OWNER_BEARER',
                    origin_type='HUMAN_DIRECT',correlation_id=correlation,**spec)
                repo.add('approvals',approval,dict(approval_id=approval,action_id=aid,principal_id=p.principal_id,project_id=action['project_id'],decision='APPROVE',scope=row['template_hash'],created_at=time.isoformat()))
                repo.add('execution_authorizations',authid,row)
                action['status']='AUTHORIZED';repo.put('actions',aid,action);self.event(repo,'AUTHORIZATION_CREATED',row)
                return row
            return self.idempotent(repo,p,key,'authorize:'+aid,spec,create)
    def validate(self,repo,auth,action,*,reserved=False,at=None):
        time=at or self.clock();state=repo.get('system_state','global')['state']
        if state!='RUNNING':raise Fault('LUMA_'+state,403)
        if auth['status']!='ACTIVE' or auth['revoked_at']:raise Fault('AUTHORIZATION_REVOKED',403)
        if action!=auth['action_template']:raise Fault('AUTHORIZATION_SCOPE_MISMATCH',403)
        owner=self.control._principal(repo,auth['owner_principal_id'])
        executor=self.control._principal(repo,'luma-executor')
        if self.control._revoked(repo,owner,'admin.actions.manage',auth['project_id'],auth['tool_id']) or self.control._revoked(repo,executor,'executor.jobs.execute',auth['project_id'],auth['tool_id']):raise Fault('CAPABILITY_DENIED',403)
        tool,risk=self.definition(repo,action)
        if not tool['enabled']:raise Fault('TOOL_DISABLED',403)
        self.control._project(repo,auth['project_id'],owner);self.control._project(repo,auth['project_id'],executor)
        if time<date(auth['valid_from']) or time>=date(auth['expires_at']):raise Fault('AUTHORIZATION_EXPIRED',403)
        if auth['policy_version']!=POLICY_VERSION:raise Fault('POLICY_VERSION_MISMATCH',403)
        spec={k:auth[k] for k in AuthorizationRequest.model_fields}
        if action!=auth['action_template'] or risk!=auth['risk_level'] or digest({**action,'risk_level':risk,'policy_version':POLICY_VERSION,'schedule_constraint':spec})!=auth['template_hash']:
            raise Fault('AUTHORIZATION_SCOPE_MISMATCH',403)
        if risk=='CRITICAL':raise Fault('CRITICAL_UNATTENDED_DENIED',403)
        if auth['executions_used']+auth['executions_reserved']-(1 if reserved else 0)>=auth['max_executions']:raise Fault('AUTHORIZATION_EXHAUSTED',403)
        for principal,cap in ((owner,'admin.actions.manage'),(owner,'admin.approvals.manage'),(executor,'executor.jobs.execute')):
            if not self.control.granted(repo,principal,cap,auth['project_id'],auth['tool_id']):raise Fault('CAPABILITY_DENIED',403)
    def job(self,p,request,key,correlation):
        spec=JobRequest.model_validate_json(json.dumps(request)).model_dump(mode="json")
        self.control.safe(spec['action'])
        with self.store.transaction() as repo:
            auth=self.owned(repo,'execution_authorizations',spec['authorization_id'],p)
            def create():
                time=self.clock();scheduled=date(spec['scheduled_for']) if spec['scheduled_for'] else time
                if spec['trigger_type']!='IMMEDIATE' and not spec['scheduled_for']:raise Fault('INVALID_SCHEDULE')
                if spec['trigger_type']=='RECURRING' and auth['mode']!='RECURRING_POLICY':raise Fault('INVALID_SCHEDULE')
                if (spec['trigger_type']=='CONDITION') != bool(spec['condition_id']):raise Fault('INVALID_CONDITION')
                self.validate(repo,auth,spec['action'],at=scheduled)
                if scheduled<date(auth['valid_from']) or scheduled>=date(auth['expires_at']):raise Fault('AUTHORIZATION_SCOPE_MISMATCH',403)
                active=[j for j in repo.rows('jobs') if j['authorization_id']==auth['authorization_id'] and j['status'] not in TERMINAL]
                if auth['mode'] in ('ONE_SHOT','RECURRING_POLICY') and active:raise Fault('AUTHORIZATION_ALREADY_SCHEDULED',409)
                jid=ident();row=dict(job_id=jid,principal_id=p.principal_id,project_id=auth['project_id'],action_request_id=auth['created_from_action_request_id'],
                    **spec,scheduled_at=scheduled.isoformat(),next_run_at=scheduled.isoformat(),status='SCHEDULED',condition_satisfied=False,
                    attempt_count=0,max_attempts=1,lease_owner=None,lease_until=None,idempotency_key=digest({'authorization':auth['authorization_id'],'occurrence':scheduled.isoformat()}),
                    execution_deadline=auth['expires_at'],created_at=time.isoformat(),updated_at=time.isoformat(),started_at=None,finished_at=None,result_code=None,external_operation_id=None,correlation_id=correlation)
                repo.add('jobs',jid,row);self.event(repo,'JOB_CREATED',row);return row
            return self.idempotent(repo,p,key,'job',spec,create)
    def revoke(self,p,authid,key,correlation):
        with self.store.transaction() as repo:
            auth=self.owned(repo,'execution_authorizations',authid,p)
            def apply():
                auth.update(status='REVOKED',revoked_at=self.clock().isoformat());repo.put('execution_authorizations',authid,auth);self.event(repo,'AUTHORIZATION_REVOKED',auth)
                return auth
            return self.idempotent(repo,p,key,'revoke:'+authid,{},apply)
    def cancel(self,p,jid,key,correlation):
        with self.store.transaction() as repo:
            job=self.owned(repo,'jobs',jid,p)
            def apply():
                if job['status']=='RUNNING' or job['status'] in TERMINAL:raise Fault('JOB_TRANSITION_DENIED',409)
                self.finish(repo,job,'CANCELLED','HUMAN_CANCELLED');return job
            return self.idempotent(repo,p,key,'cancel:'+jid,{},apply)
    def finish(self,repo,job,status,code):
        job.update(status=status,result_code=code,finished_at=self.clock().isoformat(),lease_owner=None,lease_until=None)
        repo.put('jobs',job['job_id'],job);self.event(repo,'JOB_'+status,job,code)
    def late(self,auth,job):
        seconds=(self.clock()-date(job['scheduled_at'])).total_seconds()
        # One-second scheduler resolution; explicit grace for later execution.
        if seconds<=1:return
        if auth['late_execution_policy']=='RUN_LATE_WITHIN_GRACE' and seconds<=auth['grace_seconds']:return
        raise Fault('LATE_REAUTHORIZATION_REQUIRED' if auth['late_execution_policy']=='REQUIRE_REAUTHORIZATION' else 'JOB_EXPIRED',403)
    def tick(self):
        changed=[]
        with self.store.transaction() as repo:
            for job in repo.rows('jobs'):
                if job['status'] not in ('SCHEDULED','WAITING_FOR_DEVICE') or date(job['scheduled_at'])>self.clock():continue
                if job['trigger_type']=='CONDITION' and not job['condition_satisfied']:continue
                auth=repo.get('execution_authorizations',job['authorization_id'])
                try:
                    self.validate(repo,auth,job['action'])
                    if not self.devices.eligibility(repo,auth,job['action']):
                        job['status']='WAITING_FOR_DEVICE';repo.put('jobs',job['job_id'],job);continue
                    self.late(auth,job)
                except Fault as exc:self.finish(repo,job,'EXPIRED' if 'EXPIRED' in exc.code else 'BLOCKED',exc.code)
                else:job['status']='READY';repo.put('jobs',job['job_id'],job);self.event(repo,'JOB_READY',job)
                changed.append(job['job_id'])
        return changed
    def condition(self,jid,condition_id):
        # Internal adapter interface, no public arbitrary trigger endpoint.
        with self.store.transaction() as repo:
            job=repo.get('jobs',jid)
            if not job or job['status']!='SCHEDULED' or job['trigger_type']!='CONDITION' or job['condition_id']!=condition_id:raise Fault('INVALID_CONDITION')
            job['condition_satisfied']=True;repo.put('jobs',jid,job)
    def claim(self,worker,device_id=None,credential=None):
        with self.store.transaction() as repo:
            if device_id:self.devices.authenticate(repo,device_id,credential)
            for job in repo.rows('jobs'):
                if job['action']['execution_target']=='LOCAL_DEVICE':
                    if job['action']['target_device_id']!=device_id:continue
                elif device_id:continue
                if job['status']=='LEASED' and date(job['lease_until'])<=self.clock():job.update(status='READY',lease_owner=None,lease_until=None)
                if job['status']!='READY':continue
                auth=repo.get('execution_authorizations',job['authorization_id'])
                try:
                    self.validate(repo,auth,job['action']);self.late(auth,job)
                    if not self.devices.eligibility(repo,auth,job['action']):
                        job['status']='WAITING_FOR_DEVICE';repo.put('jobs',job['job_id'],job);continue
                except Fault as exc:self.finish(repo,job,'EXPIRED' if 'EXPIRED' in exc.code else 'BLOCKED',exc.code);continue
                job.update(status='LEASED',lease_owner=worker,lease_device_id=device_id,lease_until=(self.clock()+timedelta(seconds=LEASE_SECONDS)).isoformat())
                repo.put('jobs',job['job_id'],job);self.event(repo,'JOB_LEASED',job);return job
        return None
    def execute(self,jid,worker,*,after_effect=None):
        # Sandbox effect ledger is transactional with the final authorization check.
        # External adapters remain absent; future providers need native idempotency/reconciliation.
        with self.store.transaction() as repo:
            job=repo.get('jobs',jid)
            if not job or job['status']!='LEASED' or job['lease_owner']!=worker or date(job['lease_until'])<=self.clock():raise Fault('LEASE_INVALID',409)
            auth=repo.get('execution_authorizations',job['authorization_id'])
            try:
                self.validate(repo,auth,job['action']);self.late(auth,job)
                if not self.devices.eligibility(repo,auth,job['action']):raise Fault('DEVICE_OFFLINE',403)
                if job['action']['execution_target']=='LOCAL_DEVICE' and job.get('lease_device_id')!=job['action']['target_device_id']:raise Fault('DEVICE_SCOPE_MISMATCH',403)
                if not self.sandbox or job['action']['tool_id']!='sandbox-test':raise Fault('EXTERNAL_EXECUTION_DISABLED',403)
            except Fault as exc:self.finish(repo,job,'BLOCKED',exc.code);return job
            auth['executions_reserved']+=1;repo.put('execution_authorizations',auth['authorization_id'],auth)
            job.update(status='RUNNING',started_at=self.clock().isoformat(),attempt_count=job['attempt_count']+1)
            repo.put('jobs',jid,job);self.event(repo,'JOB_STARTED',job)
            if not repo.get('sandbox_effects',job['idempotency_key']):
                repo.add('sandbox_effects',job['idempotency_key'],dict(operation_id=ident(),project_id=job['project_id'],job_id=jid,action_hash=digest(job['action'])))
        if after_effect:after_effect()
        return self.reconcile(jid,worker)
    def reconcile(self,jid,worker=None):
        with self.store.transaction() as repo:
            job=repo.get('jobs',jid)
            if not job or job['status']!='RUNNING':raise Fault('RECONCILIATION_NOT_REQUIRED',409)
            if worker is None and date(job['lease_until'])>self.clock():raise Fault('LEASE_ACTIVE',409)
            if worker is not None and worker!=job['lease_owner']:raise Fault('LEASE_INVALID',409)
            effect=repo.get('sandbox_effects',job['idempotency_key']) if self.sandbox else None
            auth=repo.get('execution_authorizations',job['authorization_id'])
            outcome='CONFIRMED' if effect else 'UNKNOWN'
            repo.add('execution_reconciliations',ident(),dict(job_id=jid,project_id=job['project_id'],outcome=outcome,idempotency_key=job['idempotency_key']))
            if not effect:
                self.finish(repo,job,'BLOCKED','RECONCILIATION_REQUIRED');return job
            auth['executions_reserved']-=1;auth['executions_used']+=1;repo.put('execution_authorizations',auth['authorization_id'],auth)
            job['external_operation_id']=effect['operation_id']
            record=dict(execution_id=ident(),job_id=jid,authorization_id=auth['authorization_id'],principal_id=auth['owner_principal_id'],executor_principal_id='luma-executor',project_id=job['project_id'],status='SUCCEEDED',external_operation_id=effect['operation_id'],idempotency_key=job['idempotency_key'],finished_at=self.clock().isoformat())
            repo.add('execution_records',record['execution_id'],record);self.finish(repo,job,'SUCCEEDED','SANDBOX_RECORDED')
            if job['trigger_type']=='RECURRING' and auth['status']=='ACTIVE' and auth['executions_used']<auth['max_executions']:
                scheduled=date(job['scheduled_at'])+timedelta(seconds=auth['interval_seconds'])
                if scheduled<date(auth['expires_at']):
                    new={**job,'job_id':ident(),'status':'SCHEDULED','scheduled_at':scheduled.isoformat(),'next_run_at':scheduled.isoformat(),
                         'idempotency_key':digest({'authorization':auth['authorization_id'],'occurrence':scheduled.isoformat()}),'attempt_count':0,'started_at':None,'finished_at':None,'result_code':None,'external_operation_id':None}
                    repo.add('jobs',new['job_id'],new);self.event(repo,'JOB_CREATED',new)
            return job
