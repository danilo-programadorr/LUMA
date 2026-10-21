from typing import Literal
from pydantic import Field
from .models import Contract

class StateChange(Contract):
    state:Literal['RUNNING','PAUSED','LOCKED']
    confirmation:Literal['UNLOCK_LUMA'] | None=None

class ProjectChange(Contract):
    name:str | None=Field(default=None,min_length=1,max_length=100)
    status:Literal['ACTIVE','SUSPENDED'] | None=None
    enabled:bool | None=None

class Revoke(Contract):
    project_id:Literal['meu-gestor']
    tool_id:str | None=Field(default=None,max_length=64)
    capability:str=Field(min_length=1,max_length=100)
    reason:str=Field(min_length=1,max_length=500)
    expires_at:str | None=Field(default=None,max_length=40)

class ActionCreate(Contract):
    project_id:Literal['meu-gestor']
    tool_id:str=Field(min_length=1,max_length=64)
    capability:str=Field(min_length=1,max_length=100)
    intent:str=Field(min_length=1,max_length=1000)
    parameters:dict=Field(default_factory=dict)

class Decision(Contract):
    decision:Literal['APPROVE','DENY']
    scope:str=Field(pattern=r'^[a-f0-9]{64}$')
    confirmation:Literal['HUMAN_DECISION']
    reason:str | None=Field(default=None,max_length=500)

class ActionTransition(Contract):
    status:Literal['CANCELLED']

class SessionCreate(Contract):
    project_id:Literal['meu-gestor']

class LearningCreate(Contract):
    project_id:Literal['meu-gestor']
    source:str=Field(min_length=1,max_length=500)
    claim:str=Field(min_length=1,max_length=2000)
    evidence:list[str]=Field(min_length=1,max_length=10)
    confidence:Literal['LOW','MEDIUM','HIGH']

class LearningChange(Contract):
    status:Literal['VALIDATED','REJECTED']

class GrantCreate(Contract):
    principal_id:str=Field(min_length=1,max_length=64)
    capability:str=Field(min_length=1,max_length=100)
    project_id:str | None=Field(default=None,max_length=64)
    tool_id:str | None=Field(default=None,max_length=64)
    expires_at:str | None=Field(default=None,max_length=40)
