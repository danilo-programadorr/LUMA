"""Data-only future model boundary: no credentials, authority or executor."""
from typing import Literal
from pydantic import Field,field_validator
from .models import Contract,KnowledgeContext
from .grounding import GroundingRequirement

class SecretRef(Contract):
    secret_id:str=Field(pattern=r'^[a-z][a-z0-9_.-]{2,63}$')

class ToolCallProposal(Contract):
    tool_id:str=Field(min_length=1,max_length=64)
    capability:str=Field(min_length=1,max_length=100)
    parameters:dict=Field(default_factory=dict)
    reason:str=Field(max_length=1000)
    correlation_id:str=Field(max_length=64)
    @field_validator('capability')
    @classmethod
    def non_administrative(cls,value):
        from .registry import TOOLS
        if value not in {cap for tool in TOOLS.values() for cap in tool.capabilities}:
            raise ValueError('PROPOSAL_CAPABILITY_DENIED')
        return value

class ModelInputContext(Contract):
    grounding_requirement:GroundingRequirement="REQUIRED"
    user_message:str=Field(max_length=2000)
    session_summary:str=Field(default='',max_length=2000)
    project_id:str=Field(max_length=64)
    knowledge:KnowledgeContext | None=None
    available_tools:tuple[str,...]=()
    pending_action_ids:tuple[str,...]=()
    session_id:str=Field(default='',max_length=64)
    locale:str=Field(default='pt-BR',pattern=r'^[a-z]{2}-[A-Z]{2}$')

class AnswerCitation(Contract):
    document_id:str=Field(min_length=1,max_length=160)
    chunk_id:str=Field(min_length=1,max_length=200)

class LearningProposal(Contract):
    claim:str=Field(min_length=1,max_length=2000)
    evidence:tuple[str,...]=Field(min_length=1,max_length=5)

class ModelDecision(Contract):
    assistant_message:str=Field(max_length=4000)
    intent:str=Field(max_length=1000)
    proposed_actions:tuple[ToolCallProposal,...]=Field(default=(),max_length=3)
    requested_knowledge:tuple[str,...]=()
    confidence:float=Field(ge=0,le=1)
    needs_clarification:bool=False
    citations:tuple[AnswerCitation,...]=Field(default=(),max_length=5)
    learning_candidates:tuple[LearningProposal,...]=Field(default=(),max_length=2)

class AgentExecutionContext(Contract):
    agent_id:str=Field(max_length=64)
    runtime_principal:Literal['luma-runtime']
    project_id:str=Field(max_length=64)
    allowed_capabilities:tuple[str,...]
    session_id:str=Field(max_length=64)
    correlation_id:str=Field(max_length=64)
    @field_validator('allowed_capabilities')
    @classmethod
    def limited(cls,value):
        from .trust_data import RUNTIME_CAPS
        if not set(value)<=set(RUNTIME_CAPS): raise ValueError('AGENT_CAPABILITY_DENIED')
        return value

def sanitized_worker_environment(environment,*,runtime_credential=None):
    # Empty by default. No PATH, PYTHONPATH, proxies, connection strings or arbitrary inherited values.
    result={}
    if runtime_credential is not None:
        if not 32<=len(runtime_credential)<=256 or not runtime_credential.isascii() or any(c.isspace() for c in runtime_credential):
            raise ValueError('INVALID_RUNTIME_CREDENTIAL')
        if runtime_credential!=environment.get('LUMA_RUNTIME_TOKEN') or runtime_credential in {v for k,v in environment.items() if k!='LUMA_RUNTIME_TOKEN'}:
            raise ValueError('ADMIN_CREDENTIAL_DENIED')
        result['LUMA_RUNTIME_TOKEN']=runtime_credential
    return result

def model_input(control,**fields):
    # Trusted backend construction only; rejects known secrets before future serialization.
    value=ModelInputContext(**fields)
    control.safe(value.model_dump(mode='json'),max_chars=2*1024*1024)
    return value
