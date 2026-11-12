import time,uuid
from pathlib import Path
from datetime import timedelta
import pytest
from sqlalchemy import update,select
from backend.owner_schema import owner_bindings
from backend.owner_auth import AuthenticatedOwnerPrincipal
from backend.device_protocol import *
from backend.tests.device_support import *
from device_agent.identity import Identity
from device_agent.client import endpoint

@pytest.fixture
def channel(monkeypatch):
    monkeypatch.setenv('LUMA_ENV','test')
    path=Path('runtime')/('device-test-'+uuid.uuid4().hex+'.db')
    app,client,clock=build('sqlite:///'+path.resolve().as_posix())
    yield app,client,clock
    client.__exit__(None,None,None);path.unlink(missing_ok=True)

def heartbeat(c,key,row,n=1,**changes):
    return c.post('/v1/device-runtime/heartbeat',json=signed(key,row['device_id'],n,{**HB,**changes}))
def owner():return AuthenticatedOwnerPrincipal('local-owner','google.com','owner-fixture',int(time.time()),'synthetic')
def test_enrollment_requires_owner_confirmation(channel):
    app,c,t=channel;k,d,_,_=enroll(c,False)
    assert heartbeat(c,k,d).status_code==403
    assert c.post('/v1/devices/'+d['device_id']+'/approve',json={'fingerprint':d['key_fingerprint']}).status_code==401
    assert c.post('/v1/devices/'+d['device_id']+'/approve',headers=HEADERS,json={'fingerprint':d['key_fingerprint']}).status_code==200
    assert heartbeat(c,k,d).status_code==200
    row=c.get('/v1/devices',headers=HEADERS).json()[0];assert row['online'] and row['key_fingerprint']==fingerprint(public_text(k))
    assert 'public_key' not in row and 'nonces' not in row

def test_used_challenge(channel):
    _,c,_=channel;_,_,_,b=enroll(c)
    assert c.post('/v1/devices/enrollment/complete',json=b.model_dump()).json()['error']['code']=='DEVICE_ENROLLMENT_USED'
def test_expired_challenge(channel):
    _,c,t=channel;ch=c.post('/v1/devices/enrollment/start',headers=HEADERS,json={'display_name':'PC'}).json();t[0]+=timedelta(seconds=301)
    assert c.post('/v1/devices/enrollment/complete',json=enrollment(ch,Ed25519PrivateKey.generate()).model_dump()).json()['error']['code']=='DEVICE_ENROLLMENT_EXPIRED'
@pytest.mark.parametrize('kind',['signature','wrong_key','public_only','payload','path','clock','sequence','nonce','unknown','protocol','extra','capability'])
def test_signed_request_attacks(channel,kind):
    _,c,t=channel;k,d,_,_=enroll(c);assert heartbeat(c,k,d).status_code==200
    b=signed(k,d['device_id'],2,HB)
    if kind=='signature':b['signature']='A'*88
    elif kind in ('wrong_key','public_only'):b=signed(Ed25519PrivateKey.generate(),d['device_id'],2,HB)
    elif kind=='payload':b['payload']['runtime_version']='9.9'
    elif kind=='path':b=signed(k,d['device_id'],2,HB,operation='poll')
    elif kind=='clock':b=signed(k,d['device_id'],2,HB,timestamp=int(t[0].timestamp())-181)
    elif kind=='sequence':b=signed(k,d['device_id'],1,HB)
    elif kind=='nonce':
        first=signed(k,d['device_id'],2,HB);assert c.post('/v1/device-runtime/heartbeat',json=first).status_code==200
        b=signed(k,d['device_id'],3,HB,nonce=first['nonce'])
    elif kind=='unknown':b=signed(k,uuid.uuid4().hex,2,HB)
    elif kind=='protocol':b['device_protocol_version']='2'
    elif kind=='extra':b['approved']=True
    elif kind=='capability':b=signed(k,d['device_id'],2,{**HB,'capabilities':['CODEX_EXECUTOR']})
    assert c.post('/v1/device-runtime/heartbeat',json=b).status_code in (400,401,403,409)

