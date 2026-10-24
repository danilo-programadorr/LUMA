from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from backend.control_plane_tasks import RuntimeTaskService
from backend.app.trust import Control
from backend.app.execution import ExecutionService
from backend.app.trust_data import verify
from backend.tests.test_remote_boundary import claimed,result,send
@pytest.fixture
def pg_boundary(engine):
    e,p,clock=engine;c=e.control
    sid=c.mutate(p,'session',{'project_id':'meu-gestor'},'pg-boundary-session','pg-boundary')['session_id']
    e.devices.register(p,dict(device_id='pc-boundary',name='Synthetic PG device',device_type='WINDOWS'),'pg-boundary-register','pg-boundary')
    return SimpleNamespace(state=SimpleNamespace(runtime_tasks=RuntimeTaskService(c,e))),c,e,p,c.principal('luma-runtime'),sid
def test_postgres_boundary_acceptance(pg_boundary):
    t=claimed(pg_boundary)
    assert send(pg_boundary,result(t))['task_status']=='WAITING_AUTHORIZATION'
    with pg_boundary[1].store.read() as r:assert verify(r) and not r.rows('approvals') and not r.rows('jobs')
def test_postgres_concurrent_duplicate_result(pg_boundary):
    t=claimed(pg_boundary);res=result(t);barrier=Barrier(2)
    def upload(_):barrier.wait(timeout=10);return send(pg_boundary,res)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(upload,range(2)))
    assert responses[0]==responses[1]
    with pg_boundary[1].store.read() as r:assert len(r.rows('actions'))==1 and verify(r)
def test_postgres_result_retry_after_service_restart(pg_boundary):
    t=claimed(pg_boundary);res=result(t);first=send(pg_boundary,res)
    c=Control(pg_boundary[1].settings);e=ExecutionService(c)
    try:
        assert RuntimeTaskService(c,e).accept(c.principal('luma-runtime'),res.device_id,res.model_dump_json().encode())==first
        with c.store.read() as r:assert len(r.rows('actions'))==1 and verify(r)
    finally:c.close()
def test_postgres_cancellation_persists(pg_boundary):
    t=claimed(pg_boundary);pg_boundary[0].state.runtime_tasks.cancel(pg_boundary[3],t.task_id)
    from backend.app.errors import Fault
    with pytest.raises(Fault):send(pg_boundary,result(t))
    with pg_boundary[1].store.read() as r:assert r.get('agent_tasks',t.task_id)['status']=='CANCELLED' and not r.rows('actions') and verify(r)
