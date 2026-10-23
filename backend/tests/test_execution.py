import secrets
from datetime import timedelta
import pytest
from backend.tests.test_conversation import bundle
from backend.app.execution import ExecutionService
from backend.app.execution_contracts import CanonicalActionEnvelope
from backend.app.models import now
from backend.app.errors import Fault

@pytest.fixture
def engine(bundle):
    control=bundle[0].app.state.control
    time=[now()]
    engine=ExecutionService(control,sandbox=True,clock=lambda:time[0])
    with control.store.transaction() as repo:
        repo.add('tools','sandbox-test',dict(tool_id='sandbox-test',enabled=True,capabilities=['record','review','sensitive','critical']))
    return engine,control.principal(),time

def candidate(engine,operation='record',**changes):
    e,p,t=engine
    body=CanonicalActionEnvelope(project_id='meu-gestor',tool_id='sandbox-test',operation=operation,**changes).model_dump()
    return e.candidate(p,body,secrets.token_hex(12),'test-correlation')

def authorization(engine,operation='record',**changes):
    e,p,t=engine;a=candidate(engine,operation)
    spec=dict(mode='ONE_SHOT',valid_from=t[0].isoformat(),expires_at=(t[0]+timedelta(minutes=5)).isoformat(),max_executions=1,confirmation='AUTHORIZE_EXACT_ACTION',late_execution_policy='RUN_LATE_WITHIN_GRACE',grace_seconds=120)
    spec.update(changes)
    return e.authorize(p,a['action_id'],spec,secrets.token_hex(12),'correlation',confirmed=True)

def make_job(engine,auth,**changes):
    e,p,t=engine;spec=dict(authorization_id=auth['authorization_id'],action=auth['action_template']);spec.update(changes)
    return e.job(p,spec,secrets.token_hex(12),'correlation')

def test_one_shot_quota_and_ledger(engine):
    e,p,t=engine;a=authorization(engine);j=make_job(engine,a);e.tick();claim=e.claim('worker');assert claim['job_id']==j['job_id'];assert e.claim('second') is None
    assert e.execute(j['job_id'],'worker')['status']=='SUCCEEDED'
    with e.store.read() as r:assert len(r.rows('sandbox_effects'))==len(r.rows('execution_records'))==1
    with pytest.raises(Fault,match='EXHAUSTED'):make_job(engine,a)

@pytest.mark.parametrize('change',[{'project_id':'other'},{'tool_id':'google_calendar'},{'operation':'review'},{'destination':'other'},{'parameters':{'recipient':'B'}},{'execution_target':'LOCAL_DEVICE','target_device_id':'other'}])
def test_action_drift(engine,change):
    a=authorization(engine)
    with pytest.raises(Fault):make_job(engine,a,action={**a['action_template'],**change})

@pytest.mark.parametrize('block',['revoke','kill','tool','grant','expiry','policy','project'])
def test_revalidate_after_lease(engine,block):
    e,p,t=engine;a=authorization(engine);j=make_job(engine,a);e.tick();e.claim('worker')
    if block=='revoke':e.revoke(p,a['authorization_id'],secrets.token_hex(12),'c')
    elif block=='expiry':t[0]+=timedelta(minutes=6)
    else:
        with e.store.transaction() as r:
            if block=='kill':row=r.get('system_state','global');row['state']='LOCKED';r.put('system_state','global',row)
            elif block=='tool':row=r.get('tools','sandbox-test');row['enabled']=False;r.put('tools','sandbox-test',row)
            elif block=='project':row=r.get('projects','meu-gestor');row['enabled']=False;r.put('projects','meu-gestor',row)
            elif block=='policy':row=r.get('execution_authorizations',a['authorization_id']);row['policy_version']='changed';r.put('execution_authorizations',a['authorization_id'],row)
            else:
                for g in r.rows('grants'):
                    if g['principal_id']=='luma-executor':g['status']='REVOKED';r.put('grants',g['grant_id'],g)
    try:assert e.execute(j['job_id'],'worker')['status']=='BLOCKED'
    except Fault as exc:assert exc.code=='LEASE_INVALID'
    with e.store.read() as r:assert not r.rows('sandbox_effects')

