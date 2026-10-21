import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from .models import Principal


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

    def __post_init__(self):
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
            history=get('KNOWLEDGE_HISTORY','false')
            if history not in ('true','false'): raise ValueError()
            return cls(token=get('TOKEN'),knowledge_token=get('KNOWLEDGE_TOKEN'),
                knowledge_endpoint=get('KNOWLEDGE_ENDPOINT','http://127.0.0.1:8765'),
                host=get('HOST','127.0.0.1'),port=int(get('PORT','8770')),
                timeout=float(get('TIMEOUT','3')),history=history=='true',
                packages=tuple(x.strip() for x in get('KNOWLEDGE_PACKAGES').split(',') if x.strip()))
        except (ValueError,TypeError):
            raise ValueError('INVALID_LOCAL_CONFIGURATION') from None
