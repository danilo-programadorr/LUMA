import secrets
from datetime import timedelta
import pytest
from backend.tests.test_codex_channel import channel,setup,task
from backend.app.errors import Fault

def test_legacy_candidate_cannot_skip_remote_task(channel):
 setup(channel);t=task(channel,approve=False)
 e=channel[0].state.execution;p=e.control.principal()
 action=t['proposal']['envelope']
 with pytest.raises(Fault,match='CODEX_REMOTE_TASK_REQUIRED'):e.candidate(p,action,secrets.token_hex(12),'legacy')

def test_phase_only_accepts_one_shot_authorization(channel):
 setup(channel);t=task(channel,mode='READ_ONLY',approve=False)
 e=channel[0].state.execution;p=e.control.principal();now=e.clock()
 spec=dict(mode='BOUNDED_WINDOW',valid_from=now.isoformat(),expires_at=(now+timedelta(seconds=60)).isoformat(),max_executions=2,confirmation='AUTHORIZE_EXACT_ACTION')
 with e.store.transaction() as r:
  with pytest.raises(Fault,match='CODEX_ONE_SHOT_REQUIRED'):e.authorize(p,t['action_request_id'],spec,secrets.token_hex(12),'fixture',confirmed=True,_repo=r)
  assert not r.rows('approvals') and not r.rows('execution_authorizations')