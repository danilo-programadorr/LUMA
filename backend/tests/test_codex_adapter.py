"""Adapter lifecycle with a controlled runner; no model invocation."""
import json,hashlib,time,threading,sys,os
from pathlib import Path
import pytest
from backend.codex.contracts import ExecutionProfile
from backend.app.control import digest
from device_agent.codex_workspace import WorkspaceRegistry

def context(tmp_path,mode='WORKSPACE_WRITE'):
 root=tmp_path/'managed';w=root/'fixture';(w/'src').mkdir(parents=True);(w/'tests').mkdir()
 (w/'src/calc.py').write_text('value=1\n',encoding='utf8')
 (w/'tests/test_calc.py').write_text('protected',encoding='utf8')
 r=WorkspaceRegistry(tmp_path/'mapping',root)
 binary=tmp_path/'codex.exe';binary.write_bytes(b'FAKE_BINARY_NOT_REAL_CODEX')
 m=r.register('fixture','meu-gestor','a'*32,w,['READ_ONLY','WORKSPACE_WRITE'],binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),model='test-model')
 profile=ExecutionProfile(workspace_id='fixture',mapping_version=1,mapping_fingerprint=m['mapping_fingerprint'],task_prompt='Corrigir função sintética',execution_mode=mode,read_paths=['src/calc.py'],allowed_paths=['src/calc.py'] if mode=='WORKSPACE_WRITE' else [],binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),model='test-model')
 job=dict(job_id='b'*32,lease_id='c'*32,device_id='a'*32,project_id='meu-gestor',expires_at='2099-01-01T00:00:00+00:00',profile=profile.model_dump(),profile_hash=digest(profile.model_dump()))
 return r,w,binary,job

class FakeRunner:
 def __init__(self,work,change=True,validation=True,code='CODEX_EXITED'):self.w=work;self.calls=0;self.change=change;self.validation=validation;self.code=code
 def run(self,argv,stdin,**kw):
  self.calls+=1
  if self.change:(self.w/'src/calc.py').write_text('value=2\n')
  return dict(exit_code=0,code=self.code,summary='Sintético, sem modelo',usage={},validation_pass=self.validation)

def adapter(tmp_path,mode='WORKSPACE_WRITE',**kw):
 from device_agent.codex_adapter import CodexExecutorAdapter
 r,w,b,j=context(tmp_path,mode);fake=FakeRunner(w,**kw)
 a=CodexExecutorAdapter(r,tmp_path/'journal',b,runner=fake,validator=lambda *args:True,real_enabled=False)
 return a,fake,j,w

def test_fake_adapter_verified_effect_and_marker(tmp_path):
 a,f,j,w=adapter(tmp_path);result=a.execute(j,lambda:True)
 assert result.status=='SUCCEEDED' and result.changed_files==['src/calc.py'] and f.calls==1
 assert a.journal.get(j['job_id'])['marker']=='VERIFIED'
 a.acknowledge(j['job_id']);assert a.journal.get(j['job_id'])['marker']=='RESULT_SENT'

def test_same_job_never_invoked_twice(tmp_path):
 a,f,j,w=adapter(tmp_path);a.execute(j,lambda:True)
 with pytest.raises(ValueError,match='AMBIGUOUS'):a.execute(j,lambda:True)
 assert f.calls==1

def test_authorization_denied_before_launch(tmp_path):
 a,f,j,w=adapter(tmp_path)
 result=a.execute(j,lambda:False)
 assert result.status!='SUCCEEDED' and f.calls==0

def test_pin_changed_before_launch(tmp_path):
 a,f,j,w=adapter(tmp_path);a.binary.write_bytes(b'changed')
 result=a.execute(j,lambda:True)
 assert result.code=='CODEX_BINARY_CHANGED' and f.calls==0

def test_hash_drift_before_launch(tmp_path):
 a,f,j,w=adapter(tmp_path);j['profile']['task_prompt']='different'
 with pytest.raises(ValueError,match='PROFILE_CHANGED'):a.execute(j,lambda:True)
 assert f.calls==0

