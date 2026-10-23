"""Strict public requests; authority and definitive risk are server-owned."""
from typing import Literal
from pydantic import Field,model_validator
from .models import Contract

class CanonicalActionEnvelope(Contract):
    project_id:str=Field(min_length=1,max_length=64)
    tool_id:str=Field(min_length=1,max_length=64)
    operation:str=Field(min_length=1,max_length=80)
    resource:str=Field(default='',max_length=200)
    destination:str=Field(default='',max_length=200)
    parameters:dict=Field(default_factory=dict)
    execution_target:Literal['CLOUD','LOCAL_DEVICE','EITHER']='CLOUD'
    target_device_id:str|None=Field(default=None,pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    allowed_paths:list[str]=Field(default_factory=list,max_length=8)
    @model_validator(mode='after')
    def target(self):
        if (self.execution_target=='LOCAL_DEVICE') != bool(self.target_device_id):raise ValueError('DEVICE_TARGET_REQUIRED')
        if len(self.allowed_paths)>8:raise ValueError('INVALID_RESOURCE_SCOPE')
        return self

class ActionCandidate(CanonicalActionEnvelope):
    pass

class ToolCallProposal(CanonicalActionEnvelope):
    reason:str=Field(max_length=500)
    correlation_id:str=Field(max_length=64)
    agent_id:str=Field(max_length=64)
    requested_risk:Literal['LOW','MEDIUM','HIGH','CRITICAL']='LOW'

class AuthorizationRequest(Contract):
    mode:Literal['ONE_SHOT','BOUNDED_WINDOW','RECURRING_POLICY']='ONE_SHOT'
    valid_from:str=Field(max_length=40)
    expires_at:str=Field(max_length=40)
    max_executions:int=Field(ge=1,le=100)
    interval_seconds:int|None=Field(default=None,ge=60,le=2592000)
    late_execution_policy:Literal['SKIP','RUN_LATE_WITHIN_GRACE','REQUIRE_REAUTHORIZATION']='SKIP'
    grace_seconds:int=Field(default=0,ge=0,le=3600)
    confirmation:Literal['AUTHORIZE_EXACT_ACTION']

class JobRequest(Contract):
    authorization_id:str=Field(max_length=64)
    action:CanonicalActionEnvelope
    trigger_type:Literal['IMMEDIATE','SCHEDULED_AT','RECURRING','CONDITION']='IMMEDIATE'
    scheduled_for:str|None=Field(default=None,max_length=40)
    condition_id:str|None=Field(default=None,max_length=64)

class CredentialRef(Contract):
    store:Literal['SECRET_MANAGER']
    reference:str=Field(pattern=r'^[a-zA-Z0-9/_-]{1,200}$')

class ExecutionReconciliation(Contract):
    job_id:str
    idempotency_key:str
    outcome:Literal['CONFIRMED','NOT_FOUND','UNKNOWN']
    external_operation_id:str|None=None


class DeviceRegistration(Contract):
    device_id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    name:str=Field(min_length=1,max_length=100)
    device_type:Literal['WINDOWS']='WINDOWS'

class DeviceHeartbeat(Contract):
    device_id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    executor_version:str=Field(pattern=r'^[0-9.a-z]{1,30}$')
    status:Literal['ONLINE','BUSY','OFFLINE']
    capabilities:list[Literal['sandbox-test']]=Field(default_factory=list,max_length=1)
    current_job_count:int=Field(ge=0,le=1)

class DeviceCredential(Contract):
    device_id:str
    credential_id:str
    secret_reference:CredentialRef|None=None
    mode:Literal['LOCAL_DEVELOPMENT','SECRET_STORE']='LOCAL_DEVELOPMENT'

class LocalResourceScope(Contract):
    allowed_paths:list[str]=Field(default_factory=list,max_length=8)
    default:Literal['DENY']='DENY'

class DevicePollRequest(Contract):
    device_id:str
    timeout_seconds:int=Field(default=20,ge=1,le=30)
    transport:Literal['HTTPS_LONG_POLL']='HTTPS_LONG_POLL'


class TaskAgentExecutionContext(Contract):
    agent_id:str
    runtime_principal:Literal['luma-runtime']='luma-runtime'
    project_id:str
    session_id:str
    correlation_id:str
    task_id:str
    capabilities:tuple[Literal['knowledge.read','runtime.actions.propose'],...]
    knowledge_source_ids:tuple[str,...]=()
    allowed_proposal_types:tuple[Literal['ACTION_REQUEST'],...]=('ACTION_REQUEST',)
    deadline:str
    hop_count:int=Field(ge=0,le=5)
