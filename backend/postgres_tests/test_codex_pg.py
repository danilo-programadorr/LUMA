"""PostgreSQL real; verifier/model/result fixtures remain simulated."""
import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from fastapi.testclient import TestClient
from backend.tests.device_support import Verifier,HEADERS,enroll,signed
from backend.tests import test_codex_channel as cases
from backend.migrate import migrate
from backend.control_plane_app import ControlPlaneSettings,create_control_plane
from backend.app.trust_data import verify

@pytest.fixture
def channel(pg_url,monkeypatch):
 monkeypatch.setenv('LUMA_ENV','test');migrate(pg_url,'postgresql',codex=True)
 settings=ControlPlaneSettings(database_url=pg_url,database_backend='postgresql',owner_auth_mode='IDENTITY_PLATFORM',identity_project='synthetic',devices_enabled=True,device_test_tool=True,codex_enabled=True)
 app=create_control_plane(settings,_test_verifier=Verifier())
 with TestClient(app,base_url='http://127.0.0.1') as c:
  assert c.post('/v1/owner/bootstrap',headers=HEADERS,json={'code':app.state.owner_auth.issue_bootstrap()}).status_code==200
  key,d,_,_=enroll(c);seq=[0]
  def send(op,payload):
   seq[0]+=1;return c.post('/v1/device-runtime/'+op,json=signed(key,d['device_id'],seq[0],payload,op))
  yield app,c,d,send

def test_codex_pg_one_shot_and_replay(channel):
 cases.test_approved_signed_job_completes_once(channel)
 with channel[0].state.control.store.read() as r:assert verify(r)

def test_codex_pg_concurrent_owner_decision_one_job(channel):
 cases.setup(channel);t=cases.task(channel,approve=False);gate=Barrier(2)
 def approve(_):
  gate.wait()
  return channel[1].post('/v1/tasks/'+t['task_id']+'/decision',headers=HEADERS,json={'decision':'APPROVE','proposal_hash':t['proposal_hash']})
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(approve,range(2)))
 assert all(r.status_code==200 for r in results)
 assert len({r.json()['job_id'] for r in results})==1
 with channel[0].state.control.store.read() as r:assert len(r.rows('execution_authorizations'))==len(r.rows('jobs'))==1

def test_codex_pg_revoke_while_running_late_result(channel):
 cases.test_during_run_denied_and_late_success_never_accepted(channel,'revoke')

def test_codex_pg_cancel_while_running_late_result(channel):
 cases.test_during_run_denied_and_late_success_never_accepted(channel,'cancel')

def test_codex_pg_restart_preserves_completed_job(channel):
 cases.setup(channel);t=cases.task(channel);j=cases.poll(channel)
 assert channel[3]('codex/result',cases.payload(j)).status_code==200
 app=create_control_plane(channel[0].state.control.settings,_test_verifier=Verifier())
 with TestClient(app,base_url='http://127.0.0.1') as other:
  response=other.get('/v1/tasks/'+t['task_id'],headers=HEADERS)
  assert response.status_code==200 and response.json()['status']=='COMPLETED'
 with channel[0].state.control.store.read() as r:assert len(r.rows('execution_records'))==1 and verify(r)

def test_codex_pg_schema9_idempotent_preserves_previous_migrations(channel):
 app=channel[0]
 assert migrate(app.state.control.settings.database_url,'postgresql',codex=True) is False
 assert migrate(app.state.control.settings.database_url,'postgresql',library=True) is False
 from sqlalchemy import select
 from backend.app.database import version
 with app.state.control.store.read() as r:assert r.connection.execute(select(version.c.version)).scalar_one()==9
def test_codex_pg_numeric_cli_usage_and_idempotent_delivery(channel):
 from backend.tests.test_codex_usage_boundary import test_numeric_cli_usage_is_persisted_and_replayed_once
 test_numeric_cli_usage_is_persisted_and_replayed_once(channel)
