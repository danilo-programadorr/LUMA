"""Canonical task gateway. Runtime output is untrusted data, never authority."""
import json
from datetime import timedelta
from pydantic import ValidationError
from .remote_protocol import RemoteTaskEnvelope,RuntimeResultEnvelope,ContextEnvelope,Scope,decode
from .app.models import ident,now
from .app.control import digest,date
from .app.errors import Fault
from .app.trust_data import append
from .app.proposal_flow import prepare,Trace,proposal_catalog
class RuntimeTaskService:
    def __init__(self,control,execution,clock=now):
        self.control=control;self.execution=execution;self.store=control.store;self.clock=clock
    def event(self,r,task,kind,code='OK'):
        append(r,dict(event_id=ident(),timestamp=self.clock().isoformat(),event_type=kind,result=code,
            principal_id=task.get('principal_id'),project_id=task.get('project_id'),
            task_id=task.get('task_id'),correlation_id=task.get('correlation_id')))
    def registry(self,r):
        return digest({'tools':r.rows('tools'),'agents':r.rows('agents')})
    def device(self,r,device,owner,project):
        row=r.get('execution_devices',device)
        if not row or row['owner_principal_id']!=owner or row['project_id']!=project:raise Fault('DEVICE_SCOPE_MISMATCH',403)
        if row['revoked_at'] or not row['enabled']:raise Fault('DEVICE_REVOKED',403)
        return row
    def create(self,owner,*,project_id,session_id,device_id,message,key,correlation,scope=None):
        scope=scope or Scope()
        with self.store.transaction() as r:
            owner=self.execution.owner(r,owner,project_id)
            runtime=self.control._principal(r,'luma-runtime')
            runtime,human,session=self.control.runtime_session(r,runtime,session_id,'runtime.model.generate')
            if human.principal_id!=owner.principal_id or session['project_id']!=project_id:raise Fault('SESSION_SCOPE',403)
            self.control._check(r,human,project_id,'knowledge','knowledge.read')
            self.control._check(r,runtime,project_id,'knowledge','knowledge.read')
            self.device(r,device_id,owner.principal_id,project_id)
            self.control.safe({'message':message,'scope':scope.model_dump(mode='json')})
            payload=dict(project_id=project_id,session_id=session_id,device_id=device_id,message=message,scope=scope.model_dump(mode='json'))
            def insert():
                time=self.clock();tid=ident()
                envelope=RemoteTaskEnvelope(task_id=tid,project_id=project_id,session_id=session_id,target_device_id=device_id,
                    correlation_id=correlation,created_at=time,expires_at=time+timedelta(minutes=5),
                    user_message=message,idempotency_key=key,tool_registry_version=self.registry(r),scope=scope,
                    context_ref=ContextEnvelope(proposal_catalog=proposal_catalog(self.control,r,runtime,project_id,'luma')))
                row=dict(task_id=tid,principal_id=owner.principal_id,project_id=project_id,session_id=session_id,runtime_id=runtime.principal_id,
                    device_id=device_id,correlation_id=correlation,status='QUEUED',created_at=time.isoformat(),
                    envelope=envelope.model_dump(mode='json'))
                r.add('agent_tasks',tid,row);self.event(r,row,'REMOTE_TASK_CREATED');self.event(r,row,'RUNTIME_ASSIGNED')
                return row
            row=self.execution.idempotent(r,owner,key,'remote_task',payload,insert)
            current=r.get('agent_tasks',row['task_id'])
            return RemoteTaskEnvelope.model_validate_json(json.dumps(current['envelope']))
    def check(self,r,row,runtime,device):
        if runtime.principal_type!='SERVICE_RUNTIME' or runtime.principal_id!=row['runtime_id']:raise Fault('RUNTIME_IDENTITY_DENIED',403)
        actual,human,session=self.control.runtime_session(r,runtime,row['session_id'],'runtime.model.generate')
        if human.principal_id!=row['principal_id'] or session['project_id']!=row['project_id']:raise Fault('SESSION_SCOPE',403)
        if device!=row['device_id']:raise Fault('DEVICE_SCOPE_MISMATCH',403)
        self.control._check(r,human,row['project_id'],'knowledge','knowledge.read')
        self.control._check(r,actual,row['project_id'],'knowledge','knowledge.read')
        self.device(r,device,row['principal_id'],row['project_id'])
        if row['status'] in ('CANCELLED','EXPIRED','POLICY_DENIED','FAILED'):raise Fault('TASK_TERMINAL',409)
        if date(row['envelope']['expires_at'])<=self.clock():raise Fault('TASK_EXPIRED',409)
        return actual,human
    def claim(self,runtime,tid,device):
        with self.store.transaction() as r:
            row=r.get('agent_tasks',tid)
            if not row or 'envelope' not in row:raise Fault('TASK_NOT_FOUND',404)
            self.check(r,row,runtime,device)
            if row['status']!='QUEUED':raise Fault('TASK_NOT_QUEUED',409)
            row['status']='CLAIMED_BY_RUNTIME';r.put('agent_tasks',tid,row);self.event(r,row,'RUNTIME_ACCEPTED')
            return RemoteTaskEnvelope.model_validate_json(json.dumps(row['envelope']))
    def cancel(self,owner,tid):
        with self.store.transaction() as r:
            row=r.get('agent_tasks',tid)
            if not row:raise Fault('TASK_NOT_FOUND',404)
            self.execution.owner(r,owner,row['project_id'])
            if row['principal_id']!=owner.principal_id:raise Fault('OBJECT_SCOPE',403)
            if row['status'] in ('COMPLETED','WAITING_AUTHORIZATION'):raise Fault('TASK_TERMINAL',409)
            row['status']='CANCELLED';r.put('agent_tasks',tid,row);self.event(r,row,'REMOTE_TASK_CANCELLED')
    def accept(self,runtime,device,payload):
        try:result=decode(RuntimeResultEnvelope,payload)
        except (ValidationError,ValueError):
            with self.store.transaction() as r:self.event(r,{},'RUNTIME_RESULT_REJECTED','RUNTIME_PROTOCOL_ERROR')
            raise Fault('RUNTIME_PROTOCOL_ERROR',400) from None
        rejection=None;response=None
        with self.store.transaction() as r:
            row=r.get('agent_tasks',result.task_id)
            if not row or 'envelope' not in row:raise Fault('TASK_NOT_FOUND',404)
            try:
                actual,human=self.check(r,row,runtime,device)
                if (result.device_id,result.runtime_id,result.correlation_id)!=(device,actual.principal_id,row['correlation_id']):raise Fault('RESULT_SCOPE_MISMATCH',403)
                fingerprint=digest(result.model_dump(mode='json'))
                if row.get('result_hash'):
                    if row['result_hash']!=fingerprint:raise Fault('IDEMPOTENCY_CONFLICT',409)
                    return row['response']
                if row['status']!='CLAIMED_BY_RUNTIME':raise Fault('TASK_NOT_CLAIMED',409)
                self.control.safe(result.model_dump(mode='json'),max_chars=262144)
                self.event(r,row,'RUNTIME_RESULT_RECEIVED')
                task=RemoteTaskEnvelope.model_validate_json(json.dumps(row['envelope']))
                if task.tool_registry_version!=self.registry(r):raise Fault('RUNTIME_POLICY_STALE',409)
                if result.result_type=='MODEL_RESULT':raise Fault('REMOTE_MODEL_CONTEXT_DENIED',403)
                if result.security_review=='REJECT':raise Fault('POLICY_DENIED',403)
                action=None
                if result.proposal:
                    self.event(r,row,'RUNTIME_PROPOSAL_RECEIVED')
                    item=result.proposal
                    if item.project_id!=row['project_id']:raise Fault('PROPOSAL_PROJECT_SCOPE_DENIED',403)
                    if (item.workspace_id,item.resource,item.destination)!=(task.scope.workspace_id,task.scope.resource,task.scope.destination):raise Fault('PROPOSAL_REQUEST_SCOPE_MISMATCH',403)
                    trace=Trace()
                    action=prepare(self.execution,r,human,row['project_id'],'luma',
                        dict(tool_id=item.tool_id,capability=item.operation,parameters=item.parameters,reason=item.reason_summary,correlation_id=row['correlation_id']),
                        trace,dict(task_id=row['task_id'],workflow_run_id=row['task_id'],correlation_id=row['correlation_id']),0)
                    if (action['envelope']['resource'],action['envelope']['destination'])!=(task.scope.resource,task.scope.destination):raise Fault('PROPOSAL_REQUEST_SCOPE_MISMATCH',403)
                    action['envelope'].update(execution_target='LOCAL_DEVICE',target_device_id=device)
                    action['workspace_id']=item.workspace_id
                    action['proposal_hash']=digest(action['envelope'])
                    if result.security_review=='REJECT':raise Fault('POLICY_DENIED',403)
                    r.add('actions',action['action_id'],action)
                    self.event(r,row,'PROPOSAL_ACCEPTED');self.event(r,row,'ACTION_REQUEST_CREATED')
                state='WAITING_AUTHORIZATION' if action else 'NEEDS_CLARIFICATION' if result.needs_clarification else 'FAILED' if result.result_type=='ERROR' else 'COMPLETED'
                if result.error_code=='POLICY_DENIED':state='POLICY_DENIED'
                response=dict(task_id=row['task_id'],task_status=state,action_request_id=action['action_id'] if action else None,
                    effective_risk=action['risk_level'] if action else None,answer=result.answer,error_code=result.error_code,
                    correlation_id=row['correlation_id'])
                row.update(status=state,result_hash=fingerprint,response=response)
                r.put('agent_tasks',row['task_id'],row)
            except Fault as exc:
                # Domain rejection is not an infrastructure outage.
                if exc.code in ('PROPOSAL_SCHEMA_INVALID','PROPOSAL_TOOL_UNKNOWN','PROPOSAL_PARAMETER_INVALID'):
                    exc=Fault(exc.code,400)
                rejection=exc
                # Preserve existing terminal status and completed response on late/replayed attacks.
                if exc.code not in ('RUNTIME_IDENTITY_DENIED','DEVICE_SCOPE_MISMATCH','RESULT_SCOPE_MISMATCH') and row['status'] not in ('CANCELLED','EXPIRED','COMPLETED','WAITING_AUTHORIZATION','NEEDS_CLARIFICATION'):
                    row['status']='EXPIRED' if exc.code=='TASK_EXPIRED' else 'POLICY_DENIED'
                    r.put('agent_tasks',row['task_id'],row)
                self.event(r,row,'PROPOSAL_REJECTED',exc.code)
        if rejection:raise rejection
        return response