def test_replay_and_skew_tolerance(channel):
    _,c,t=channel;k,d,_,_=enroll(c);b=signed(k,d['device_id'],1,HB,timestamp=int(t[0].timestamp())-150)
    assert c.post('/v1/device-runtime/heartbeat',json=b).status_code==200
    assert c.post('/v1/device-runtime/heartbeat',json=b).json()['error']['code']=='DEVICE_REPLAY_DETECTED'
def test_offline_restart_sequence_and_identity(channel):
    _,c,t=channel;k,d,_,_=enroll(c);heartbeat(c,k,d);t[0]+=timedelta(seconds=46)
    assert c.get('/v1/devices',headers=HEADERS).json()[0]['status']=='OFFLINE'
    b=signed(k,d['device_id'],2,HB,timestamp=int(t[0].timestamp()))
    assert c.post('/v1/device-runtime/heartbeat',json=b).status_code==200
    assert c.get('/v1/devices',headers=HEADERS).json()[0]['online']
@pytest.mark.parametrize('operation',['heartbeat','poll','result'])
def test_revoked_channel(channel,operation):
    _,c,_=channel;k,d,_,_=enroll(c);c.post('/v1/devices/'+d['device_id']+'/revoke',headers=HEADERS,json={})
    payload=HB if operation=='heartbeat' else {} if operation=='poll' else {'job_id':uuid.uuid4().hex,'lease_id':uuid.uuid4().hex}
    b=signed(k,d['device_id'],1,payload,operation=operation)
    assert c.post('/v1/device-runtime/'+operation,json=b).status_code==403

def test_binding_transfer_denied(channel):
    app,c,_=channel;k,d,_,_=enroll(c)
    with app.state.control.store.transaction() as r:r.connection.execute(update(owner_bindings).values(subject_uid='other-fixture'))
    assert heartbeat(c,k,d).json()['error']['code']=='DEVICE_OWNER_MISMATCH'
def test_owner_device_route_separation(channel):
    _,c,_=channel;k,d,_,_=enroll(c)
    assert c.post('/v1/device-runtime/heartbeat',headers=HEADERS,json=signed(k,d['device_id'],1,HB)).status_code==401
    assert c.get('/v1/devices',headers={'Authorization':'Bearer other-fixture'}).status_code==403
    assert c.get('/v1/devices').status_code==401
    assert c.post('/v1/device/heartbeat',headers={'Authorization':'Bearer '+'x'*48,'X-Luma-Device-ID':d['device_id']},json={}).status_code==401
    assert c.post('/v1/execution-devices',headers={**HEADERS,'Idempotency-Key':'synthetic-register'},json={'device_id':'legacy','name':'No','device_type':'WINDOWS'}).status_code==403

def job_channel(channel):
    app,c,t=channel;k,d,_,_=enroll(c);heartbeat(c,k,d)
    job=app.state.device_service.test_job(owner(),d['device_id'])
    return app,c,t,k,d,job
def poll(c,k,d,n,t=None):return c.post('/v1/device-runtime/poll',json=signed(k,d['device_id'],n,{},operation='poll',timestamp=t))
def test_safe_job_result_and_idempotency(channel):
    app,c,t,k,d,j=job_channel(channel);leased=poll(c,k,d,2).json()['job'];assert leased['job_id']==j['job_id']
    assert poll(c,k,d,3).json()['job'] is None
    payload={'job_id':j['job_id'],'lease_id':leased['lease_id']}
    for n in (4,5):assert c.post('/v1/device-runtime/result',json=signed(k,d['device_id'],n,payload,operation='result')).json()['status']=='SUCCEEDED'
    with app.state.control.store.read() as r:assert len(r.rows('sandbox_effects'))==len(r.rows('execution_records'))==1

