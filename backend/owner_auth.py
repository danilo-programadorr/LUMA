"""Google identity authenticates; the durable single-owner binding authorizes."""
import hashlib,secrets,time,threading
from dataclasses import dataclass
from sqlalchemy import select,insert,update
from .owner_schema import owner_bindings as bindings,owner_bootstrap as bootstrap
from .app.database import version
from .app.errors import Fault
from .app.models import now

# Bounded tolerance for issuer/local clock differences; expiry remains strict.
OWNER_CLOCK_SKEW_SECONDS=30

@dataclass(frozen=True)
class AuthenticatedOwnerPrincipal:
    internal_owner_id:str
    identity_provider:str
    subject_uid:str
    auth_time:int
    request_correlation_id:str

class GoogleTokenVerifier:
    def __init__(self,project):
        if not project:raise ValueError('IDENTITY_PROJECT_REQUIRED')
        self.project=project
    def verify(self,token):
        from google.oauth2.id_token import verify_firebase_token
        from google.auth.transport.requests import Request
        try:
            claims=verify_firebase_token(token,Request(),audience=self.project,clock_skew_in_seconds=OWNER_CLOCK_SKEW_SECONDS)
            return validate_claims(claims,self.project)
        except Exception:raise Fault('UNAUTHORIZED',401) from None

def validate_claims(c,project):
    current=int(time.time())
    if not isinstance(c,dict):raise Fault('UNAUTHORIZED',401)
    if c.get('aud')!=project or c.get('iss')!='https://securetoken.google.com/'+project:raise Fault('UNAUTHORIZED',401)
    uid=c.get('sub')
    if not isinstance(uid,str) or not 1<=len(uid)<=128 or any(ord(x)<33 for x in uid):raise Fault('UNAUTHORIZED',401)
    for field in ('iat','exp','auth_time'):
        if type(c.get(field)) is not int:raise Fault('UNAUTHORIZED',401)
    if not 0<c['auth_time']<=c['iat']<=current+OWNER_CLOCK_SKEW_SECONDS or not current<c['exp'] or c['exp']<=c['iat']:raise Fault('UNAUTHORIZED',401)
    firebase=c.get('firebase',{})
    if not isinstance(firebase,dict) or firebase.get('sign_in_provider')!='google.com' or firebase.get('tenant'):raise Fault('UNAUTHORIZED',401)
    return {'sub':uid,'auth_time':c['auth_time']}

def require_recent_auth(principal,window_seconds=300):
    # Local pilot policy: five minutes. Refreshing an ID token does not reset auth_time.
    if not -OWNER_CLOCK_SKEW_SECONDS<=int(time.time())-principal.auth_time<=window_seconds:raise Fault('RECENT_AUTH_REQUIRED',403)

class OwnerAuthenticator:
    def __init__(self,control,settings,verifier=None):
        self.control=control;self.settings=settings
        self.verifier=verifier or GoogleTokenVerifier(settings.identity_project)
        self.lock=threading.Lock();self.requests=[]
        with control.store.read() as r:
            if r.connection.execute(select(version.c.version)).scalar_one() not in (5,6,7,8,9):raise ValueError('OWNER_MIGRATION_REQUIRED')
    def rate_limit(self):
        with self.lock:
            current=time.monotonic();self.requests=[t for t in self.requests if t>current-60]
            if len(self.requests)>=120:raise Fault('AUTH_RATE_LIMITED',429)
            self.requests.append(current)
    def event(self,event,result,correlation):
        with self.control.store.transaction() as r:self.control.event(r,None,None,event,result,correlation)
    def identity(self,request):
        self.rate_limit()
        values=request.headers.getlist('authorization')
        try:
            if len(values)!=1:raise Fault('UNAUTHORIZED',401)
            parts=values[0].split(' ')
            if len(parts)!=2 or parts[0].lower()!='bearer' or not parts[1].isascii() or not 1<=len(parts[1])<=16384:raise Fault('UNAUTHORIZED',401)
            return self.verifier.verify(parts[1])
        except Exception:
            self.event('AUTH_LOGIN_REJECTED','UNAUTHORIZED',request.state.correlation_id)
            raise Fault('UNAUTHORIZED',401) from None
    def authenticate(self,request):
        c=self.identity(request)
        with self.control.store.read() as r:row=r.connection.execute(select(bindings).where(bindings.c.id==1)).mappings().first()
        if not row or row['status']!='ACTIVE' or row['provider']!='google.com' or row['subject_uid']!=c['sub']:
            self.event('OWNER_ACCESS_FORBIDDEN','FORBIDDEN',request.state.correlation_id)
            raise Fault('FORBIDDEN',403)
        p=self.control.principal(row['internal_owner_id'])
        if p.principal_type!='HUMAN_OWNER':raise Fault('FORBIDDEN',403)
        request.state.owner=AuthenticatedOwnerPrincipal(p.principal_id,'google.com',c['sub'],c['auth_time'],request.state.correlation_id)
        self.event('AUTH_LOGIN_ACCEPTED','ACCEPTED',request.state.correlation_id)
        return p
    def issue_bootstrap(self):
        code=secrets.token_urlsafe(32)
        with self.control.store.transaction() as r:
            if r.connection.execute(select(bindings.c.id)).first():raise Fault('BOOTSTRAP_DISABLED',403)
            prior=r.connection.execute(select(bootstrap).where(bootstrap.c.id==1)).mappings().first()
            if prior and prior['status']=='ACTIVE' and prior['expires_at']>int(time.time()):raise Fault('BOOTSTRAP_ALREADY_ISSUED',409)
            values=dict(digest=hashlib.sha256(code.encode()).hexdigest(),expires_at=int(time.time())+300,attempts=0,status='ACTIVE')
            if prior:r.connection.execute(update(bootstrap).where(bootstrap.c.id==1).values(**values))
            else:r.connection.execute(insert(bootstrap).values(id=1,**values))
            self.control.event(r,None,None,'OWNER_BOOTSTRAP_STARTED','CREATED','local-bootstrap')
        return code
    def bind(self,claims,code,correlation):
        failure=None
        with self.control.store.transaction() as r:
            existing=r.connection.execute(select(bindings.c.id)).first()
            row=r.connection.execute(select(bootstrap).where(bootstrap.c.id==1)).mappings().first()
            if existing:failure='BOOTSTRAP_DISABLED'
            elif not row or row['status']!='ACTIVE' or row['attempts']>=5 or row['expires_at']<=int(time.time()):failure='BOOTSTRAP_REJECTED'
            else:
                valid=secrets.compare_digest(row['digest'],hashlib.sha256(code.encode()).hexdigest())
                r.connection.execute(update(bootstrap).where(bootstrap.c.id==1).values(attempts=row['attempts']+1,status='USED' if valid else ('LOCKED' if row['attempts']+1>=5 else 'ACTIVE')))
                if not valid:failure='BOOTSTRAP_REJECTED'
                else:
                    stamp=now().isoformat()
                    r.connection.execute(insert(bindings).values(id=1,provider='google.com',subject_uid=claims['sub'],internal_owner_id=self.settings.principal.principal_id,status='ACTIVE',created_at=stamp,bound_at=stamp,revoked_at=None,version=1))
            self.control.event(r,None,None,'OWNER_BOOTSTRAP_REJECTED' if failure else 'OWNER_BOUND',failure or 'BOUND',correlation)
        # Raise after committing failed attempt counters and audit.
        if failure:raise Fault(failure,403)
        return {'status':'BOUND'}
