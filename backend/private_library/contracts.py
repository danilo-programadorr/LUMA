import hashlib
from typing import Literal, Annotated
from pydantic import Field, model_validator
from backend.app.models import Contract

ID = r'^[a-f0-9]{32}$'
PROJECT = r'^[a-z0-9][a-z0-9-]{0,63}$'

class SourceMetadata(Contract):
    source_id: str = Field(pattern=ID)
    project_id: str = Field(pattern=PROJECT)
    device_id: str = Field(pattern=ID)
    title: str = Field(min_length=1, max_length=160, pattern=r'^[^\x00-\x1f]+$')
    content_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    extension: Literal['.pdf', '.txt', '.md']
    byte_count: int = Field(ge=1, le=8388608)
    page_count: int = Field(ge=0, le=500)
    chunk_count: int = Field(ge=1, le=4000)
    origin: Literal['LOCAL_USER_FILE'] = 'LOCAL_USER_FILE'
    index_version: Literal['1'] = '1'

class PrivateExcerpt(Contract):
    source_id: str = Field(pattern=ID)
    source_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    chunk_id: str = Field(pattern=r'^[a-f0-9]{24}$')
    excerpt: str = Field(min_length=1, max_length=1000)
    page: int | None = Field(default=None, ge=1, le=500)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    score: float = Field(ge=0, le=10000)

class LibraryGrant(Contract):
    enabled: bool

class LibraryHeartbeat(Contract):
    protocol_version: Literal['1'] = '1'
    capability: Literal['PRIVATE_LIBRARY'] = 'PRIVATE_LIBRARY'

class LibraryScope(Contract):
    project_id: str = Field(pattern=PROJECT)

class LibraryRegister(Contract):
    source: SourceMetadata

class LibraryQueryCreate(Contract):
    project_id: str = Field(pattern=PROJECT)
    target_device_id: str = Field(pattern=ID)
    query: str = Field(min_length=1, max_length=1200)
    idempotency_key: str = Field(pattern=ID)
    source_ids: list[str] = Field(default_factory=list, max_length=8)

class LibraryLease(Contract):
    query_id: str = Field(pattern=ID)
    lease_id: str = Field(pattern=ID)

class LibraryDelivery(LibraryLease):
    matches: list[PrivateExcerpt] = Field(default_factory=list, max_length=5)
    error_code: Literal['LIBRARY_STORAGE_INTEGRITY','LIBRARY_SOURCE_UNAVAILABLE','LIBRARY_QUERY_INVALID','LIBRARY_LOCAL_FAILURE'] | None = None

class Empty(Contract):
    pass

def source_id(project_id, device_id, content_hash):
    return hashlib.sha256((project_id + '\0' + device_id + '\0' + content_hash).encode()).hexdigest()[:32]

class LibraryCheck(LibraryScope):
    query_id: str | None = Field(default=None, pattern=ID)
    lease_id: str | None = Field(default=None, pattern=ID)
    @model_validator(mode='after')
    def paired(self):
        if (self.query_id is None) != (self.lease_id is None):raise ValueError('LIBRARY_LEASE_PAIR_REQUIRED')
        return self

class LibraryWork(Contract):
    query_id: str = Field(pattern=ID)
    project_id: str = Field(pattern=PROJECT)
    target_device_id: str = Field(pattern=ID)
    query: str = Field(min_length=1,max_length=1200)
    source_ids: list[Annotated[str,Field(pattern=ID)]] = Field(min_length=1,max_length=500)
    expires_at: int = Field(ge=1)
