import time,secrets,uuid
from pathlib import Path
import pytest
from sqlalchemy import select,update,insert
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from backend.migrate import migrate
from backend.control_plane_app import ControlPlaneSettings,create_control_plane
from backend.owner_auth import validate_claims,require_recent_auth,AuthenticatedOwnerPrincipal
from backend.owner_schema import owner_bindings,owner_bootstrap
from backend.app.errors import Fault

PROJECT='synthetic-project'
def claims(**changes):
    t=int(time.time());return dict(sub='synthetic-owner',aud=PROJECT,iss='https://securetoken.google.com/'+PROJECT,iat=t,exp=t+3600,auth_time=t,firebase={'sign_in_provider':'google.com'},**changes)
class Verifier:
    def verify(self,token):
        if token not in ('owner-fixture','other-fixture'):raise Fault('UNAUTHORIZED',401)
        c=claims();c['sub']='synthetic-owner' if token=='owner-fixture' else 'synthetic-other'
        return validate_claims(c,PROJECT)
@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv('LUMA_ENV','test')
    p=Path('runtime')/('auth-test-'+uuid.uuid4().hex+'.db');url='sqlite:///'+p.resolve().as_posix()
    migrate(url,owner=True)
    app=create_control_plane(ControlPlaneSettings(database_url=url,owner_auth_mode='IDENTITY_PLATFORM',identity_project=PROJECT),_test_verifier=Verifier())
    with TestClient(app,base_url='http://127.0.0.1') as client:yield app,client
    p.unlink(missing_ok=True)
def headers(token='owner-fixture'):return {'Authorization':'Bearer '+token}
def bind(app,client):
    code=app.state.owner_auth.issue_bootstrap()
    response=client.post('/v1/owner/bootstrap',headers=headers(),json={'code':code})
    assert response.status_code==200,response.text
    return code
@pytest.mark.parametrize('field,value',[('aud','wrong'),('iss','wrong'),('sub',''),('sub','x'*129),('sub',123),('iat',0),('iat',9999999999),('exp',1),('exp',True),('auth_time',None),('auth_time',9999999999),('firebase',{}),('firebase',{'sign_in_provider':'password'}),('firebase',{'sign_in_provider':'google.com','tenant':'other'})])
def test_invalid_claims(field,value):
    c=claims();c[field]=value
    with pytest.raises(Fault):validate_claims(c,PROJECT)
def test_valid_claims():assert validate_claims(claims(),PROJECT)['sub']=='synthetic-owner'
@pytest.mark.parametrize('mode',['UNKNOWN','TEST','identity_platform',''])
def test_invalid_mode(mode):
    with pytest.raises(ValueError):ControlPlaneSettings(owner_auth_mode=mode)
def test_missing_project():
    with pytest.raises(ValueError):ControlPlaneSettings(owner_auth_mode='IDENTITY_PLATFORM')
def test_no_token(setup):assert setup[1].get('/v1/owner/me').status_code==401
def test_invalid_signature_adapter(setup):assert setup[1].get('/v1/owner/me',headers=headers('invalid')).status_code==401
def test_first_login_not_owner(setup):assert setup[1].get('/v1/owner/me',headers=headers()).status_code==403
def test_binding_and_me(setup):
    a,c=setup;bind(a,c);r=c.get('/v1/owner/me',headers=headers());assert r.status_code==200
    assert set(r.json())=={'internal_owner_id','provider','status','auth_time','auth_age_seconds'}
def test_other_uid_forbidden(setup):
    a,c=setup;bind(a,c);assert c.get('/v1/owner/me',headers=headers('other-fixture')).status_code==403
def test_forged_body(setup):
    a,c=setup;bind(a,c);assert c.post('/v1/admin/state',headers=headers('other-fixture'),json={'owner_id':'synthetic-owner'}).status_code==403
def test_bootstrap_replay(setup):
    a,c=setup;code=bind(a,c);assert c.post('/v1/owner/bootstrap',headers=headers(),json={'code':code}).status_code==403
def test_bootstrap_extra_fields(setup):
    a,c=setup;code=a.state.owner_auth.issue_bootstrap();assert c.post('/v1/owner/bootstrap',headers=headers(),json={'code':code,'owner_id':'forged'}).status_code==400
def test_attempts_durable(setup):
    a,c=setup;code=a.state.owner_auth.issue_bootstrap()
    for _ in range(5):assert c.post('/v1/owner/bootstrap',headers=headers(),json={'code':'wrong'}).status_code==403
    assert c.post('/v1/owner/bootstrap',headers=headers(),json={'code':code}).status_code==403
    with a.state.control.store.read() as r:assert r.connection.execute(select(owner_bootstrap.c.attempts)).scalar_one()==5
def test_expired_bootstrap(setup):
    a,c=setup;code=a.state.owner_auth.issue_bootstrap()
    with a.state.control.store.transaction() as r:r.connection.execute(update(owner_bootstrap).values(expires_at=0))
    assert c.post('/v1/owner/bootstrap',headers=headers(),json={'code':code}).status_code==403
