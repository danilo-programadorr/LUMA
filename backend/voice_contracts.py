"""Architecture-only voice and collaboration boundaries. No live adapter here."""
from typing import Protocol,Literal
from pydantic import Field
from backend.app.models import Contract

class VoiceSessionIntent(Contract):
    provider:Literal['GEMINI_LIVE','OPENAI_REALTIME','OPENAI_GPT_LIVE']
    locale:Literal['pt-BR']='pt-BR'
    session_id:str=Field(min_length=1,max_length=64)
    enabled:Literal[False]=False
class AgentContribution(Contract):
    agent_id:Literal['luma','development','security','data','product','qa','growth','content','codex']
    kind:Literal['MESSAGE','EVIDENCE','PROPOSAL','OBJECTION','CONCLUSION']
    content:str=Field(min_length=1,max_length=2000)
    evidence_refs:list[str]=Field(default_factory=list,max_length=8)
    authority:Literal['ADVISORY_ONLY']='ADVISORY_ONLY'
class CollaborationPlan(Contract):
    mode:Literal['PARALLEL','SEQUENTIAL']
    contributions:list[AgentContribution]=Field(default_factory=list,max_length=18)
    consolidator:Literal['LUMA_ADK']='LUMA_ADK'
    approval_authority:Literal['NONE']='NONE'
class VoiceProvider(Protocol):
    """Future interface. Events are user intent or playback, never approval."""
    def capabilities(self)->dict:...
    async def connect(self,session:VoiceSessionIntent):...
    async def send_audio(self,audio:bytes):...
    async def interrupt(self):...
    async def close(self):...
    def events(self):...
VOICE_EVALUATION={'primary':'GEMINI_LIVE','challenger':['OPENAI_REALTIME','OPENAI_GPT_LIVE'],'orchestration':'GEMINI_GOOGLE_ADK','production_enabled':False,'selection':'PENDING_OWNER_AUTHORIZED_REAL_AB_TEST'}
class PrivateLibraryProvider(Protocol):
    """Reserved local/private retrieval; no automatic web egress or ingestion."""
    def retrieve(self,project_id:str,query:str):...
