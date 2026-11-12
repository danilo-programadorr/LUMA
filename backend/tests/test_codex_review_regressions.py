"""Counterexamples from the independent review; no model calls."""
import sys,time,subprocess,json
from pathlib import Path
import pytest
from backend.tests.test_codex_channel import channel,setup,task,poll,payload
from backend.tests.test_codex_adapter import adapter
from backend.app.control import digest

def test_revoked_permission_prevents_process_creation(monkeypatch):
 from device_agent.codex_process import ProcessRunner
 def forbidden(*args,**kw):pytest.fail('process created after known revocation')
 monkeypatch.setattr(subprocess,'Popen',forbidden)
 r=ProcessRunner().run(['unused.exe'],'',check=lambda:False,timeout=2,max_output=1024)
 assert r['code']=='CODEX_AUTHORIZATION_REVOKED' and r['exit_code'] is None

def test_model_and_validation_share_one_absolute_deadline(tmp_path,monkeypatch):
 a,f,j,w=adapter(tmp_path);clock=[1000.]
 j['profile']['max_duration']=10;j['profile_hash']=digest(j['profile'])
 original=f.run
 def run(*args,**kw):clock[0]+=9;return original(*args,**kw)
 f.run=run
 def validation(*args):clock[0]+=2;return True
 a.validator=validation
 monkeypatch.setattr('device_agent.codex_adapter.time.monotonic',lambda:clock[0])
 r=a.execute(j,lambda:True)
 assert r.code=='CODEX_TIMEOUT' and r.status!='SUCCEEDED'

def test_cancel_acknowledgement_reaches_cancelled_not_blocked(channel):
 setup(channel);t=task(channel);j=poll(channel);app,c,d,send=channel
 r=c.post('/v1/tasks/'+t['task_id']+'/cancel',headers=__import__('backend.tests.device_support',fromlist=['HEADERS']).HEADERS,json={})
 assert r.status_code==200 and r.json()['status']=='CANCELLING'
 reply=send('codex/result',payload(j,status='CANCELLED',code='CODEX_CANCELLED',validation_pass=False))
 assert reply.status_code==200 and reply.json()['status']=='CANCELLED'
 assert c.get('/v1/tasks/'+t['task_id'],headers=__import__('backend.tests.device_support',fromlist=['HEADERS']).HEADERS).json()['status']=='CANCELLED'

def test_zero_exit_without_structured_response_is_not_success(tmp_path):
 from device_agent.codex_workspace import snapshot,fingerprint
 a,f,j,w=adapter(tmp_path)
 (w/'.git').mkdir();(w/'.luma-fixture.json').write_text('{"fixture":"LUMA_CODEX_ACCEPTANCE_V1"}')
 j['profile']['snapshot_hash']=fingerprint(snapshot(w));j['profile_hash']=digest(j['profile'])
 a.synthetic=False;a.real_enabled=True
 r=a.execute(j,lambda:True)
 assert r.status!='SUCCEEDED' and r.code=='CODEX_RESULT_INVALID'
def test_signed_process_progress_is_audited_without_new_authority(channel):
 setup(channel);t=task(channel);j=poll(channel);app,c,d,send=channel
 for phase in ('BINARY_VALIDATED','PROCESS_STARTED','PROCESS_EXITED','VERIFIED'):
  r=send('codex/progress',{'job_id':j['job_id'],'lease_id':j['lease_id'],'phase':phase,'execution_kind':'SIMULATED_TEST'})
  assert r.status_code==200 and r.json()['continue'] is True
 with app.state.control.store.read() as repo:
  names=[e['event_type'] for e in repo.rows('audit_events')]
  assert 'CODEX_SIMULATED_PROCESS_STARTED' in names
  assert len(repo.rows('execution_authorizations'))==1 and not repo.rows('execution_records')

def test_windows_revocation_before_resume_has_no_child_effect(tmp_path):
 from device_agent.codex_process import ProcessRunner
 marker=tmp_path/'not-started.txt';calls=[0]
 def check():calls[0]+=1;return calls[0]==1
 source="from pathlib import Path;Path("+repr(str(marker))+").write_text('UNEXPECTED')"
 result=ProcessRunner().run([sys.executable,'-c',source],'',check=check,timeout=5,max_output=1024)
 assert result['code']=='CODEX_AUTHORIZATION_REVOKED' and not result['process_started']
 assert not marker.exists()

def test_local_mapping_policy_tampering_invalidates_fingerprint(tmp_path):
 from backend.tests.test_codex_workspace import registry
 r,w=registry(tmp_path);entry=r.register('fixture','meu-gestor','a'*32,w,['READ_ONLY'])
 entry['allowed_execution_modes']=['READ_ONLY','WORKSPACE_WRITE'];r.save(entry)
 with pytest.raises(ValueError,match='MAPPING_CHANGED'):
  r.resolve('fixture','meu-gestor','a'*32,entry['mapping_fingerprint'],1)

@pytest.mark.parametrize('field,value,code',[('execution_mode','WORKSPACE_WRITE','MODE_DENIED'),('binary_sha256','b'*64,'BINARY_OR_MODEL_CHANGED'),('model','other-model','BINARY_OR_MODEL_CHANGED')])
def test_local_policy_enforced_independently_of_control_plane(tmp_path,field,value,code):
 from backend.tests.test_codex_workspace import registry
 r,w=registry(tmp_path);entry=r.register('fixture','meu-gestor','a'*32,w,['READ_ONLY'],binary_sha256='a'*64,model='pinned-model')
 options=dict(execution_mode='READ_ONLY',binary_sha256='a'*64,model='pinned-model');options[field]=value
 with pytest.raises(ValueError,match=code):
  r.resolve('fixture','meu-gestor','a'*32,entry['mapping_fingerprint'],1,**options)

@pytest.mark.parametrize('operation',['check','result'])
def test_extension_rejects_extraneous_root_fields(channel,operation):
 setup(channel);task(channel);j=poll(channel);app,c,d,send=channel
 body=payload(j) if operation=='result' else {'job_id':j['job_id'],'lease_id':j['lease_id']}
 body['phase']='PROCESS_STARTED'
 response=send('codex/'+operation,body)
 assert response.status_code==400 and response.json()['error']['code']=='CODEX_REQUEST_INVALID'
