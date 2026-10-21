import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from .models import Principal
from .database import DEFAULT_URL,database_path


@dataclass(frozen=True)
class Settings:
    token: str = field(repr=False)
    knowledge_token: str = field(repr=False)
    knowledge_endpoint: str = 'http://127.0.0.1:8765'
    host: str = '127.0.0.1'
    port: int = 8770
    timeout: float = 3.0
    history: bool = False
    packages: tuple[str,...] = ()
    principal: Principal = field(default_factory=Principal)
    database_url: str = DEFAULT_URL
    admin_confirmation_token: str = field(default="",repr=False)

    runtime_token: str = field(default="",repr=False)

    def __post_init__(self):
        if self.runtime_token and (not 32<=len(self.runtime_token)<=256 or not self.runtime_token.isascii() or any(c.isspace() for c in self.runtime_token) or self.runtime_token in (self.token,self.knowledge_token,self.admin_confirmation_token)):
            raise ValueError("INVALID_RUNTIME_CONFIGURATION")
        if self.principal.principal_id!='local-owner' or self.principal.principal_type!='HUMAN_OWNER': raise ValueError('INVALID_OWNER_IDENTITY')
        database_path(self.database_url)
        if self.admin_confirmation_token and (not 32<=len(self.admin_confirmation_token)<=256 or not self.admin_confirmation_token.isascii() or any(c.isspace() for c in self.admin_confirmation_token) or self.admin_confirmation_token in (self.token,self.knowledge_token)):
            raise ValueError("INVALID_CONFIRMATION_CONFIGURATION")
        u=urlsplit(self.knowledge_endpoint)
        tokens=(self.token,self.knowledge_token)
        if (any(not 32<=len(t)<=256 or not t.isascii() or any(c.isspace() for c in t) for t in tokens)
            or self.token==self.knowledge_token or self.host!='127.0.0.1' or not 1024<=self.port<=65535
            or not .05<=self.timeout<=10 or u.scheme!='http' or u.hostname!='127.0.0.1'
            or not u.port or u.username or u.password or u.path not in ('','/') or u.query or u.fragment
            or self.principal.project_scopes not in ((),('meu-gestor',))):
            raise ValueError('INVALID_LOCAL_CONFIGURATION')

    @classmethod
    def from_env(cls):
        get=lambda k,d='':os.environ.get('LUMA_'+k,d)
        try:
            if get('OWNER_TOKEN') and get('TOKEN') and get('OWNER_TOKEN')!=get('TOKEN'): raise ValueError()
            history=get('KNOWLEDGE_HISTORY','false')
            if history not in ('true','false'): raise ValueError()
            return cls(token=get('OWNER_TOKEN') or get('TOKEN'),knowledge_token=get('KNOWLEDGE_TOKEN'),
                knowledge_endpoint=get('KNOWLEDGE_ENDPOINT','http://127.0.0.1:8765'),
                host=get('HOST','127.0.0.1'),port=int(get('PORT','8770')),
                timeout=float(get('TIMEOUT','3')),history=history=='true',
                packages=tuple(x.strip() for x in get('KNOWLEDGE_PACKAGES').split(',') if x.strip()),
                database_url=get('DATABASE_URL',DEFAULT_URL),admin_confirmation_token=get('ADMIN_CONFIRM_TOKEN'),runtime_token=get('RUNTIME_TOKEN'))
        except (ValueError,TypeError):
            raise ValueError('INVALID_LOCAL_CONFIGURATION') from None
