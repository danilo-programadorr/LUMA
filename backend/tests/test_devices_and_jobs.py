import secrets
from datetime import timedelta
import pytest,httpx
from backend.tests.test_execution import engine,authorization,make_job,candidate
from backend.tests.test_conversation import bundle
from backend.app.errors import Fault
from backend.local_executor import endpoint,poll_once

def test_device_http_identity_and_no_owner_privilege(bundle):
    api,cfg,*_=bundle
    d=api.post('/v1/execution-devices',json={'device_id':'pc-test','name':'Synthetic','device_type':'WINDOWS'},headers={'Idempotency-Key':'register-device'}).json()
    credential=d['device_credential'];headers={'Authorization':'Bearer '+credential,'X-Luma-Device-ID':'pc-test'}
    body=dict(device_id='pc-test',executor_version='0.5.0rc1',status='ONLINE',capabilities=[],current_job_count=0)
    assert api.post('/v1/device/heartbeat',json=body,headers=headers).status_code==200
    assert api.get('/v1/admin/state',headers=headers).status_code==401
    assert api.post('/v1/device/poll',json={},headers=headers).json() is None
    assert api.post('/v1/device/heartbeat',json={**body,'device_id':'other'},headers=headers).status_code==401
    assert api.post('/v1/device/heartbeat',json={**body,'capabilities':['sandbox-test']},headers=headers).status_code==403
    assert api.post('/v1/device/heartbeat',json=body).status_code==401
    assert credential not in api.get('/v1/execution-devices').text
    assert credential not in api.get('/v1/admin/audit').text
    api.post('/v1/execution-devices/pc-test/revoke',json={},headers={'Idempotency-Key':'revoke-device'})
    assert api.post('/v1/device/poll',json={},headers=headers).status_code==403

@pytest.mark.parametrize('url',['http://example.com','https://u:p@example.com','https://example.com/?token=x','ftp://example.com'])
def test_outbound_endpoint_restrictions(url):
    with pytest.raises(ValueError):endpoint(url)

def test_outbound_client_only_heartbeat_and_poll():
    paths=[]
    def handle(request):
        paths.append(request.url.path)
        assert request.headers['authorization']=='Bearer synthetic-device-only'
        return httpx.Response(200,content=b'{}' if request.url.path.endswith('heartbeat') else b'null',headers={'content-type':'application/json'})
    with httpx.Client(base_url='https://example.com',headers={'Authorization':'Bearer synthetic-device-only'},transport=httpx.MockTransport(handle)) as client:
        assert poll_once(client,'pc-test')['job_received'] is False
    assert paths==['/v1/device/heartbeat','/v1/device/poll']

@pytest.mark.parametrize('policy,result',[('SKIP','EXPIRED'),('REQUIRE_REAUTHORIZATION','BLOCKED'),('RUN_LATE_WITHIN_GRACE','READY')])
def test_late_policy(engine,policy,result):
    e,p,t=engine;a=authorization(engine,late_execution_policy=policy,grace_seconds=60 if policy=='RUN_LATE_WITHIN_GRACE' else 0);j=make_job(engine,a)
    t[0]+=timedelta(seconds=10);e.tick()
    with e.store.read() as r:assert r.get('jobs',j['job_id'])['status']==result

def test_lease_recovery_and_cancellation(engine):
    e,p,t=engine;a=authorization(engine);j=make_job(engine,a);e.tick();e.claim('crashed');t[0]+=timedelta(seconds=31)
    assert e.claim('replacement')['lease_owner']=='replacement'
    e.cancel(p,j['job_id'],'cancel-job-key','c')
    with pytest.raises(Fault,match='LEASE_INVALID'):e.execute(j['job_id'],'replacement')

def test_condition_trigger(engine):
    e,p,t=engine;a=authorization(engine);j=make_job(engine,a,trigger_type='CONDITION',scheduled_for=t[0].isoformat(),condition_id='internal-test')
    e.tick();assert e.claim('worker') is None
    with pytest.raises(Fault):e.condition(j['job_id'],'other')
    e.condition(j['job_id'],'internal-test');e.tick();assert e.claim('worker')['job_id']==j['job_id']

def test_job_duplicate_idempotency(engine):
    e,p,t=engine;a=authorization(engine);spec=dict(authorization_id=a['authorization_id'],action=a['action_template'])
    first=e.job(p,spec,'job-idempotency','c');second=e.job(p,spec,'job-idempotency','c');assert first==second
    with pytest.raises(Fault,match='IDEMPOTENCY_CONFLICT'):e.job(p,{**spec,'trigger_type':'SCHEDULED_AT','scheduled_for':t[0].isoformat()},'job-idempotency','c')

@pytest.mark.parametrize('key',['approved','authorized','owner','execute_now','grant','risk_level'])
def test_parameter_authority_denied(engine,key):
    with pytest.raises(Fault):candidate(engine,parameters={key:True})

@pytest.mark.parametrize('mode',['BOUNDED_WINDOW','RECURRING_POLICY'])
def test_revocation_between_occurrences(engine,mode):
    e,p,t=engine;a=authorization(engine,mode=mode,max_executions=2,interval_seconds=60 if mode=='RECURRING_POLICY' else None)
    j=make_job(engine,a,trigger_type='RECURRING' if mode=='RECURRING_POLICY' else 'IMMEDIATE',scheduled_for=t[0].isoformat());e.tick();e.claim('w');e.execute(j['job_id'],'w')
    e.revoke(p,a['authorization_id'],'revoke-between','c');t[0]+=timedelta(seconds=60);e.tick();assert e.claim('w2') is None
    with e.store.read() as r:assert len(r.rows('sandbox_effects'))==1