def test_job_no_fallback_other_device(channel):
    app,c,t,k,d,j=job_channel(channel);k2,d2,_,_=enroll(c);heartbeat(c,k2,d2)
    assert poll(c,k2,d2,2).json()['job'] is None
    t[0]+=timedelta(seconds=46)
    assert poll(c,k,d,2,int(t[0].timestamp())).json()['status']=='WAITING_FOR_DEVICE'

def test_expired_lease_reconciles_without_effect(channel):
    app,c,t,k,d,j=job_channel(channel);first=poll(c,k,d,2).json()['job'];t[0]+=timedelta(seconds=31)
    second=poll(c,k,d,3,int(t[0].timestamp())).json()['job'];assert first['job_id']==second['job_id'] and first['lease_id']!=second['lease_id']
    payload={'job_id':j['job_id'],'lease_id':first['lease_id']}
    assert c.post('/v1/device-runtime/result',json=signed(k,d['device_id'],4,payload,operation='result')).status_code==409
    payload['lease_id']=second['lease_id']
    assert c.post('/v1/device-runtime/result',json=signed(k,d['device_id'],5,payload,operation='result')).status_code==200
@pytest.mark.parametrize('block',['expiry','revocation','cancel','kill','capability'])
def test_offline_job_blockers(channel,block):
    app,c,t,k,d,j=job_channel(channel);e=app.state.execution;p=e.control.principal()
    if block=='expiry':t[0]+=timedelta(seconds=301)
    elif block=='revocation':e.revoke(p,j['authorization_id'],uuid.uuid4().hex,'test')
    elif block=='cancel':e.cancel(p,j['job_id'],uuid.uuid4().hex,'test')
    else:
        with e.store.transaction() as r:
            if block=='kill':row=r.get('system_state','global');row['state']='LOCKED';r.put('system_state','global',row)
            else:row=r.get('execution_devices',d['device_id']);row['capabilities']=[];r.put('execution_devices',d['device_id'],row)
    c.post('/v1/device-runtime/heartbeat',json=signed(k,d['device_id'],2,HB,timestamp=int(t[0].timestamp())))
    response=poll(c,k,d,3,int(t[0].timestamp()));assert response.status_code==403 or response.json()['job'] is None
    with e.store.read() as r:assert not r.rows('sandbox_effects')

def test_stale_owner_approval(channel):
    app,c,t=channel;_,d,_,_=enroll(c,False)
    stale=AuthenticatedOwnerPrincipal('local-owner','google.com','owner-fixture',int(time.time())-301,'test')
    with pytest.raises(Fault,match='RECENT_AUTH'):app.state.device_service.change(stale,d['device_id'],'approve',d['key_fingerprint'])
def test_rate_limit_durable(channel):
    app,c,_=channel;k,d,_,_=enroll(c)
    with app.state.control.store.transaction() as r:r.add('device_rate_limits','device-'+d['device_id'],{'window':app.state.device_service.seconds(),'count':120})
    assert heartbeat(c,k,d).status_code==429

def test_windows_key_storage_and_restart():
    directory=Path('runtime')/('identity-test-'+uuid.uuid4().hex);path=directory/'identity.db'
    a=Identity(path,create=True);fp=a.fingerprint();assert a.reserve()==1
    b=Identity(path);assert b.fingerprint()==fp and b.reserve()==2
    key=b.key();raw=key.private_bytes_raw();assert raw not in path.read_bytes()
    b.bind('a'*32,'http://127.0.0.1:8770')
    assert Identity(path).binding()[0]=='a'*32
    with pytest.raises(RuntimeError):b.bind('b'*32,'http://127.0.0.1:8770')
@pytest.mark.parametrize('url',['http://remote.example','https://user:password@example.com','https://example.com/path','https://example.com?token=no'])
def test_remote_http_and_credential_urls_denied(url):
    with pytest.raises(ValueError):endpoint(url)

