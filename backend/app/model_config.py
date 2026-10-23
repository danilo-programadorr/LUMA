import os,re
from dataclasses import dataclass,field

# Reserved names only; no execution configuration is implemented for these profiles.
FUTURE_PROFILES=('AGENTIC','DEEP_REASONING')

@dataclass(frozen=True)
class ModelSettings:
    provider:str='disabled'
    api_key:str=field(default='',repr=False)
    model:str=''
    timeout:float=30.0
    max_input_chars:int=2000
    max_knowledge_chars:int=24000
    max_conversation_chars:int=8000
    profile:str='CONVERSATIONAL'
    max_output_tokens:int=32768
    thinking_level:str='low'
    attempts:int=1
    def __post_init__(self):
        if self.provider not in ('disabled','gemini'): raise ValueError('INVALID_MODEL_CONFIG')
        if self.model and not re.fullmatch(r'gemini-[a-z0-9][a-z0-9.-]{1,80}',self.model): raise ValueError('INVALID_MODEL_CONFIG')
        if self.api_key and (not 16<=len(self.api_key)<=256 or not self.api_key.isascii() or any(c.isspace() for c in self.api_key)):
            raise ValueError('INVALID_MODEL_CONFIG')
        if not (1<=self.timeout<=60 and 1<=self.max_input_chars<=2000 and 256<=self.max_knowledge_chars<=32000
            and 0<=self.max_conversation_chars<=8000 and self.profile=='CONVERSATIONAL' and self.max_output_tokens==32768 and self.thinking_level=='low' and self.attempts==1):
            raise ValueError('INVALID_MODEL_CONFIG')
    @classmethod
    def from_env(cls,settings):
        get=lambda k,d='':os.environ.get('LUMA_'+k,d)
        try:
            alias=os.environ.get('GEMINI_API_KEY','');key=get('GEMINI_API_KEY') or alias
            if alias and get('GEMINI_API_KEY') and alias!=get('GEMINI_API_KEY'): raise ValueError()
            result=cls(provider=get('MODEL_PROVIDER','disabled'),api_key=key,model=get('GEMINI_MODEL'),
                timeout=float(get('MODEL_TIMEOUT','30')),max_input_chars=int(get('MODEL_MAX_INPUT_CHARS','2000')),
                max_knowledge_chars=int(get('MODEL_MAX_KNOWLEDGE_CHARS','24000')),max_conversation_chars=int(get('MODEL_MAX_CONVERSATION_CHARS','8000')))
            result.check_separation(settings)
            return result
        except (ValueError,TypeError): raise ValueError('INVALID_MODEL_CONFIG') from None
    def check_separation(self,settings):
        if self.api_key and self.api_key in (settings.token,settings.runtime_token,settings.admin_confirmation_token,settings.knowledge_token):
            raise ValueError('MODEL_CREDENTIAL_REUSE')
    @property
    def configured(self): return self.provider=='gemini' and bool(self.api_key and self.model)
