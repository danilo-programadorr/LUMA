"""Intelligence-only processing. No Store, Control, grants, approvals or job writer."""
import hashlib,json,threading,time
from collections import OrderedDict
from datetime import datetime,timezone
from .remote_protocol import RemoteTaskEnvelope,RuntimeResultEnvelope,RuntimeProposalEnvelope,TraceSummary,decode
from .app.errors import Fault
class RuntimeTaskProcessor:
    principal_type='SERVICE_RUNTIME'
    def __init__(self,handler,*,device_id,registry_version,clock=lambda:datetime.now(timezone.utc)):
        self.handler=handler;self.device_id=device_id;self.registry_version=registry_version;self.clock=clock
        self.cache=OrderedDict();self.keys={};self.lock=threading.Lock();self.inflight={}
    def process(self,payload):
        task=decode(RemoteTaskEnvelope,payload)
        if task.target_device_id!=self.device_id:raise Fault('RUNTIME_DEVICE_SCOPE',403)
        if task.expires_at<=self.clock():raise Fault('TASK_EXPIRED',409)
        if task.tool_registry_version!=self.registry_version:raise Fault('RUNTIME_POLICY_STALE',409)
        fingerprint=hashlib.sha256(task.model_dump_json().encode()).hexdigest()
        while True:
            if task.expires_at<=self.clock():raise Fault('TASK_EXPIRED',409)
            with self.lock:
                if task.idempotency_key in self.keys and self.keys[task.idempotency_key]!=task.task_id:raise Fault('IDEMPOTENCY_CONFLICT',409)
                if task.task_id in self.cache:
                    prior,result=self.cache[task.task_id]
                    if prior!=fingerprint:raise Fault('IDEMPOTENCY_CONFLICT',409)
                    return result
                pending=self.inflight.get(task.task_id)
                if pending:
                    if pending[0]!=fingerprint:raise Fault('IDEMPOTENCY_CONFLICT',409)
                    event=pending[1]
                else:
                    if len(self.inflight)>=16:raise Fault('RUNTIME_UNAVAILABLE',503)
                    event=threading.Event()
                    self.inflight[task.task_id]=(fingerprint,event)
                    self.keys[task.idempotency_key]=task.task_id
                    break
            if not event.wait(180):raise Fault('RUNTIME_UNAVAILABLE',503)
        try:
            result=self.handler(task)
            if not isinstance(result,RuntimeResultEnvelope):raise Fault('RUNTIME_PROTOCOL_ERROR',400)
            result=decode(RuntimeResultEnvelope,result.model_dump_json().encode())
            if (result.task_id,result.device_id,result.correlation_id)!=(task.task_id,self.device_id,task.correlation_id):raise Fault('RUNTIME_RESULT_SCOPE',403)
            encoded=result.model_dump_json().encode()
            with self.lock:
                if len(self.cache)>=128:
                    expired=self.cache.popitem(last=False)[0]
                    self.keys={k:v for k,v in self.keys.items() if v!=expired}
                self.cache[task.task_id]=(fingerprint,encoded)
            return encoded
        finally:
            with self.lock:
                self.inflight.pop(task.task_id,None)
                if task.task_id not in self.cache:self.keys.pop(task.idempotency_key,None)
                event.set()

class LocalRuntimeTransport:
    def __init__(self,processor):self.processor=processor
    def exchange(self,payload):return self.processor.process(bytes(payload))
class FutureRemoteRuntimeTransport:
    def exchange(self,payload):raise Fault('RUNTIME_UNAVAILABLE',503)

