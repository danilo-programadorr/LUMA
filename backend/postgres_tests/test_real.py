from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
import secrets
import pytest
from sqlalchemy import select,inspect,text
from backend.app.database import Store,engine_for,version,TABLES,validate_database
from backend.app.errors import Fault
from backend.app.trust_data import verify
from backend.app.execution_contracts import CanonicalActionEnvelope
from backend.migrate import migrate
from backend.tests.test_execution import (
    candidate,authorization,make_job,
    test_one_shot_quota_and_ledger,
    test_action_drift,
    test_revalidate_after_lease,
    test_crash_reconciliation_without_duplicate,
    test_risk,
    test_recurring_limit,
    test_runtime_cannot_authorize,
)

def test_fresh_migrations_and_restart(pg_url):
    assert migrate(pg_url,'postgresql') is True
    assert migrate(pg_url,'postgresql') is False
    store=Store(pg_url,'postgresql')
    with store.read() as r:
        assert r.connection.dialect.name=='postgresql'
        assert r.connection.execute(text('SHOW server_version')).scalar().startswith('18.')
        assert r.connection.execute(select(version.c.version)).scalar_one()==4
    store.close()
    again=Store(pg_url,'postgresql')
    with again.read() as r: assert r.get('audit_chain','head') is not None
    again.close()

@pytest.mark.parametrize('revision',[1,2,3])
def test_upgrade_supported_revisions(pg_url,revision):
    from backend.migrations.v0001_initial import upgrade as first
    from backend.migrations.v0002_trust_boundary import upgrade as second
    from backend.migrations.v0003_conversation import upgrade as third
    db=engine_for(pg_url,'postgresql')
    try:
        with db.begin() as c:
            for upgrade in (first,second,third)[:revision]: upgrade(c)
        assert migrate(pg_url,'postgresql')
        with db.connect() as c: assert c.execute(select(version.c.version)).scalar_one()==4
    finally: db.dispose()

def concurrent(fn):
    gate=Barrier(2)
    def run(i):
        gate.wait(timeout=10)
        return fn(i)
    with ThreadPoolExecutor(max_workers=2) as pool: return list(pool.map(run,range(2)))

def test_two_workers_one_claim(engine):
    e,p,t=engine
    job=make_job(engine,authorization(engine));e.tick()
    results=concurrent(lambda i:e.claim('worker-'+str(i)))
    assert sum(x is not None for x in results)==1
    claimed=next(x for x in results if x)
    assert claimed['job_id']==job['job_id']
    assert e.execute(job['job_id'],claimed['lease_owner'])['status']=='SUCCEEDED'
    with e.store.read() as r:
        assert len(r.rows('execution_records'))==len(r.rows('sandbox_effects'))==1
        assert verify(r)

def test_concurrent_idempotency(engine):
    e,p,t=engine
    body=CanonicalActionEnvelope(project_id='meu-gestor',tool_id='sandbox-test',operation='record').model_dump()
    results=concurrent(lambda i:e.candidate(p,body,'same-pg-request','concurrent'))
    assert results[0]==results[1]
    with e.store.read() as r:
        assert len(r.rows('actions'))==1
        assert len(r.rows('idempotency'))==1
        assert verify(r)

def test_concurrent_updates_serialized(engine):
    e,p,t=engine
    def update(i):
        with e.store.transaction() as r:
            row=r.get('system_state','global')
            row['counter']=row.get('counter',0)+1
            r.put('system_state','global',row)
    concurrent(update)
    with e.store.read() as r: assert r.get('system_state','global')['counter']==2

def test_authorization_failure_atomic(engine,monkeypatch):
    e,p,t=engine
    action=candidate(engine)
    original=e.event
    def fail(r,kind,row,code='OK'):
        original(r,kind,row,code)
        if kind=='AUTHORIZATION_CREATED': raise RuntimeError('injected')
    monkeypatch.setattr(e,'event',fail)
    with pytest.raises(RuntimeError,match='injected'):
        e.authorize(p,action['action_id'],dict(mode='ONE_SHOT',valid_from=t[0].isoformat(),
            expires_at=(t[0]+timedelta(minutes=5)).isoformat(),max_executions=1,
            confirmation='AUTHORIZE_EXACT_ACTION'),'atomic-key','atomic',confirmed=True)
    with e.store.read() as r:
        assert not r.rows('approvals') and not r.rows('execution_authorizations') and not r.rows('jobs')
        assert r.get('actions',action['action_id'])['status']!='AUTHORIZED'
        assert verify(r)

