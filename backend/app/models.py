from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator


def now():
    return datetime.now(timezone.utc)


def ident():
    return uuid4().hex


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)


class Principal(Contract):
    principal_id: str = 'local-owner'
    principal_type: Literal['HUMAN_OWNER','SERVICE_RUNTIME','AGENT_SERVICE','TOOL_SERVICE'] = 'HUMAN_OWNER'
    display_name: str = 'Owner local'
    roles: tuple[str, ...] = ('OWNER',)
    project_scopes: tuple[str, ...] = ('meu-gestor',)
    capabilities: tuple[str, ...] = ('knowledge.read',)
    approval_level: Literal['OWNER_SCOPED'] = 'OWNER_SCOPED'


class Project(Contract):
    project_id: str
    name: str
    status: Literal['ACTIVE','SUSPENDED'] = 'ACTIVE'
    knowledge_endpoint: str
    knowledge_mode: Literal['lexical'] = 'lexical'
    enabled: bool = True
    capabilities: tuple[str, ...] = ('knowledge.read',)
    metadata: dict[str, str] = Field(default_factory=dict)


class Tool(Contract):
    tool_id: str
    status: Literal['PLANNED','ENABLED_LOCAL']
    enabled: bool = False
    capabilities: tuple[str, ...]


class Limits(Contract):
    max_documents: int = Field(default=5,ge=1,le=5)
    max_chunks: int = Field(default=12,ge=1,le=12)
    max_chars: int = Field(default=16000,ge=256,le=16000)


class KnowledgeRequest(Contract):
    project_id: str = Field(min_length=1,max_length=64)
    query: str = Field(min_length=1,max_length=2000)
    package: str | None = Field(default=None,pattern=r'^PACKAGE_[A-Z_]+$')
    include_history: bool = False
    limits: Limits = Field(default_factory=Limits)

    @field_validator('query')
    @classmethod
    def valid_query(cls,v):
        if not v.strip() or any(ord(c)<32 and c not in '\r\n\t' for c in v):
            raise ValueError('INVALID_QUERY')
        return v


class KnowledgeContext(Contract):
    project_id: str
    brain_version: str
    engine_version: str
    query: str
    results: list[dict]
    sources: list[dict]
    warnings: list[str]
    permission_status: Literal['NOT_DETERMINED_BY_RETRIEVAL']
    retrieved_at: datetime = Field(default_factory=now)
    request_id: str
    correlation_id: str
    mode: Literal['lexical'] = 'lexical'
    status: str
    confidence: str
    content_trust: Literal['UNTRUSTED_DATA'] = 'UNTRUSTED_DATA'


class ActionRequest(Contract):
    action_id: str = Field(default_factory=ident)
    principal_id: str
    project_id: str
    tool_id: str
    capability: str
    intent: str = Field(max_length=1000)
    parameters: dict = Field(default_factory=dict)
    risk_level: Literal['LOW','MEDIUM','HIGH']
    approval_requirement: Literal['AUTO','CONFIRM','DENY']
    status: Literal['PROPOSED','WAITING_APPROVAL','APPROVED','DENIED','EXECUTING','SUCCEEDED','FAILED','CANCELLED'] = 'PROPOSED'
    origin_type: Literal['HUMAN_DIRECT','MODEL_PROPOSED','AGENT_PROPOSED','SYSTEM'] = 'SYSTEM'
    origin_id: str | None = None
    session_id: str | None = None
    correlation_id: str | None = None
    created_at: datetime = Field(default_factory=now)


class ApprovalRecord(Contract):
    approval_id: str = Field(default_factory=ident)
    action_id: str
    principal_id: str
    decision: Literal['APPROVE','DENY']
    timestamp: datetime = Field(default_factory=now)
    expires_at: datetime
    scope: str
    reason: str | None = Field(default=None,max_length=500)


class Session(Contract):
    human_principal_id: str | None = None
    runtime_principal_id: str | None = None
    session_id: str = Field(default_factory=ident)
    principal_id: str
    active_project_id: str
    created_at: datetime = Field(default_factory=now)
    last_activity: datetime = Field(default_factory=now)
    status: Literal['ACTIVE','CLOSED'] = 'ACTIVE'


class LearningCandidate(Contract):
    candidate_id: str = Field(default_factory=ident)
    source: str = Field(min_length=1,max_length=500)
    project_id: str
    claim: str = Field(min_length=1,max_length=2000)
    evidence: tuple[str,...]
    confidence: Literal['LOW','MEDIUM','HIGH']
    status: Literal['PROPOSED','VALIDATED','REJECTED','PROMOTED'] = 'PROPOSED'
    created_at: datetime = Field(default_factory=now)


class ModelProvider(Protocol):
    """Future port only. No concrete model provider in Phase 7A."""
    def generate(self, context: "ModelInputContext", correlation_id: str) -> "ModelResult": ...

class Grant(Contract):
    grant_id:str
    principal_id:str
    capability:str
    project_id:str | None=None
    tool_id:str | None=None
    scope:Literal['GLOBAL','PROJECT']
    granted_by:str
    created_at:str
    expires_at:str | None=None
    status:Literal['ACTIVE','REVOKED','EXPIRED']

class RetentionPolicy(Contract):
    category:Literal['sessions','actions','approvals','learning_candidates','audit']
    mode:Literal['NO_AUTO_DELETE']='NO_AUTO_DELETE'
    purge_enabled:Literal[False]=False
