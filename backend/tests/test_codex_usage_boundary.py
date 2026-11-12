"""Regression from real CLI delivery: numeric token counts are metadata, not credentials."""
import pytest
from backend.tests.test_codex_channel import channel,setup,task,poll,payload

USAGE={'input_tokens':12093,'cached_input_tokens':0,'output_tokens':119,'reasoning_output_tokens':37}

def test_numeric_cli_usage_is_persisted_and_replayed_once(channel):
 setup(channel);task(channel);j=poll(channel);app,c,d,send=channel
 data=payload(j,usage=USAGE)
 response=send('codex/result',data)
 assert response.status_code==200,response.text
 assert response.json()['status']=='SUCCEEDED'
 assert send('codex/result',data).json()['duplicate'] is True
 with app.state.control.store.read() as r:
  assert r.get('jobs',j['job_id'])['codex_result']['usage']==USAGE
  assert len(r.rows('execution_records'))==1

@pytest.mark.parametrize('usage',[{'input_tokens':'opaque-value'},{'input_tokens':True},{'owner_token':123}])
def test_usage_cannot_smuggle_strings_booleans_or_unknown_fields(channel,usage):
 setup(channel);task(channel);j=poll(channel)
 response=channel[3]('codex/result',payload(j,usage=usage))
 assert response.status_code==400
 with channel[0].state.control.store.read() as r:assert not r.get('jobs',j['job_id']).get('codex_result')

def test_usage_exception_does_not_skip_sensitive_summary_screening(channel):
 setup(channel);task(channel);j=poll(channel)
 response=channel[3]('codex/result',payload(j,usage=USAGE,summary='AIza'+('z'*36)))
 assert response.status_code==400 and response.json()['error']['code']=='SENSITIVE_PAYLOAD'
 with channel[0].state.control.store.read() as r:assert not r.get('jobs',j['job_id']).get('codex_result')

def test_numeric_usage_after_lease_expiry_records_blocked_not_success(channel):
 setup(channel);task(channel);j=poll(channel);app,c,d,send=channel
 with app.state.control.store.transaction() as r:
  job=r.get('jobs',j['job_id']);job['lease_until']='2000-01-01T00:00:00+00:00';r.put('jobs',j['job_id'],job)
 response=send('codex/result',payload(j,usage=USAGE))
 assert response.status_code==200 and response.json()['status']=='BLOCKED'
 with app.state.control.store.read() as r:
  job=r.get('jobs',j['job_id']);assert job['result_code']=='CODEX_EXECUTION_AMBIGUOUS'
  assert job['codex_result']['usage']==USAGE and not r.rows('execution_records')
  auth=r.get('execution_authorizations',job['authorization_id'])
  assert auth['executions_used']==1 and auth['executions_reserved']==0