@pytest.mark.parametrize('attack',['wrong_code','wrong_signature','approval_fingerprint','expired_approval','owner_revoked'])
def test_enrollment_security_additional(channel,attack):
    app,c,t=channel
    if attack in ('wrong_code','wrong_signature'):
        ch=c.post('/v1/devices/enrollment/start',headers=HEADERS,json={'display_name':'PC'}).json();k=Ed25519PrivateKey.generate();b=enrollment(ch,k).model_dump()
        b['code' if attack=='wrong_code' else 'signature']='x'*43 if attack=='wrong_code' else 'A'*88
        assert c.post('/v1/devices/enrollment/complete',json=b).status_code==401
    else:
        k,d,_,_=enroll(c,False)
        if attack=='expired_approval':t[0]+=timedelta(seconds=301)
        elif attack=='owner_revoked':
            with app.state.control.store.transaction() as r:r.connection.execute(update(owner_bindings).values(status='REVOKED'))
        response=c.post('/v1/devices/'+d['device_id']+'/approve',headers=HEADERS,json={'fingerprint':'0'*64 if attack=='approval_fingerprint' else d['key_fingerprint']})
        assert response.status_code in (403,409)

def test_device_approval_does_not_create_execution_authority(channel):
    app,c,t=channel;enroll(c)
    with app.state.control.store.read() as r:
        for name in ('actions','approvals','execution_authorizations','jobs'):assert r.rows(name)==[]

def test_result_blocked_after_authorization_revocation(channel):
    app,c,t,k,d,j=job_channel(channel);leased=poll(c,k,d,2).json()['job']
    app.state.execution.revoke(app.state.control.principal(),j['authorization_id'],uuid.uuid4().hex,'test')
    response=c.post('/v1/device-runtime/result',json=signed(k,d['device_id'],3,{'job_id':j['job_id'],'lease_id':leased['lease_id']},operation='result'))
    assert response.status_code==403
    with app.state.control.store.read() as r:assert not r.rows('sandbox_effects')

def test_malformed_and_bounded_requests(channel):
    _,c,_=channel
    assert c.post('/v1/device-runtime/heartbeat',content='{').status_code==400
    assert c.post('/v1/device-runtime/heartbeat',content='x'*16385).status_code==413

def test_client_agent_roundtrip_and_restart(channel):
    from device_agent.client import DeviceClient
    app,c,t=channel
    path=Path('runtime')/('agent-test-'+uuid.uuid4().hex)/'identity.db'
    identity=Identity(path,create=True)
    class Transport:
        def post(self,url,**kwargs):return c.post(url,json=kwargs['json'])
    client=DeviceClient(identity,'http://127.0.0.1',Transport())
    ch=c.post('/v1/devices/enrollment/start',headers=HEADERS,json={'display_name':'PC'}).json()
    d=client.enroll(ch['challenge_id'],ch['code'])
    assert c.post('/v1/devices/'+d['device_id']+'/approve',headers=HEADERS,json={'fingerprint':d['key_fingerprint']}).status_code==200
    assert client.once()['heartbeat']=='ACCEPTED'
    app.state.device_service.test_job(owner(),d['device_id'])
    restarted=DeviceClient(Identity(path),'http://127.0.0.1',Transport())
    assert restarted.once()['synthetic_job_completed']
    assert Identity(path).fingerprint()==d['key_fingerprint']

def test_local_sequence_atomic_under_concurrency():
    from concurrent.futures import ThreadPoolExecutor
    path=Path('runtime')/('sequence-test-'+uuid.uuid4().hex)/'identity.db'
    identity=Identity(path,create=True)
    with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(lambda _:Identity(path).reserve(),range(12)))
    assert sorted(values)==list(range(1,13))


def test_agent_import_has_no_control_plane_or_database():
    import subprocess,sys
    code="import device_agent.client,sys; assert not any(x in sys.modules for x in ('sqlalchemy','psycopg','backend.app.database','backend.app.trust','backend.control_plane_app')); print('ISOLATED')"
    run=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert run.returncode==0,run.stderr

def test_job_offline_state_is_persisted(channel):
    app,c,t=channel;k,d,_,_=enroll(c)
    j=app.state.device_service.test_job(owner(),d['device_id'])
    assert j['status']=='WAITING_FOR_DEVICE'
