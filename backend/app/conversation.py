"""Human conversation coordinator. Model output is data, never authority."""
import json,re,time
from datetime import timedelta
from fastapi import APIRouter,Request,Security
from fastapi.security import HTTPBearer
from pydantic import Field,ValidationError
from .models import Contract,KnowledgeRequest,Limits,now,ident
from .model_contracts import ModelInputContext,ModelDecision,decision_contract
from .generation import ModelResult,ModelUsage,usage_alerts
from .control import digest,stamp,date,action_scope
from .trust_data import append
from .errors import Fault
from .grounding import grounding_requirement,clarification_only
from .input_context import bounded_summary,input_counts,validation_errors

class ConversationTurn(Contract):
    session_id:str=Field(min_length=1,max_length=64)
    user_message:str=Field(min_length=1,max_length=2000)
    locale:str=Field(default='pt-BR',pattern=r'^[a-z]{2}-[A-Z]{2}$')

class ConversationAnswer(Contract):
    session_id:str
    project_id:str
    correlation_id:str
    assistant_message:str
    citations:list[dict]
    warnings:list[str]
    confidence:str
    model_confidence:float
    freshness:list[str]
    production_verified:bool=False
    proposed_actions:list[dict]
    learning_candidates:list[dict]
    needs_clarification:bool
    model_status:str
    model_name:str
    system_instruction_version:str
    usage:dict

