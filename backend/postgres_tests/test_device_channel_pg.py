from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
import time,uuid
import pytest
from backend.tests.device_support import *
from backend.tests.test_device_channel import owner

@pytest.fixture
def channel_pg(pg_url,monkeypatch):
    monkeypatch.setenv('LUMA_ENV','test');app,c,t=build(pg_url,'postgresql')
    yield app,c,t
    c.__exit__(None,None,None)

def ready(channel_pg):
    app,c,t=channel_pg;k,d,_,_=enroll(c)
    assert c.post('/v1/device-runtime/heartbeat',json=signed(k,d['device_id'],1,HB)).status_code==200
    j=app.state.device_service.test_job(owner(),d['device_id']);return app,c,t,k,d,j

def test_postgres_two_pollers_one_claim(channel_pg):
    app,c,t,k,d,j=ready(channel_pg);barrier=Barrier(2)
    bodies=[signed(k,d['device_id'],n,{},operation='poll') for n in (2,3)]
    def poll(body):barrier.wait();return c.post('/v1/device-runtime/poll',json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(poll,bodies))
    assert all(r.status_code in (200,409) for r in responses)
    assert sum(bool(r.json().get('job')) for r in responses)==1
    with app.state.control.store.read() as r:assert r.get('jobs',j['job_id'])['status']=='LEASED'
    assert app.state.control.listing(app.state.control.principal(),'audit_verify')['verified']

def test_postgres_replay_is_durable_across_service_instances(channel_pg):
    from backend.device_service import DeviceService
    app,c,t,k,d,j=ready(channel_pg)
    body=signed(k,d['device_id'],2,{},operation='poll')
    assert c.post('/v1/device-runtime/poll',json=body).status_code==200
    service=DeviceService(app.state.control,app.state.execution)
    with pytest.raises(Fault,match='DEVICE_REPLAY'):service.handle('/v1/device-runtime/poll',body)

@pytest.mark.parametrize('condition',['expired','revoked','cancelled','kill'])
def test_postgres_offline_blockers(channel_pg,condition):
    app,c,t,k,d,j=ready(channel_pg);e=app.state.execution
    if condition=='expired':t[0]+=timedelta(seconds=301)
    elif condition=='revoked':e.revoke(e.control.principal(),j['authorization_id'],uuid.uuid4().hex,'pg')
    elif condition=='cancelled':e.cancel(e.control.principal(),j['job_id'],uuid.uuid4().hex,'pg')
    else:
        with e.store.transaction() as r:row=r.get('system_state','global');row['state']='LOCKED';r.put('system_state','global',row)
    c.post('/v1/device-runtime/heartbeat',json=signed(k,d['device_id'],2,HB,timestamp=int(t[0].timestamp())))
    response=c.post('/v1/device-runtime/poll',json=signed(k,d['device_id'],3,{},operation='poll',timestamp=int(t[0].timestamp())))
    assert response.status_code==403 or response.json()['job'] is None
    with e.store.read() as r:assert not r.rows('sandbox_effects')

def test_postgres_result_and_lease_reconciliation(channel_pg):
    app,c,t,k,d,j=ready(channel_pg)
    a=c.post('/v1/device-runtime/poll',json=signed(k,d['device_id'],2,{},operation='poll')).json()['job'];t[0]+=timedelta(seconds=31)
    b=c.post('/v1/device-runtime/poll',json=signed(k,d['device_id'],3,{},operation='poll')).json()['job']
    assert a['job_id']==b['job_id'] and a['lease_id']!=b['lease_id']
    payload={'job_id':b['job_id'],'lease_id':b['lease_id']}
    for n in (4,5):assert c.post('/v1/device-runtime/result',json=signed(k,d['device_id'],n,payload,operation='result')).status_code==200
    with app.state.control.store.read() as r:assert len(r.rows('sandbox_effects'))==len(r.rows('execution_records'))==1
    assert app.state.control.listing(app.state.control.principal(),'audit_verify')['verified']
