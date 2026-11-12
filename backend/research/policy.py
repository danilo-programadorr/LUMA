"""Deterministic routing and egress. Retrieved content never changes authority."""
import hashlib,ipaddress,re,socket,unicodedata
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from backend.app.errors import Fault
from .contracts import Route,Source

def folded(text):return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')
class KnowledgeRouter:
    def route(self,query,allow_web=True,mode='AUTO'):
        q=folded(query)
        no_web=not allow_web or bool(re.search(r'nao (?:pesquise|busque|use).*internet|sem (?:internet|web)',q))
        current=bool(re.search(r'hoje|agora|recente|atual|noticia|ultima versao|mudou.*regra|vulnerabilidade',q))
        project=bool(re.search(r'\bluma\b|meu gestor|nosso projeto|nosso backend|nossa versao|projeto interno',q))
        transform=bool(re.match(r'(reescreva|traduza|formate|calcule|resuma este texto)\b',q))
        private=bool(re.search(r'biblioteca privada|private library|meus livros|pdf privado',q))
        explicit=bool(re.search(r'pesquise|busque na (?:web|internet)|verifique na internet',q))
        if private:kind='PRIVATE_LIBRARY_FUTURE'
        elif transform:kind='NO_RETRIEVAL'
        elif no_web:kind='PROJECT_FIRST' if project else 'NO_RETRIEVAL'
        elif project and (current or explicit or mode=='PROJECT_HYBRID'):kind='HYBRID_WEB_PROJECT'
        elif project:kind='PROJECT_FIRST'
        elif current or explicit:kind='WEB_REQUIRED'
        else:kind='WEB_FIRST'
        inferred='NEWS' if 'noticia' in q else 'SCIENTIFIC' if re.search(r'cientific|estudo|meta.analise',q) else 'TECHNICAL' if re.search(r'react|python|api|software|vulnerabilidade|codigo',q) else 'GENERAL_WEB'
        horizon='REALTIME' if re.search(r'agora|tempo real',q) else 'DAY' if re.search(r'hoje|noticia',q) else 'CURRENT_VERSION' if re.search(r'versao|vulnerabilidade',q) else 'UNKNOWN' if current else 'EVERGREEN'
        return Route(route=kind,freshness_required=current and not no_web,freshness_horizon=horizon,mode=inferred if mode=='AUTO' else mode,reason='USER_WEB_DISABLED' if no_web else 'DETERMINISTIC_POLICY')

class ExternalQueryPolicy:
    def __init__(self,known_secrets=()):self.known_secrets=tuple(x for x in known_secrets if x)
    def check(self,text):
        if not isinstance(text,str) or not text.strip() or len(text)>1200:raise Fault('RESEARCH_EGRESS_BLOCKED',400)
        q=unicodedata.normalize('NFKC',text).strip()
        patterns=[r'AIza[\w-]{20,}',r'GOCSPX-',r'-----BEGIN .*PRIVATE KEY',r'Bearer\s+\S+',r'eyJ[\w-]+\.eyJ',r'1//[\w-]+',r'(?:api[_ -]?key|password|senha|secret|token|bootstrap|enrollment)\s*[:=]\s*\S+',r'(?:postgres|mysql|mongodb)(?:ql)?://',r'[A-Za-z]:[\\/]',r'/home/|/Users/|/etc/',r'[\w.+-]+@[\w.-]+\.[a-z]{2,}',r'\b(?:\d[ .-]?){11,16}\b',r'(?<![\w-])[A-Za-z0-9_-]{40,}(?![\w-])',r'```|Traceback \(most recent',r'confidencial|documento interno|conteudo privado|proprietary|private document']
        if any(re.search(p,q,re.I) for p in patterns) or any(s in q for s in self.known_secrets) or any(ord(x)<32 and x not in '\n\t' for x in q):raise Fault('RESEARCH_EGRESS_BLOCKED',403)
        return ' '.join(q.split())

class URLPolicy:
    def check(self,url,resolve=False):
        try:
            if len(url)>2048 or any(ord(c)<33 for c in url) or '\\' in url:raise ValueError()
            u=urlsplit(url);host=(u.hostname or '').encode('idna').decode().lower().rstrip('.')
            if u.scheme not in ('http','https') or not host or u.username or u.password or (u.port and u.port not in (80,443)):raise ValueError()
            if host=='localhost' or host.endswith(('.localhost','.local','.internal','.lan','.test')) or host=='metadata.google.internal' or '.' not in host and ':' not in host:raise ValueError()
            try:
                ip=ipaddress.ip_address(host)
            except ValueError:
                if re.fullmatch(r'[0-9.xa-f]+',host) or '%' in host:raise ValueError()
                ip=None
            if ip and (not ip.is_global or ip.is_multicast):raise ValueError()
            if resolve:
                ips={x[4][0] for x in socket.getaddrinfo(host,u.port or 443,type=socket.SOCK_STREAM)}
                if not ips or any(not ipaddress.ip_address(x).is_global for x in ips):raise ValueError()
            params=parse_qsl(u.query,keep_blank_values=True)
            if any(re.search(r'token|key|secret|signature|credential|password|auth|session',k,re.I) for k,v in params):raise ValueError()
            clean=urlunsplit((u.scheme,host,u.path or '/',urlencode([(k,v) for k,v in params if not k.lower().startswith('utm_') and k.lower() not in ('gclid','fbclid')]),''))
            return clean
        except (ValueError,UnicodeError,OSError):raise Fault('UNSAFE_URL',400) from None

class SourceRankingPolicy:
    # Explicit publisher-domain evidence, not a suffix-based claim of truth.
    official={'react.dev':'React documentation','docs.python.org':'Python documentation','ai.google.dev':'Google AI documentation','developers.openai.com':'OpenAI documentation','nvd.nist.gov':'NIST advisories'}
    def normalize(self,url,title,stamp,provider):
        canonical=URLPolicy().check(url);domain=urlsplit(canonical).hostname
        publisher=self.official.get(domain)
        kind='OFFICIAL' if publisher else 'ACADEMIC_INDEX' if domain in ('pubmed.ncbi.nlm.nih.gov','arxiv.org') else 'UNKNOWN'
        return Source(source_id=hashlib.sha256(canonical.encode()).hexdigest()[:24],title=title[:300],url=url,canonical_url=canonical,domain=domain,publisher=publisher,source_type=kind,quality_tier=3 if publisher else 1 if kind=='ACADEMIC_INDEX' else 0,retrieved_at=stamp,freshness='RETRIEVED_NOW',provider=provider)
    def rank(self,sources):return sorted(sources,key=lambda s:-s.quality_tier)

class ResearchUsagePolicy:
    max_calls=2
    max_urls=3
    max_sources=8
    request_timeout_seconds=240
    lease_seconds=90
    owner_per_minute=6
    daily_requests=30
    cache_ttl={'REALTIME':0,'DAY':60,'WEEK':300,'MONTH':900,'CURRENT_VERSION':60,'EVERGREEN':3600,'UNKNOWN':0}
    def before_call(self,calls):
        if calls>=self.max_calls:raise Fault('RESEARCH_BUDGET_EXCEEDED',429)