class ConversationService:
    def __init__(self,control,knowledge,provider,config,*,defer_proposals=False,observer=None):
        self.control,self.knowledge,self.provider,self.config=control,knowledge,provider,config
        self.defer_proposals=defer_proposals;self.observer=observer
    def authorize(self,repo,p,sid):
        human=self.control._principal(repo,p.principal_id)
        if human.principal_type!='HUMAN_OWNER': raise Fault('HUMAN_IDENTITY_REQUIRED',403)
        session=repo.get('sessions',sid)
        if not session or session.get('human_principal_id')!=human.principal_id: raise Fault('SESSION_SCOPE',403)
        runtime=self.control._principal(repo,session.get('runtime_principal_id'))
        runtime,owner,session=self.control.runtime_session(repo,runtime,sid,'runtime.model.generate')
        if owner.principal_id!=human.principal_id or not self.control.granted(repo,human,'conversation.turn',session['project_id']): raise Fault('CAPABILITY_DENIED',403)
        self.control._check(repo,human,session['project_id'],'knowledge','knowledge.read')
        self.control._check(repo,runtime,session['project_id'],'knowledge','knowledge.read')
        return runtime,session
    def event(self,repo,p,sid,project,correlation,result,latency,usage=None):
        append(repo,dict(event_id=ident(),timestamp=stamp(),principal_id=p.principal_id,session_id=sid,project_id=project,
            runtime_principal='luma-runtime',event_type='MODEL_GENERATION',result=result,correlation_id=correlation,
            model_provider=self.config.provider,model_name=self.config.model,system_instruction_version='luma-system-2',
            latency_ms=max(0,int(latency*1000)),usage=usage or {},usage_alerts=usage_alerts(ModelUsage.model_validate(usage or {}))))
    def turn(self,p,body,key,correlation,*,proposal_agent_id=None,action_intent='INFORMATIONAL',decision_mode='GENERAL',proposal_candidates=(),requested_action=None):
        start=time.monotonic();rid=None;project=None;verified_sid=None;input_diagnostic=None
        try:
            self.control.safe(body.model_dump())
            if not body.user_message.strip() or len(body.user_message)>self.config.max_input_chars: raise Fault('MODEL_INPUT_TOO_LARGE',413)
            if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key or ''): raise Fault('IDEMPOTENCY_KEY_REQUIRED')
            rid=digest(dict(principal=p.principal_id,key=key));fingerprint=digest(body.model_dump())
            with self.control.store.transaction() as repo:
                runtime,session=self.authorize(repo,p,body.session_id);project=session['project_id'];verified_sid=session['session_id']
                previous=repo.get('conversation_requests',rid)
                if previous: raise Fault('TURN_ALREADY_RECORDED' if previous['fingerprint']==fingerprint else 'IDEMPOTENCY_CONFLICT',409)
                window=repo.get('conversation_windows',body.session_id)
                if window and window.get('active_request') and date(window['lease_expires_at'])>now(): raise Fault('SESSION_BUSY',409)
                history=window.get('turns',[]) if window and date(window['expires_at'])>now() else []
                conversation_chars=len(json.dumps(history,ensure_ascii=False))
                summary,truncated=bounded_summary(history,self.config.max_conversation_chars)
                data=dict(session_id=body.session_id,principal_id=p.principal_id,project_id=project,turns=history,
                    expires_at=(now()+timedelta(hours=24)).isoformat(),active_request=rid,lease_expires_at=(now()+timedelta(seconds=self.config.timeout+20)).isoformat())
                (repo.put if window else repo.add)('conversation_windows',body.session_id,data)
                repo.add('conversation_requests',rid,dict(principal_id=p.principal_id,project_id=project,session_id=body.session_id,
                    fingerprint=fingerprint,status='RUNNING',correlation_id=correlation,created_at=stamp()))
            requirement=grounding_requirement(body.user_message)
            knowledge=None
            if requirement=='REQUIRED':
                knowledge=self.control.runtime_knowledge(runtime,body.session_id,KnowledgeRequest(project_id=project,query=body.user_message,
                    limits=Limits(max_chars=min(16000,max(256,self.config.max_knowledge_chars//2)))),correlation,self.knowledge)
            else:
                # Do not supply factual history as a substitute for fresh authorized Knowledge.
                summary='[]';truncated=bool(history)
            catalog=()
            if self.defer_proposals and proposal_agent_id:
                from .proposal_flow import proposal_catalog
                with self.control.store.read() as repo:
                    runtime,_=self.authorize(repo,p,body.session_id)
                    catalog=proposal_catalog(self.control,repo,runtime,project,proposal_agent_id)
            fields=dict(requested_action=requested_action,action_intent=action_intent,decision_mode=decision_mode,proposal_candidates=proposal_candidates,proposal_catalog=catalog,user_message=body.user_message,session_summary=summary,project_id=project,session_id=body.session_id,
                locale=body.locale,grounding_requirement=requirement,knowledge=knowledge,available_tools=(),pending_action_ids=(),context_truncated=truncated)
            input_diagnostic=dict(**input_counts(fields,conversation_chars),context_truncated=truncated,validation_errors=[])
            if input_diagnostic['knowledge_context_chars']>self.config.max_knowledge_chars:raise Fault('MODEL_INPUT_TOO_LARGE',413)
            try:
                context=ModelInputContext(**fields)
            except ValidationError as exc:
                input_diagnostic['validation_errors']=validation_errors(exc,fields)
                raise Fault('MODEL_INPUT_SCHEMA_INVALID',503) from None
            self.control.safe(context.model_dump(mode='json'),max_chars=65536)
            result=self.provider.generate(context,correlation)
            if not isinstance(result,ModelResult): raise Fault('MODEL_INVALID_RESPONSE',503)
            try:result=ModelResult.model_validate_json(result.model_dump_json())
            except ValidationError as exc:
                if self.defer_proposals and any('proposed_actions' in e['loc'] for e in exc.errors(include_input=False,include_context=False,include_url=False)):raise Fault('PROPOSAL_SCHEMA_INVALID',503) from None
                raise
            decision=result.decision
            if decision_mode!='GENERAL':
                if decision_mode in ('PROPOSAL','PROPOSAL_REQUIRED') and not decision.proposed_actions and (decision_mode=='PROPOSAL_REQUIRED' or not decision.needs_clarification):raise Fault('ACTION_INTENT_UNFULFILLED',503)
                try:decision_contract(decision_mode).validate_json(decision.model_dump_json())
                except ValidationError:raise Fault('PROPOSAL_DECISION_INVALID',503) from None
            if self.observer:self.observer(decision)
            self.control.safe(result.model_dump(mode='json',exclude={'usage'}),max_chars=131072)
            sources={(s['document_id'],s['chunk_id']):s for s in knowledge.sources} if knowledge else {}
            citations=[]
            for c in decision.citations:
                source=sources.get((c.document_id,c.chunk_id))
                if not source: raise Fault('MODEL_INVALID_CITATION',503)
                citations.append(source)
            if requirement=='REQUIRED' and not citations and not (decision.needs_clarification and clarification_only(decision.assistant_message)): raise Fault('MODEL_MISSING_CITATION',503)
            allowed={document_id for document_id,chunk_id in sources}
            if any(x not in allowed for x in re.findall(r'\bMG-[A-Z0-9_-]+',decision.assistant_message)): raise Fault('MODEL_INVALID_CITATION',503)
            if re.search(r'\b(marquei|desmarquei|concluí|executei|enviei|agendei|implantei|I scheduled|I executed|I deployed)\b',decision.assistant_message,re.I):
                raise Fault('MODEL_EXECUTION_CLAIM',503)
            with self.control.store.transaction() as repo:
                runtime,session=self.authorize(repo,p,body.session_id)
                window=repo.get('conversation_windows',body.session_id)
                if window['active_request']!=rid: raise Fault('TURN_LEASE_EXPIRED',409)
                actions=[]
                for proposal in (() if self.defer_proposals else decision.proposed_actions):
                    self.parameters(proposal.parameters)
                    tool=repo.get('tools',proposal.tool_id)
                    if not tool or proposal.capability not in tool['capabilities']: raise Fault('MODEL_INVALID_PROPOSAL',503)
                    # No external tool or model-triggered executor in 7D; backend owns every status.
                    action=dict(action_id=ident(),principal_id=runtime.principal_id,human_principal_id=p.principal_id,project_id=project,
                        tool_id=proposal.tool_id,capability=proposal.capability,intent=proposal.reason,parameters=proposal.parameters,
                        risk_level='LOW' if proposal.capability=='knowledge.read' else 'HIGH',approval_requirement='DENY',status='DENIED',
                        origin_type='MODEL_PROPOSED',origin_id=runtime.principal_id,session_id=body.session_id,correlation_id=correlation,created_at=stamp())
                    action['scope']=action_scope(action);repo.add('actions',action['action_id'],action);actions.append(action)
                candidates=[]
                for proposal in decision.learning_candidates:
                    if any(e not in allowed for e in proposal.evidence): raise Fault('MODEL_INVALID_CITATION',503)
                    candidate=dict(candidate_id=ident(),principal_id=runtime.principal_id,human_principal_id=p.principal_id,
                        project_id=project,session_id=body.session_id,origin_type='MODEL_PROPOSED',source='MODEL_OUTPUT',claim=proposal.claim,
                        evidence=list(proposal.evidence),confidence='LOW',status='PROPOSED',created_at=stamp())
                    permitted=self.control.granted(repo,runtime,'runtime.learning.propose',project)
                    if permitted: repo.add('learning',candidate['candidate_id'],candidate)
                    candidates.append({**candidate,'persisted':permitted})
                turns=window['turns']+[dict(user=body.user_message,assistant=decision.assistant_message)]
                turns=turns[-4:]
                while turns and len(json.dumps(turns,ensure_ascii=False))>self.config.max_conversation_chars: turns.pop(0)
                window.update(turns=turns,active_request=None,expires_at=(now()+timedelta(hours=24)).isoformat())
                repo.put('conversation_windows',body.session_id,window)
                record=repo.get('conversation_requests',rid);record['status']='COMPLETED';record['input_diagnostic']=input_diagnostic;repo.put('conversation_requests',rid,record)
                self.event(repo,p,body.session_id,project,correlation,'OK',time.monotonic()-start,result.usage.model_dump())
            return ConversationAnswer(session_id=body.session_id,project_id=project,correlation_id=correlation,
                assistant_message=decision.assistant_message,citations=citations,warnings=list(dict.fromkeys((knowledge.warnings if knowledge else [])+(['CONVERSATION_CONTEXT_TRUNCATED'] if truncated else [])+usage_alerts(result.usage)+['NO_TOOL_EXECUTION','PRODUCTION_NOT_VERIFIED'])),
                confidence=knowledge.confidence if knowledge else 'NOT_APPLICABLE',model_confidence=decision.confidence,freshness=sorted({r.get('freshness','UNKNOWN') for r in (knowledge.results if knowledge else [])}),
                proposed_actions=actions,learning_candidates=candidates,needs_clarification=decision.needs_clarification,
                model_status='READY',model_name=result.model_name,system_instruction_version=result.instruction_version,usage=result.usage.model_dump())
        except Exception as exc:
            error=exc if isinstance(exc,Fault) else Fault('MODEL_ERROR',503)
            with self.control.store.transaction() as repo:
                if rid:
                    record=repo.get('conversation_requests',rid)
                    if record and record.get('correlation_id')==correlation:
                        record.update(status='FAILED',error=error.code)
                        if input_diagnostic is not None:record['input_diagnostic']=input_diagnostic
                        repo.put('conversation_requests',rid,record)
                        window=repo.get('conversation_windows',body.session_id)
                        if window and window.get('active_request')==rid:
                            window['active_request']=None;repo.put('conversation_windows',body.session_id,window)
                self.event(repo,p,verified_sid,project,correlation,error.code,time.monotonic()-start,provider_usage if (provider_usage:=getattr(error,'usage',None)) else None)
            raise error from None
    def parameters(self,value,depth=0):
        if depth>4 or len(json.dumps(value))>4096: raise Fault('MODEL_INVALID_PROPOSAL',503)
        if isinstance(value,dict):
            if len(value)>16: raise Fault('MODEL_INVALID_PROPOSAL',503)
            for key,item in value.items():
                if len(key)>64 or key.lower() in ('approved','grant','unlock','principal_id','origin_type','permission_override'): raise Fault('MODEL_INVALID_PROPOSAL',503)
                self.parameters(item,depth+1)
        elif isinstance(value,list):
            if len(value)>16: raise Fault('MODEL_INVALID_PROPOSAL',503)
            for item in value:self.parameters(item,depth+1)
        elif isinstance(value,str) and len(value)>2000: raise Fault('MODEL_INVALID_PROPOSAL',503)

def install_conversation(app,service):
    router=APIRouter(prefix='/v1/conversation',dependencies=[Security(HTTPBearer(auto_error=False))])
    @router.post('/turn',response_model=ConversationAnswer)
    def turn(body:ConversationTurn,request:Request):
        keys=request.headers.getlist('idempotency-key')
        if len(keys)!=1: raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        return service.turn(request.state.principal,body,keys[0],request.state.correlation_id)
    app.include_router(router)