def test_read_only_write_rejected(tmp_path):
 a,f,j,w=adapter(tmp_path,mode='READ_ONLY');result=a.execute(j,lambda:True)
 assert result.code=='CODEX_SCOPE_EXCEEDED' and result.status!='SUCCEEDED'

def test_exit_zero_does_not_replace_validation(tmp_path):
 a,f,j,w=adapter(tmp_path);a.validator=lambda *args:False
 result=a.execute(j,lambda:True)
 assert result.status=='FAILED' and result.code=='CODEX_VALIDATION_FAILED'

def test_revoke_after_effect_never_success(tmp_path):
 a,f,j,w=adapter(tmp_path)
 result=a.execute(j,lambda:f.calls==0)
 assert result.status!='SUCCEEDED'

def test_ambiguous_marker_survives_restart(tmp_path):
 from device_agent.codex_adapter import Journal
 journal=Journal(tmp_path/'journal');journal.prepare('x',{'profile_hash':'a'})
 journal.mark('x','PROCESS_STARTED')
 other=Journal(tmp_path/'journal')
 with pytest.raises(ValueError,match='AMBIGUOUS'):other.prepare('x',{'profile_hash':'a'})

def test_no_real_runner_without_explicit_gate(tmp_path):
 from device_agent.codex_adapter import CodexExecutorAdapter
 r,w,b,j=context(tmp_path)
 a=CodexExecutorAdapter(r,tmp_path/'journal',b,real_enabled=False)
 assert a.execute(j,lambda:True).code=='CODEX_REAL_GATE_REQUIRED'

def test_structured_event_filter_discards_reasoning_and_secrets():
 from device_agent.codex_process import EventFilter
 f=EventFilter(2048)
 f.feed('stdout',b'{"type":"item.completed","item":{"type":"reasoning","text":"DO_NOT_RETAIN"}}\n')
 f.feed('stdout',b'{"type":"item.completed","item":{"type":"agent_message","text":"{\\"summary\\":\\"Fixture verificado\\"}"}}\n')
 f.feed('stdout',b'{"type":"turn.completed","usage":{"input_tokens":10,"secret":"DO_NOT_RETAIN"}}\n')
 assert f.summary=='Fixture verificado' and f.usage=={'input_tokens':10}
 assert 'DO_NOT_RETAIN' not in str(vars(f))

def test_output_is_bounded():
 from device_agent.codex_process import EventFilter
 f=EventFilter(1024)
 with pytest.raises(ValueError,match='OUTPUT'):f.feed('stderr',b'x'*2048)

def test_process_tree_cancellation_real_subprocess_no_model(tmp_path):
 from device_agent.codex_process import ProcessRunner
 child_pid=tmp_path/'child.pid'
 source="import subprocess,sys,time,pathlib;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(90)']);pathlib.Path("+repr(str(child_pid))+").write_text(str(p.pid));print('RUNNING',flush=True);time.sleep(90)"
 start=time.monotonic()
 result=ProcessRunner().run([sys.executable,'-c',source],'',check=lambda:time.monotonic()-start<1.5,timeout=10,max_output=2048)
 assert result['code']=='CODEX_AUTHORIZATION_REVOKED'
 assert time.monotonic()-start<8
 assert result['tree_closed'] is True
 assert child_pid.is_file()
 if os.name=='nt':
  import ctypes
  from ctypes import wintypes
  k=ctypes.WinDLL('kernel32',use_last_error=True)
  k.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD);k.OpenProcess.restype=wintypes.HANDLE
  k.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD);k.WaitForSingleObject.restype=wintypes.DWORD
  k.CloseHandle.argtypes=(wintypes.HANDLE,);k.CloseHandle.restype=wintypes.BOOL
  handle=k.OpenProcess(0x100000,False,int(child_pid.read_text()))
  if handle:
   try:assert k.WaitForSingleObject(handle,2000)==0,'descendant_still_running'
   finally:k.CloseHandle(handle)
  else:assert ctypes.get_last_error()==87,'descendant_state_not_confirmed'
