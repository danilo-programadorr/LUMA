"""Versioned data contracts. No authority, database, runtime or tool implementation."""
import json
from datetime import datetime
from typing import Literal,Protocol
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .app.model_contracts import ModelInputContext,ProposalCatalogEntry
from .app.generation import ModelResult
MAX_FRAME=262144
class Frame(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,strict=True)
    protocol_version:Literal['1']='1'
    @model_validator(mode='after')
    def bounded(self):
        if len(self.model_dump_json().encode())>MAX_FRAME:raise ValueError('FRAME_TOO_LARGE')
        return self
class ContextEnvelope(Frame):
    context_ref:str=Field(default='',max_length=128)
    messages:tuple[str,...]=Field(default=(),max_length=4)
    model_input:ModelInputContext|None=None
    proposal_catalog:tuple[ProposalCatalogEntry,...]=Field(default=(),max_length=16)
    @model_validator(mode='after')
    def limit(self):
        if any(len(x)>2000 for x in self.messages) or sum(len(x.encode()) for x in self.messages)>8000:raise ValueError('CONTEXT_TOO_LARGE')
        return self
class Scope(Frame):
    workspace_id:str=Field(default='',max_length=64)
    resource:str=Field(default='',max_length=200)
    destination:str=Field(default='',max_length=200)
class RemoteTaskEnvelope(Frame):
    task_id:str=Field(min_length=1,max_length=64)
    project_id:str=Field(min_length=1,max_length=64)
    session_id:str=Field(min_length=1,max_length=64)
    target_device_id:str=Field(min_length=1,max_length=64)
    runtime_id:Literal['luma-runtime']='luma-runtime'
    correlation_id:str=Field(min_length=1,max_length=64)
    created_at:datetime
    expires_at:datetime
    task_type:Literal['ANALYZE','MODEL_GENERATION']='ANALYZE'
    user_message:str=Field(min_length=1,max_length=2000)
    context_ref:ContextEnvelope=Field(default_factory=ContextEnvelope)
    idempotency_key:str=Field(min_length=8,max_length=128)
    tool_registry_version:str=Field(min_length=1,max_length=64)
    scope:Scope=Field(default_factory=Scope)
    @model_validator(mode='after')
    def dates(self):
        if not self.created_at.tzinfo or not self.expires_at.tzinfo or self.expires_at<=self.created_at:raise ValueError('INVALID_TASK_TIME')
        if (self.expires_at-self.created_at).total_seconds()>600:raise ValueError('TASK_TTL_TOO_LONG')
        if self.context_ref.model_input and (self.context_ref.model_input.project_id!=self.project_id or self.context_ref.model_input.session_id!=self.session_id):raise ValueError('CONTEXT_BINDING')
        return self
class RuntimeProposalEnvelope(Frame):
    proposal_id:str=Field(min_length=1,max_length=64)
    tool_id:str=Field(min_length=1,max_length=64)
    operation:str=Field(min_length=1,max_length=100)
    project_id:str=Field(min_length=1,max_length=64)
    workspace_id:str=Field(default='',max_length=64)
    resource:str=Field(default='',max_length=200)
    destination:str=Field(default='',max_length=200)
    parameters:dict[str,str]=Field(default_factory=dict,max_length=16)
    requested_target:Literal['LOCAL_DEVICE']='LOCAL_DEVICE'
    runtime_risk_hint:Literal['LOW','MEDIUM','HIGH','CRITICAL']='HIGH'
    reason_summary:str=Field(default='',max_length=1000)
    @model_validator(mode='after')
    def params(self):
        forbidden={'approved','authorization','authorization_id','owner_id','owner_override','risk','tool_enabled','kill_switch','execution_allowed','grant','unlock'}
        if forbidden&self.parameters.keys() or any(len(v)>2000 for v in self.parameters.values()) or len(json.dumps(self.parameters).encode())>8192:raise ValueError('INVALID_PROPOSAL_PARAMETERS')
        return self
class TraceSummary(Frame):
    agent_id:str=Field(max_length=64)
    workflow_node:str=Field(max_length=64)
    decision_type:Literal['ANSWER','PROPOSAL','REVIEW','CLARIFICATION']
    latency_ms:int=Field(ge=0,le=180000)
    status:Literal['COMPLETED','FAILED']
class RuntimeResultEnvelope(Frame):
    task_id:str=Field(min_length=1,max_length=64)
    runtime_id:Literal['luma-runtime']='luma-runtime'
    device_id:str=Field(min_length=1,max_length=64)
    correlation_id:str=Field(min_length=1,max_length=64)
    result_type:Literal['ANSWER','PROPOSAL','NEEDS_CLARIFICATION','ERROR','MODEL_RESULT']='ANSWER'
    answer:str=Field(default='',max_length=4000)
    citations:tuple[str,...]=Field(default=(),max_length=5)
    proposal:RuntimeProposalEnvelope|None=None
    needs_clarification:bool=False
    security_review:Literal['NONE','WARN','REJECT']='NONE'
    agent_trace_summary:tuple[TraceSummary,...]=Field(default=(),max_length=6)
    runtime_status:Literal['COMPLETED','FAILED']='COMPLETED'
    model_result:ModelResult|None=None
    error_code:Literal['RUNTIME_UNAVAILABLE','RUNTIME_PROTOCOL_ERROR','MODEL_ERROR','KNOWLEDGE_UNAVAILABLE','POLICY_DENIED','TECHNICAL_FAILURE','RUNTIME_POLICY_STALE']|None=None
    @model_validator(mode='after')
    def consistent(self):
        if any(len(x)>200 for x in self.citations):raise ValueError('CITATION_TOO_LARGE')
        if (self.result_type=='PROPOSAL')!=(self.proposal is not None):raise ValueError('PROPOSAL_RESULT_MISMATCH')
        if (self.result_type=='MODEL_RESULT')!=(self.model_result is not None):raise ValueError('MODEL_RESULT_MISMATCH')
        if (self.result_type=='ERROR')!=(self.error_code is not None):raise ValueError('ERROR_RESULT_MISMATCH')
        return self
class RuntimeHeartbeat(Frame):
    runtime_id:Literal['luma-runtime']='luma-runtime'
    device_id:str=Field(min_length=1,max_length=64)
    registry_version:str=Field(min_length=1,max_length=64)
    runtime_status:Literal['ONLINE','BUSY','OFFLINE']
class RuntimeErrorEnvelope(Frame):
    task_id:str=Field(min_length=1,max_length=64)
    correlation_id:str=Field(min_length=1,max_length=64)
    code:Literal['RUNTIME_UNAVAILABLE','RUNTIME_PROTOCOL_ERROR','MODEL_ERROR','KNOWLEDGE_UNAVAILABLE','NEEDS_CLARIFICATION','POLICY_DENIED','TECHNICAL_FAILURE','RUNTIME_POLICY_STALE']
class RuntimeTransport(Protocol):
    def exchange(self,payload:bytes)->bytes: ...
def decode(cls,payload):
    if len(payload)>MAX_FRAME:raise ValueError('FRAME_TOO_LARGE')
    return cls.model_validate_json(payload)
TASK_STATES=('QUEUED','WAITING_FOR_DEVICE','CLAIMED_BY_RUNTIME','ANALYZING','NEEDS_CLARIFICATION','WAITING_AUTHORIZATION','AUTHORIZED','READY_FOR_EXECUTION','EXECUTING','COMPLETED','POLICY_DENIED','CANCELLED','EXPIRED','FAILED')