def test_crash_reconciliation_without_duplicate(engine):
    e,p,t=engine;a=authorization(engine);j=make_job(engine,a);e.tick();e.claim('worker')
    def crash():raise RuntimeError('synthetic-crash')
    with pytest.raises(RuntimeError):e.execute(j['job_id'],'worker',after_effect=crash)
    t[0]+=timedelta(seconds=31)
    assert e.reconcile(j['job_id'])['status']=='SUCCEEDED'
    with e.store.read() as r:assert len(r.rows('sandbox_effects'))==1 and r.rows('execution_reconciliations')[0]['outcome']=='CONFIRMED'

@pytest.mark.parametrize('operation,mode,allowed',[('sensitive','RECURRING_POLICY',False),('sensitive','ONE_SHOT',True),('critical','ONE_SHOT',False),('review','BOUNDED_WINDOW',False)])
def test_risk(engine,operation,mode,allowed):
    if allowed:assert authorization(engine,operation,mode=mode)['risk_level']=='HIGH'
    else:
        with pytest.raises(Fault):authorization(engine,operation,mode=mode,interval_seconds=60 if mode=='RECURRING_POLICY' else None)

def test_recurring_limit(engine):
    e,p,t=engine;a=authorization(engine,mode='RECURRING_POLICY',interval_seconds=60,max_executions=2)
    j=make_job(engine,a,trigger_type='RECURRING',scheduled_for=t[0].isoformat());e.tick();e.claim('one');e.execute(j['job_id'],'one')
    t[0]+=timedelta(seconds=60);e.tick();claim=e.claim('two');e.execute(claim['job_id'],'two')
    with e.store.read() as r:assert len(r.rows('jobs'))==2 and len(r.rows('sandbox_effects'))==2

def test_device_wait_spoof_revoke(engine):
    e,p,t=engine;d=e.devices.register(p,dict(device_id='pc-test',name='Test',device_type='WINDOWS'),'register-test','c')
    a=candidate(engine,execution_target='LOCAL_DEVICE',target_device_id='pc-test')
    spec=dict(mode='ONE_SHOT',valid_from=t[0].isoformat(),expires_at=(t[0]+timedelta(minutes=5)).isoformat(),max_executions=1,confirmation='AUTHORIZE_EXACT_ACTION',late_execution_policy='RUN_LATE_WITHIN_GRACE',grace_seconds=120)
    auth=e.authorize(p,a['action_id'],spec,'authorize-test','c');j=make_job(engine,auth);e.tick()
    with e.store.read() as r:assert r.get('jobs',j['job_id'])['status']=='WAITING_FOR_DEVICE'
    hb=dict(device_id='pc-test',executor_version='0.5.0rc1',status='ONLINE',capabilities=['sandbox-test'],current_job_count=0)
    with pytest.raises(Fault,match='DEVICE_UNAUTHORIZED'):e.devices.heartbeat(hb,'invalid-credential')
    e.devices.heartbeat(hb,d['device_credential']);e.tick();assert e.claim('cloud') is None
    job=e.claim('device','pc-test',d['device_credential']);assert job['job_id']==j['job_id']
    e.devices.revoke(p,'pc-test');assert e.execute(j['job_id'],'device')['result_code']=='BLOCKED_DEVICE_REVOKED'

def test_runtime_cannot_authorize(engine):
    e,p,t=engine;runtime=e.control.principal('luma-runtime');a=candidate(engine)
    with pytest.raises(Fault,match='ADMIN_CAPABILITY_DENIED'):
        e.authorize(runtime,a['action_id'],dict(valid_from=t[0].isoformat(),expires_at=(t[0]+timedelta(minutes=1)).isoformat(),max_executions=1,confirmation='AUTHORIZE_EXACT_ACTION'),'runtime-key','c')
