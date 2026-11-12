from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import secrets
import pytest
from backend.tests.test_remote_tasks import create,service,approve,online
from backend.app.errors import Fault
from backend.app.trust_data import verify

def test_pg_remote_creation_idempotent(engine):
 e,p,_=engine;s=service(engine);b={'project_id':'meu-gestor','task_type':'ANALYTICAL','input':'Synthetic analysis','idempotency_key':secrets.token_hex(12)};gate=Barrier(2)
 def run(_):gate.wait();return s.create(p,b,'pg')['task_id']
 with ThreadPoolExecutor(max_workers=2) as pool:assert len(set(pool.map(run,(0,1))))==1
 with e.store.read() as r:assert len(r.rows('agent_tasks'))==1;verify(r)
def test_pg_remote_approve_reject_race(engine):
 t=create(engine);gate=Barrier(2)
 def run(value):
  gate.wait()
  try:return service(engine).decide(engine[1],t['task_id'],{'decision':value,'proposal_hash':t['proposal_hash']},'pg',True)['decision']
  except Fault:return 'DENIED'
 with ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(run,('APPROVE','REJECT')))
 assert out.count('DENIED')==1
 with engine[0].store.read() as r:assert len(r.rows('approvals'))==1;verify(r)
def test_pg_remote_double_approve_one_job(engine):
 t=create(engine);gate=Barrier(2)
 def run(_):gate.wait();return approve(engine,t)['job_id']
 with ThreadPoolExecutor(max_workers=2) as pool:assert len(set(pool.map(run,(0,1))))==1
 with engine[0].store.read() as r:assert len(r.rows('jobs'))==len(r.rows('execution_authorizations'))==1
def test_pg_remote_revoke_claim_race(engine):
 t=create(engine);a=approve(engine,t);e,p,_=engine;online(engine);e.tick();gate=Barrier(2)
 def revoke():gate.wait();return service(engine).revoke(p,t['task_id'],'pg')
 def claim():gate.wait();return e.claim('pg-worker','remote-test',e._remote_test_credential)
 with ThreadPoolExecutor(max_workers=2) as pool:
  f=pool.submit(revoke);g=pool.submit(claim);f.result();job=g.result()
 if job:assert e.execute(job['job_id'],'pg-worker')['status']=='BLOCKED'
 with e.store.read() as r:assert not r.rows('sandbox_effects');verify(r)
def test_pg_remote_restart_and_effect_once(engine):
 t=create(engine);a=approve(engine,t);e,p,_=engine;assert service(engine).get(p,t['task_id'])['job_id']==a['job_id'];online(engine);e.tick();job=e.claim('pg-worker','remote-test',e._remote_test_credential);e.execute(job['job_id'],'pg-worker')
 assert service(engine).get(p,t['task_id'])['status']=='COMPLETED'
 with e.store.read() as r:assert len(r.rows('sandbox_effects'))==1;verify(r)
def test_pg_remote_analysis_reuses_runtime(engine):
 from backend.tests.test_remote_tasks import test_remote_analytical_task_uses_existing_runtime as scenario
 scenario(engine)
def test_pg_remote_new_store_preserves_task_and_decision(engine):
 from backend.app.trust import Control
 from backend.app.execution import ExecutionService
 t=create(engine);a=approve(engine,t);e,p,clock=engine;fresh=Control(e.control.settings)
 try:
  successor=ExecutionService(fresh,sandbox=True,clock=lambda:clock[0]);from backend.remote_tasks import RemoteTasks
  current=RemoteTasks(successor).get(fresh.principal(),t['task_id']);assert current['job_id']==a['job_id'] and current['decision']=='APPROVE'
  with fresh.store.read() as r:verify(r)
 finally:fresh.close()

def test_pg_remote_displayed_expiration_matches_execution_window(engine):
 from backend.tests.test_remote_tasks import test_remote_offline_return_can_execute_until_displayed_expiration as scenario
 scenario(engine)