class IntelligenceHandler:
    def __init__(self,provider,knowledge=None,workflow=None):
        self.provider=provider;self.knowledge=knowledge;self.workflow=workflow
    def __call__(self,task):
        try:return self._run(task)
        except Exception as exc:
            if task.task_type=='MODEL_GENERATION':raise
            code=getattr(exc,'code','')
            safe='KNOWLEDGE_UNAVAILABLE' if code.startswith('KNOWLEDGE') else 'MODEL_ERROR' if code.startswith('MODEL') else 'RUNTIME_PROTOCOL_ERROR' if code.startswith('RUNTIME_PROTOCOL') else 'TECHNICAL_FAILURE'
            return RuntimeResultEnvelope(task_id=task.task_id,device_id=task.target_device_id,correlation_id=task.correlation_id,
                result_type='ERROR',runtime_status='FAILED',error_code=safe)
    def _run(self,task):
        from .app.model_contracts import ModelInputContext
        from .app.models import KnowledgeRequest,Limits
        from .app.grounding import grounding_requirement
        start=time.monotonic()
        if task.task_type=='MODEL_GENERATION':
            if task.context_ref.model_input is None:raise Fault('RUNTIME_PROTOCOL_ERROR',400)
            model=self.provider.generate(task.context_ref.model_input,task.correlation_id)
            return RuntimeResultEnvelope(task_id=task.task_id,device_id=task.target_device_id,correlation_id=task.correlation_id,result_type='MODEL_RESULT',model_result=model)
        knowledge=None
        requirement=grounding_requirement(task.user_message)
        if requirement=='REQUIRED':
            if self.knowledge is None:raise Fault('KNOWLEDGE_UNAVAILABLE',503)
            knowledge=self.knowledge.query(KnowledgeRequest(project_id=task.project_id,query=task.user_message,limits=Limits(max_chars=8000)),task.correlation_id)
        context=ModelInputContext(user_message=task.user_message,project_id=task.project_id,session_id=task.session_id,
            session_summary=json.dumps(task.context_ref.messages),knowledge=knowledge,grounding_requirement=requirement,
            proposal_catalog=task.context_ref.proposal_catalog)
        from .app.agent_team import route,instruction
        from .app.action_intent import classify,ActionIntent
        classification=classify(task.user_message)
        requested=list(route(task.user_message,task.project_id,task.correlation_id).requested_agents)
        if classification in (ActionIntent.ACTION_REQUEST,ActionIntent.AMBIGUOUS):requested=['security']
        roles=['luma',*requested]
        if requested and classification==ActionIntent.INFORMATIONAL:roles.append('luma')
        results=[];summaries=[]
        def generate(role,index):
            mode='SECURITY_REVIEW' if role=='security' else 'PROPOSAL' if classification==ActionIntent.ACTION_REQUEST and task.context_ref.proposal_catalog else 'GENERAL'
            pending=tuple(p for previous in results for p in previous.decision.proposed_actions)[:3]
            local=context.model_copy(update={'decision_mode':mode,'action_intent':classification.value,'proposal_candidates':pending})
            result=self.provider.generate(local,task.correlation_id)
            from .app.model_contracts import decision_contract
            from .app.grounding import clarification_only
            import re
            decision_contract(mode).validate_json(result.decision.model_dump_json())
            decision=result.decision
            sources={(x['document_id'],x['chunk_id']) for x in knowledge.sources} if knowledge else set()
            if any((x.document_id,x.chunk_id) not in sources for x in decision.citations):raise Fault('MODEL_INVALID_CITATION',503)
            if requirement=='REQUIRED' and not decision.citations and not (decision.needs_clarification and clarification_only(decision.assistant_message)):raise Fault('MODEL_MISSING_CITATION',503)
            if any(x not in {d for d,c in sources} for x in re.findall(r'\bMG-[A-Z0-9_-]+',decision.assistant_message)):raise Fault('MODEL_INVALID_CITATION',503)
            if re.search(r'\b(marquei|desmarquei|concluí|executei|enviei|agendei|implantei|I scheduled|I executed|I deployed)\b',decision.assistant_message,re.I):raise Fault('MODEL_EXECUTION_CLAIM',503)
            serialized=result.model_dump_json()
            local_secrets=(getattr(getattr(self.provider,'config',None),'api_key',''),getattr(getattr(self.knowledge,'settings',None),'knowledge_token',''))
            if any(secret and secret in serialized for secret in local_secrets):raise Fault('MODEL_SENSITIVE_OUTPUT',503)
            results.append(result)
            summaries.append(TraceSummary(agent_id=role,workflow_node=role.upper(),decision_type='REVIEW' if role=='security' else 'PROPOSAL' if result.decision.proposed_actions else 'ANSWER',
                latency_ms=min(180000,int((time.monotonic()-start)*1000)),status='COMPLETED'))
            return result.decision.model_dump(mode='json')
        if self.workflow:self.workflow([{'agent_id':role,'instruction':instruction(role)} for role in roles],generate)
        else:
            for index,role in enumerate(roles):generate(role,index)
        result=next((x for x in results if x.decision.proposed_actions),results[-1]);decision=result.decision
        review='REJECT' if any(x.decision.review_recommendation=='reject_candidate' for x in results) else 'WARN' if any(x.decision.review_recommendation in ('warn','raise_risk') for x in results) else 'NONE'
        proposal=None
        if decision.proposed_actions:
            if len(decision.proposed_actions)!=1:raise Fault('RUNTIME_PROTOCOL_ERROR',400)
            item=decision.proposed_actions[0]
            proposal=RuntimeProposalEnvelope(proposal_id=task.task_id+'-p',tool_id=item.tool_id,operation=item.capability,
                project_id=task.project_id,parameters=item.parameters,reason_summary=item.reason,
                workspace_id=task.scope.workspace_id,resource=task.scope.resource,destination=task.scope.destination)
        kind='PROPOSAL' if proposal else 'NEEDS_CLARIFICATION' if decision.needs_clarification else 'ANSWER'
        return RuntimeResultEnvelope(task_id=task.task_id,device_id=task.target_device_id,correlation_id=task.correlation_id,
            result_type=kind,answer=decision.assistant_message,proposal=proposal,needs_clarification=decision.needs_clarification,
            citations=tuple(c.document_id for c in decision.citations),
            security_review=review,agent_trace_summary=tuple(summaries))