def test_disabled_owner(setup):
    a,c=setup;bind(a,c)
    with a.state.control.store.transaction() as r:r.connection.execute(update(owner_bindings).values(status='REVOKED'))
    assert c.get('/v1/owner/me',headers=headers()).status_code==403
@pytest.mark.parametrize('path',['/v1/admin/state','/v1/admin/grants','/v1/admin/audit','/v1/owner/me'])
def test_route_protection(setup,path):assert setup[1].get(path).status_code==401
def test_health_sanitized(setup):assert setup[1].get('/health').json()['migration_status']=='CURRENT'
def test_cors_denied(setup):assert setup[1].get('/v1/owner/me',headers={'Origin':'https://evil.example'}).status_code==403
def test_cors_preflight(setup):
    r=setup[1].options('/v1/owner/me',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'})
    assert r.headers['access-control-allow-origin']=='http://localhost:5173'
def test_audit_sanitized(setup):
    a,c=setup;code=bind(a,c)
    with a.state.control.store.read() as r:
        events=str(r.rows('audit_events'));assert code not in events and 'owner-fixture' not in events
    assert a.state.control.listing(a.state.control.principal(),'audit_verify')['verified']
def test_auth_does_not_authorize_execution(setup):
    a,c=setup;bind(a,c);c.get('/v1/owner/me',headers=headers())
    with a.state.control.store.read() as r:
        for name in ('actions','approvals','execution_authorizations','jobs'):assert r.rows(name)==[]
def test_recent_auth():require_recent_auth(AuthenticatedOwnerPrincipal('x','google.com','y',int(time.time()),'c'))
def test_stale_auth():
    with pytest.raises(Fault):require_recent_auth(AuthenticatedOwnerPrincipal('x','google.com','y',int(time.time())-301,'c'))
def test_uid_not_email():
    c=claims();c['email']='owner@example.invalid';c['sub']='other';assert validate_claims(c,PROJECT)['sub']=='other'
def test_legacy_token_rejected(setup):assert setup[1].get('/v1/owner/me',headers=headers('L'*40)).status_code==401

@pytest.mark.parametrize('tamper',[False,True])
def test_google_verifier_real_signature(monkeypatch,tamper):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization,hashes
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from datetime import datetime,timedelta,timezone
    from google.auth import jwt,crypt
    from backend.owner_auth import GoogleTokenVerifier
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'synthetic-test')])
    certificate=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(1).not_valid_before(datetime.now(timezone.utc)-timedelta(days=1)).not_valid_after(datetime.now(timezone.utc)+timedelta(days=1)).sign(key,hashes.SHA256())
    cert=certificate.public_bytes(serialization.Encoding.PEM).decode()
    pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    token=jwt.encode(crypt.RSASigner.from_string(pem,key_id='fixture'),claims()).decode()
    if tamper:
        parts=token.split('.');parts[2]=('A' if parts[2][0]!='A' else 'B')+parts[2][1:];token='.'.join(parts)
    monkeypatch.setattr('google.oauth2.id_token._fetch_certs',lambda *args,**kwargs:{'fixture':cert})
    verifier=GoogleTokenVerifier(PROJECT)
    if tamper:
        with pytest.raises(Fault):verifier.verify(token)
    else:assert verifier.verify(token)['sub']=='synthetic-owner'

def test_rate_limit(setup):
    a,c=setup
    a.state.owner_auth.requests=[time.monotonic()]*120
    assert c.get('/v1/owner/me',headers=headers()).status_code==429

def test_test_adapter_forbidden_outside_test(setup,monkeypatch):
    a,c=setup;monkeypatch.delenv('LUMA_ENV')
    with pytest.raises(ValueError,match='TEST_ADAPTER_DENIED'):
        create_control_plane(a.state.owner_auth.settings,_test_verifier=Verifier())


def test_local_bootstrap_renewal_after_expiry(setup):
    a,c=setup;old=a.state.owner_auth.issue_bootstrap()
    with a.state.control.store.transaction() as r:r.connection.execute(update(owner_bootstrap).values(expires_at=0))
    new=a.state.owner_auth.issue_bootstrap();assert new!=old
    assert c.post('/v1/owner/bootstrap',headers=headers(),json={'code':old}).status_code==403
    assert c.post('/v1/owner/bootstrap',headers=headers(),json={'code':new}).status_code==200

def test_complete_route_inventory_unauthenticated(setup):
    a,c=setup
    for template,operations in a.openapi()['paths'].items():
        if not template.startswith('/v1/'):continue
        path=__import__('re').sub(r'\{[^}]+\}','synthetic-id',template)
        for method in operations:
            method=method.upper()
            assert c.request(method,path,json={} if method in ('POST','PATCH') else None).status_code==401,(method,path)
    assert c.get('/openapi.json').status_code==404
