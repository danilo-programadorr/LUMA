import pytest
from pydantic import ValidationError
from backend.tests.test_codex_workspace import profile
from backend.codex.contracts import ExecutionProfile

@pytest.mark.parametrize('read_paths,denied_paths',[
 (['denied/secret.txt'],['denied']),(['.codex/auth.json'],[]),(['.git/config'],[]),(['.env'],[]),
 (['private/file.txt'],['private/file.txt'])])
def test_denied_file_never_becomes_provider_context(read_paths,denied_paths):
 with pytest.raises(ValidationError):profile(read_paths=read_paths,denied_paths=denied_paths)

def test_executor_task_fields_cannot_be_ignored():
 from backend.remote_tasks import TaskCreate
 with pytest.raises(ValidationError):
  TaskCreate(project_id='meu-gestor',task_type='INFORMATIONAL',executor='CODEX',input='x',idempotency_key='abcdefgh')

def test_timeout_kills_even_when_permission_check_blocks(tmp_path):
 import sys,time
 from device_agent.codex_process import ProcessRunner
 start=time.monotonic()
 armed=[False]
 def slow():
  if armed[0]:time.sleep(2)
  return True
 def begun(pid):armed[0]=True;slow()
 marker=tmp_path/'last_tick.txt'
 source="import time,pathlib; p=pathlib.Path("+repr(str(marker))+"); t=time.monotonic();\nwhile True:p.write_text(str(time.monotonic()-t));time.sleep(.05)"
 result=ProcessRunner().run([sys.executable,'-c',source],'',check=slow,timeout=1,max_output=1024,on_started=begun)
 assert result['code']=='CODEX_TIMEOUT' and result['tree_closed']
 assert time.monotonic()-start<4
 assert marker.exists() and float(marker.read_text())<1.4

def test_journal_captures_before_and_after_for_reconciliation(tmp_path):
 from backend.tests.test_codex_adapter import adapter
 a,f,j,w=adapter(tmp_path);a.execute(j,lambda:True)
 record=a.journal.get(j['job_id'])['payload']
 assert record['before']['src/calc.py']['sha256']!=record['after']['src/calc.py']['sha256']