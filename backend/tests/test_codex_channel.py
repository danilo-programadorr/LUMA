"""Signed-channel integration. Model and Codex subprocess are not used here."""
import secrets
from datetime import timedelta
import pytest
from backend.tests.device_support import Verifier,HEADERS,enroll,signed,HB

@pytest.fixture
def channel(tmp_path,monkeypatch):
 from fastapi.testclient import TestClient
 from backend.migrate import migrate
 from backend.control_plane_app import ControlPlaneSettings,create_control_plane
 monkeypatch.setenv('LUMA_ENV','test');url='sqlite:///'+(tmp_path/'codex.db').as_posix()
 migrate(url,codex=True)
 app=create_control_plane(ControlPlaneSettings(database_url=url,owner_auth_mode='IDENTITY_PLATFORM',identity_project='synthetic',devices_enabled=True,device_test_tool=True,codex_enabled=True),_test_verifier=Verifier())
 with TestClient(app,base_url='http://127.0.0.1') as c:
  code=app.state.owner_auth.issue_bootstrap();assert c.post('/v1/owner/bootstrap',headers=HEADERS,json={'code':code}).status_code==200
  key,d,_,_=enroll(c);seq=[0]
  def send(op,payload):
   seq[0]+=1
   return c.post('/v1/device-runtime/'+op,json=signed(key,d['device_id'],seq[0],payload,op))
  yield app,c,d,send

def setup(channel):
 app,c,d,send=channel
 grant=c.post('/v1/codex/devices/'+d['device_id']+'/grant',headers=HEADERS,json={'enabled':True,'confirmation':'CODEX_EXECUTION_ONE_SHOT_ONLY'});assert grant.status_code==200,grant.text
 manifest=dict(binary_sha256='b'*64,model='fixture-model',workspace_id='fixture',project_id='meu-gestor',target_device_id=d['device_id'],display_name='Synthetic fixture',mapping_version=1,mapping_fingerprint='a'*64,allowed_execution_modes=['READ_ONLY','WORKSPACE_WRITE'],enabled=True)
 r=c.post('/v1/codex/workspaces',headers=HEADERS,json={'manifest':manifest,'confirmation':'APPROVE_CODEX_WORKSPACE'});assert r.status_code==200,r.text
 assert send('heartbeat',HB).status_code==200
 assert send('codex/heartbeat',{'binary_sha256':'b'*64,'workspace_ids':['fixture']}).status_code==200
 return manifest

def task(channel,mode='WORKSPACE_WRITE',approve=True,**changes):
 app,c,d,send=channel
 profile=dict(workspace_id='fixture',mapping_version=1,mapping_fingerprint='a'*64,task_prompt='Corrigir função no fixture sintético.',execution_mode=mode,allowed_paths=['src/calc.py'] if mode=='WORKSPACE_WRITE' else [],binary_sha256='b'*64,model='fixture-model')
 profile.update(changes)
 data=dict(project_id='meu-gestor',task_type='ACTION_ORIENTED',input='Corrigir função no fixture sintético.',executor='CODEX',codex_profile=profile,target_device_id=d['device_id'],idempotency_key=secrets.token_hex(12))
 r=c.post('/v1/tasks',headers=HEADERS,json=data);assert r.status_code==200,r.text
 t=r.json()
 if approve:
  r=c.post('/v1/tasks/'+t['task_id']+'/decision',headers=HEADERS,json={'decision':'APPROVE','proposal_hash':t['proposal_hash']});assert r.status_code==200,r.text;t=r.json()
 return t

def poll(channel):
 r=channel[3]('codex/poll',{});assert r.status_code==200,r.text
 return r.json()['job']

def payload(job,**kw):
 result=dict(execution_id=job['job_id'],job_id=job['job_id'],workspace_id='fixture',status='SUCCEEDED',code='CODEX_VERIFIED',binary_sha256='b'*64,profile_hash=job['profile_hash'],exit_code=0,duration_ms=12,changed_files=['src/calc.py'],changed_bytes=12,validation_pass=True,summary='Fixture verificado')
 result.update(kw);return dict(job_id=job['job_id'],lease_id=job['lease_id'],result=result)