def test_job_failure_atomic(engine,monkeypatch):
    e,p,t=engine;a=authorization(engine)
    original=e.event
    def fail(r,kind,row,code='OK'):
        original(r,kind,row,code)
        if kind=='JOB_CREATED': raise RuntimeError('injected')
    monkeypatch.setattr(e,'event',fail)
    with pytest.raises(RuntimeError,match='injected'):make_job(engine,a)
    with e.store.read() as r:
        assert not r.rows('jobs')
        assert len(r.rows('approvals'))==len(r.rows('execution_authorizations'))==1
        assert verify(r)

def test_unique_and_rollback(engine):
    e,p,t=engine
    with pytest.raises(Fault,match='DATABASE_UNAVAILABLE'):
        with e.store.transaction() as r:
            r.add('system_state','transient',dict(value=1))
            r.add('system_state','global',dict(value=2))
    with e.store.read() as r: assert r.get('system_state','transient') is None

def test_lease_expiry_reclaims_without_effect(engine):
    e,p,t=engine;a=authorization(engine);j=make_job(engine,a);e.tick()
    assert e.claim('crashed')['job_id']==j['job_id']
    t[0]+=timedelta(seconds=31)
    assert e.claim('replacement')['job_id']==j['job_id']
    with pytest.raises(Fault,match='LEASE_INVALID'):e.execute(j['job_id'],'crashed')
    assert e.execute(j['job_id'],'replacement')['status']=='SUCCEEDED'
    with e.store.read() as r:assert len(r.rows('sandbox_effects'))==1 and verify(r)

def test_database_fk_support(pg_url):
    db=engine_for(pg_url,'postgresql')
    try:
        with db.begin() as c:
            c.exec_driver_sql('CREATE TABLE parent_test (id INTEGER PRIMARY KEY)')
            c.exec_driver_sql('CREATE TABLE child_test (id INTEGER REFERENCES parent_test(id))')
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with db.begin() as c:c.exec_driver_sql('INSERT INTO child_test VALUES (1)')
    finally:db.dispose()

def test_json_bool_timestamp_roundtrip(engine):
    e,p,t=engine
    data={'enabled':True,'disabled':False,'empty':None,'text':'ação revogação','at':t[0].isoformat(),'nested':{'values':[1,False]}}
    with e.store.transaction() as r:r.add('system_state','roundtrip',data)
    with e.store.read() as r:assert r.get('system_state','roundtrip')==data

@pytest.mark.parametrize('change',[{'host':'localhost'},{'host':'0.0.0.0'},{'username':'postgres'},{'database':'production'},{'query':{'options':'bad'}}])
def test_reject_unapproved_database(pg_url,change):
    with pytest.raises(ValueError,match='INVALID_POSTGRES_TEST_CONFIGURATION'):validate_database(pg_url.set(**change),'postgresql')

def test_sqlite_default_rejects_postgres(pg_url):
    with pytest.raises(ValueError,match='INVALID_DATABASE_LOCATION'):validate_database(pg_url)

def test_migration_failure_rolls_back_ddl(pg_url,monkeypatch):
    import backend.migrate as runner
    original=runner.conversation_upgrade
    def fail(c):
        original(c)
        raise RuntimeError('migration-injected')
    monkeypatch.setattr(runner,'conversation_upgrade',fail)
    with pytest.raises(RuntimeError,match='migration-injected'):runner.migrate(pg_url,'postgresql')
    db=engine_for(pg_url,'postgresql')
    try:
        with db.connect() as c: assert inspect(c).get_table_names()==[]
    finally:db.dispose()

def test_concurrent_audit_chain(engine):
    e,p,t=engine
    concurrent(lambda i:candidate(engine))
    with e.store.read() as r:
        assert len(r.rows('actions'))==2
        assert verify(r)

def test_upgrade_preserves_existing_json(pg_url):
    from backend.migrations.v0001_initial import upgrade as initial
    from backend.app.database import Repository
    db=engine_for(pg_url,'postgresql')
    try:
        with db.begin() as c:
            initial(c)
            Repository(c).add('learning','historical',{'content':'synthetic historical record','enabled':False})
        migrate(pg_url,'postgresql')
        with db.connect() as c:
            assert Repository(c).get('learning','historical')=={'content':'synthetic historical record','enabled':False}
    finally:db.dispose()
