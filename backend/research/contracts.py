from typing import Literal
from pydantic import Field,model_validator
from backend.app.models import Contract

ID= r'^[a-f0-9]{32}$'
class ResearchCreate(Contract):
    project_id:str=Field(min_length=1,max_length=64,pattern=r'^[a-z0-9-]+$')
    query:str=Field(min_length=1,max_length=1200)
    target_device_id:str=Field(pattern=ID)
    idempotency_key:str=Field(pattern=ID)
    mode:Literal['AUTO','GENERAL_WEB','OFFICIAL_FIRST','SCIENTIFIC','TECHNICAL','NEWS','PROJECT_HYBRID']='AUTO'
    depth:Literal['QUICK','STANDARD','DEEP']='STANDARD'
    allow_web:bool=True
    public_query:str|None=Field(default=None,min_length=1,max_length=500)
    urls:list[str]=Field(default_factory=list,max_length=3)

class Route(Contract):
    route:Literal['WEB_FIRST','WEB_REQUIRED','PROJECT_FIRST','HYBRID_WEB_PROJECT','NO_RETRIEVAL','PRIVATE_LIBRARY_FUTURE']
    freshness_required:bool=False
    freshness_horizon:Literal['REALTIME','DAY','WEEK','MONTH','CURRENT_VERSION','EVERGREEN','UNKNOWN']='UNKNOWN'
    mode:str='GENERAL_WEB'
    reason:str=Field(max_length=100)

class ResearchRequest(Contract):
    protocol_version:Literal['1']='1'
    research_id:str=Field(pattern=ID)
    project_id:str=Field(min_length=1,max_length=64)
    query:str=Field(min_length=1,max_length=1200)
    public_query:str|None=Field(default=None,max_length=500)
    urls:list[str]=Field(default_factory=list,max_length=3)
    route:Route
    target_device_id:str=Field(pattern=ID)
    requested_at:int
    expires_at:int
    max_sources:int=Field(default=6,ge=1,le=8)
    max_depth:Literal['QUICK','STANDARD','DEEP']='STANDARD'
    egress_class:Literal['PUBLIC_GENERIC_ONLY']='PUBLIC_GENERIC_ONLY'

class Source(Contract):
    source_id:str=Field(max_length=64)
    title:str=Field(max_length=300)
    url:str=Field(max_length=2048)
    canonical_url:str=Field(max_length=2048)
    domain:str=Field(max_length=253)
    origin:Literal['WEB','PROJECT','PRIVATE_LIBRARY_FUTURE']='WEB'
    publisher:str|None=Field(default=None,max_length=200)
    source_type:str=Field(default='UNKNOWN',max_length=30)
    published_at:str|None=Field(default=None,max_length=40)
    event_at:str|None=Field(default=None,max_length=40)
    retrieved_at:int
    quality_tier:int=Field(default=0,ge=0,le=3)
    freshness:Literal['RETRIEVED_NOW','UNKNOWN']='UNKNOWN'
    provider:str=Field(max_length=60)

class Citation(Contract):
    citation_id:str=Field(max_length=64)
    source_id:str=Field(max_length=64)
    start_index:int=Field(ge=0,le=6000)
    end_index:int=Field(ge=1,le=6000)

class Usage(Contract):
    model_calls:int=Field(default=0,ge=0,le=2)
    search_queries:int|None=Field(default=None,ge=0,le=100)
    url_context_urls:int=Field(default=0,ge=0,le=3)
    input_tokens:int|None=Field(default=None,ge=0)
    output_tokens:int|None=Field(default=None,ge=0)
    thought_tokens:int|None=Field(default=None,ge=0)
    tool_use_tokens:int|None=Field(default=None,ge=0)
    total_tokens:int|None=Field(default=None,ge=0)
    cached_tokens:int|None=Field(default=None,ge=0)
    latency_ms:int=Field(default=0,ge=0)
    incremental_cost_usd:float|None=Field(default=None,ge=0)

class GoogleDisplayArtifact(Contract):
    provider:Literal['gemini_google_search']='gemini_google_search'
    provenance:Literal['AUTHENTICATED_GOOGLE_PROVIDER']='AUTHENTICATED_GOOGLE_PROVIDER'
    retention:Literal['TRANSIENT_NON_PERSISTABLE_NON_REUSABLE']='TRANSIENT_NON_PERSISTABLE_NON_REUSABLE'
    search_suggestions_html:list[str]=Field(min_length=1,max_length=5)
    presentation:Literal['SANDBOXED_FRAME','ISOLATED_WINDOW']='SANDBOXED_FRAME'
    @model_validator(mode='after')
    def bounded(self):
        if any(not html or len(html.encode('utf-8'))>20000 for html in self.search_suggestions_html):raise ValueError('INVALID_GOOGLE_ARTIFACT')
        return self

class ResearchResult(Contract):
    protocol_version:Literal['1']='1'
    research_id:str=Field(pattern=ID)
    status:Literal['COMPLETED','FAILED']
    answer:str=Field(default='',max_length=6000)
    project_answer:str=Field(default='',max_length=4000)
    sources:list[Source]=Field(default_factory=list,max_length=8)
    citations:list[Citation]=Field(default_factory=list,max_length=24)
    project_evidence:list[str]=Field(default_factory=list,max_length=8)
    freshness_status:Literal['EVIDENCED','UNAVAILABLE','NOT_REQUIRED']='UNAVAILABLE'
    agreement_status:Literal['UNKNOWN','CONFLICTING']='UNKNOWN'
    conflicting_sources:list[str]=Field(default_factory=list,max_length=8)
    uncertainty_note:str=Field(default='Sources may not be independent; retrieval is not exhaustive.',max_length=500)
    provider:str=Field(default='none',max_length=60)
    model:str=Field(default='none',max_length=80)
    usage:Usage=Field(default_factory=Usage)
    completed_at:int
    error_code:str|None=Field(default=None,max_length=80,pattern=r'^[A-Z_]+$')
    # Legacy non-Google shape stays empty; Google never reconstructs suggestions.
    search_suggestions:list[dict[str,str]]=Field(default_factory=list,max_length=0)
    provider_display_artifact:GoogleDisplayArtifact|None=None
    @model_validator(mode='after')
    def consistent(self):
        if self.provider_display_artifact and (self.provider!='gemini_google_search' or self.status!='COMPLETED'):raise ValueError('GOOGLE_ONLY_ARTIFACT')
        ids={s.source_id for s in self.sources}
        if len(ids)!=len(self.sources):raise ValueError('DUPLICATE_SOURCE_ID')
        for c in self.citations:
            if c.source_id not in ids or not c.start_index<c.end_index<=len(self.answer):raise ValueError('INVALID_CITATION')
        if not set(self.conflicting_sources)<=ids:raise ValueError('INVALID_CONFLICT')
        if self.status=='FAILED' and (self.answer or not self.error_code):raise ValueError('UNSAFE_FAILED_ANSWER')
        return self

class ResearchPoll(Contract):pass
class ResearchHeartbeat(Contract):
    protocol_version:Literal['1']='1'
    capability:Literal['WEB_RESEARCH']='WEB_RESEARCH'
class ResearchLease(Contract):
    research_id:str=Field(pattern=ID)
    lease_id:str=Field(pattern=ID)
class ResearchProgress(ResearchLease):
    stage:Literal['SEARCHING_WEB','READING_SOURCES','SYNTHESIZING']
class ResearchDelivery(ResearchLease):
    result:ResearchResult
class ResearchGrant(Contract):
    enabled:bool