def test_codex_default_disabled(channel):
 app,c,d,send=channel
 assert c.get('/v1/codex/workspaces',headers=HEADERS).json()==[]
 assert send('codex/poll',{}).status_code==403

def test_no_invocation_before_owner_approval(channel):
 setup(channel);task(channel,approve=False);assert poll(channel) is None

def test_approved_signed_job_completes_once(channel):
 setup(channel);t=task(channel);j=poll(channel);assert j['job_id']==t['job_id']
 r=channel[3]('codex/result',payload(j));assert r.status_code==200,r.text
 assert r.json()['status']=='SUCCEEDED'
 assert channel[3]('codex/result',payload(j)).json()['duplicate'] is True
 with channel[0].state.control.store.read() as repo:
  assert len(repo.rows('execution_records'))==1
  a=repo.get('execution_authorizations',repo.get('jobs',j['job_id'])['authorization_id'])
  assert a['executions_used']==1 and a['executions_reserved']==0
 assert channel[1].get('/v1/tasks/'+t['task_id'],headers=HEADERS).json()['status']=='COMPLETED'

@pytest.mark.parametrize('change',[{'mapping_fingerprint':'0'*64},{'mapping_version':2},{'workspace_id':'unknown'},{'execution_mode':'READ_ONLY','allowed_paths':['src/calc.py']}])
def test_workspace_or_profile_drift_denied(channel,change):
 setup(channel)
 with pytest.raises(AssertionError):task(channel,**change)

def test_revoke_before_claim_prevents_job(channel):
 setup(channel);t=task(channel);assert channel[1].post('/v1/tasks/'+t['task_id']+'/revoke',headers=HEADERS,json={}).status_code==200
 assert poll(channel) is None

@pytest.mark.parametrize('mutation',['revoke','cancel','kill'])
def test_during_run_denied_and_late_success_never_accepted(channel,mutation):
 setup(channel);t=task(channel);j=poll(channel);app,c,d,send=channel
 if mutation=='kill':
  with app.state.control.store.transaction() as repo:
   row=repo.get('system_state','global');row['state']='STOPPED';repo.put('system_state','global',row)
 else:assert c.post('/v1/tasks/'+t['task_id']+'/'+mutation,headers=HEADERS,json={}).status_code==200
 check=send('codex/check',{'job_id':j['job_id'],'lease_id':j['lease_id']})
 assert check.status_code==200 and not check.json()['continue']
 r=send('codex/result',payload(j))
 assert r.status_code==200 and r.json()['status']!='SUCCEEDED'
 with app.state.control.store.read() as repo:assert not repo.rows('execution_records')

def test_ambiguous_restart_never_releases_for_retry(channel):
 setup(channel);task(channel);j=poll(channel)
 assert poll(channel) is None
 assert channel[3]('codex/result',payload(j,status='RECONCILIATION_REQUIRED',code='CODEX_EXECUTION_AMBIGUOUS',validation_pass=False)).status_code==200
 assert poll(channel) is None

def test_wrong_result_hash_denied(channel):
 setup(channel);task(channel);j=poll(channel)
 r=channel[3]('codex/result',payload(j,profile_hash='0'*64));assert r.status_code==403

def test_read_only_with_changed_files_rejected(channel):
 setup(channel);task(channel,mode='READ_ONLY');j=poll(channel)
 r=channel[3]('codex/result',payload(j));assert r.status_code==403

def test_legacy_poll_does_not_block_codex_job(channel):
 setup(channel);t=task(channel)
 assert channel[3]('poll',{}).json()['job'] is None
 assert poll(channel)['job_id']==t['job_id']

def test_grant_is_not_an_execution_authorization(channel):
 setup(channel)
 with channel[0].state.control.store.read() as r:assert not r.rows('execution_authorizations') and not r.rows('jobs')

def test_profile_paths_never_include_canonical_root_in_control_plane(channel):
 setup(channel)
 public=channel[1].get('/v1/codex/workspaces',headers=HEADERS).json()
 assert 'canonical_root' not in str(public)