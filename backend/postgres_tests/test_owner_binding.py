import time,secrets
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,insert,update
from backend.migrate import migrate
from backend.control_plane_app import ControlPlaneSettings
from backend.app.trust import Control
from backend.owner_auth import OwnerAuthenticator
from backend.owner_schema import owner_bindings,owner_bootstrap
from backend.app.database import version,engine_for
from backend.app.errors import Fault

@pytest.fixture
def auth(pg_url):
    migrate(pg_url,'postgresql',owner=True)
    c=Control(ControlPlaneSettings(database_url=pg_url,database_backend='postgresql',owner_auth_mode='IDENTITY_PLATFORM',identity_project='synthetic-project'))
    a=OwnerAuthenticator(c,c.settings)
    try:yield a
    finally:c.close()
def test_pg_owner_fresh(auth):
    with auth.control.store.read() as r:assert r.connection.execute(select(version.c.version)).scalar_one()==5
def test_pg_binding(auth):
    code=auth.issue_bootstrap();auth.bind({'sub':'synthetic-owner'},code,'test')
    with auth.control.store.read() as r:assert r.connection.execute(select(owner_bindings.c.subject_uid)).scalar_one()=='synthetic-owner'
def test_pg_unique_constraint(auth):
    code=auth.issue_bootstrap();auth.bind({'sub':'synthetic-owner'},code,'test')
    with auth.control.store.read() as r:row=dict(r.connection.execute(select(owner_bindings)).mappings().one())
    row['id']=2;row['subject_uid']='other'
    with pytest.raises(Fault):
        with auth.control.store.transaction() as r:r.connection.execute(insert(owner_bindings).values(**row))
def test_pg_rollback(auth):
    with pytest.raises(RuntimeError):
        with auth.control.store.transaction() as r:
            r.connection.execute(insert(owner_bootstrap).values(id=1,digest='x'*64,expires_at=0,attempts=0,status='ACTIVE'))
            raise RuntimeError()
    with auth.control.store.read() as r:assert r.connection.execute(select(owner_bootstrap)).first() is None
def test_pg_revocation(auth):
    code=auth.issue_bootstrap();auth.bind({'sub':'synthetic-owner'},code,'test')
    with auth.control.store.transaction() as r:r.connection.execute(update(owner_bindings).values(status='REVOKED'))
    with pytest.raises(Fault):auth.issue_bootstrap()
def test_pg_audit(auth):
    code=auth.issue_bootstrap();auth.bind({'sub':'synthetic-owner'},code,'test')
    assert auth.control.listing(auth.control.principal(),'audit_verify')['verified']
def test_pg_concurrent_bootstrap(auth):
    code=auth.issue_bootstrap()
    def run(uid):
        try:auth.bind({'sub':uid},code,'test');return True
        except Fault:return False
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(run,['a','b']))==[False,True]
def test_pg_restart_replay(auth):
    code=auth.issue_bootstrap();auth.bind({'sub':'a'},code,'test')
    other=OwnerAuthenticator(auth.control,auth.settings)
    with pytest.raises(Fault):other.bind({'sub':'a'},code,'test')
