"""Bounded execution and durable local markers; model text is never success authority."""
import hashlib,json,os,sqlite3,time
from datetime import datetime,timezone
from pathlib import Path
from backend.codex.contracts import ExecutionProfile,ExecutionResult
from backend.app.control import digest
from .codex_workspace import snapshot,verify_changes,read_context,reject_links,fingerprint
from .codex_process import ProcessRunner,redact

class Journal:
 def __init__(self,root):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);reject_links(self.root)
  self.path=self.root/'executions.db'
  with self.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS executions (job TEXT PRIMARY KEY, marker TEXT NOT NULL, payload TEXT NOT NULL, result TEXT)')
 def connect(self):return sqlite3.connect(self.path,timeout=5)
 def get(self,key):
  with self.connect() as db:row=db.execute('SELECT marker,payload,result FROM executions WHERE job=?',(key,)).fetchone()
  return dict(marker=row[0],payload=json.loads(row[1]),result=json.loads(row[2]) if row[2] else None) if row else None
 def prepare(self,key,payload):
  with self.connect() as db:
   db.execute('BEGIN IMMEDIATE')
   if db.execute('SELECT 1 FROM executions WHERE job=?',(key,)).fetchone():raise ValueError('CODEX_EXECUTION_AMBIGUOUS')
   db.execute('INSERT INTO executions VALUES (?,?,?,NULL)',(key,'PREPARED',json.dumps(payload)))
 def mark(self,key,marker,result=None):
  if marker not in ('START_INTENT','PROCESS_STARTED','PROCESS_EXITED','VERIFIED','RESULT_READY','RESULT_SENT'):raise ValueError('CODEX_MARKER_INVALID')
  with self.connect() as db:
   db.execute('UPDATE executions SET marker=?,result=COALESCE(?,result) WHERE job=?',(marker,json.dumps(result) if result is not None else None,key))
 def annotate(self,key,**fields):
  with self.connect() as db:
   row=db.execute('SELECT payload FROM executions WHERE job=?',(key,)).fetchone()
   if not row:raise ValueError('CODEX_JOURNAL_MISSING')
   payload=json.loads(row[0]);payload.update(fields);db.execute('UPDATE executions SET payload=? WHERE job=?',(json.dumps(payload),key))
 def pending(self):
  with self.connect() as db:return [(row[0],json.loads(row[1])) for row in db.execute("SELECT job,result FROM executions WHERE marker!='RESULT_SENT' AND result IS NOT NULL")]
def minimal_environment():
 names={'SYSTEMROOT','WINDIR','PATH','USERPROFILE','APPDATA','LOCALAPPDATA','TEMP','TMP','PATHEXT','COMSPEC','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','HOMEDRIVE','HOMEPATH'}
 env={k:v for k,v in os.environ.items() if k.upper() in names}
 system=Path(os.environ.get('SYSTEMROOT','C:/Windows'))
 env['PATH']=os.pathsep.join((str(system/'System32'),str(system/'System32/WindowsPowerShell/v1.0')))
 return env
class CodexExecutorAdapter:
 def __init__(self,registry,state_dir,binary,*,runner=None,validator=None,real_enabled=False):
  self.registry=registry;self.journal=Journal(state_dir);self.binary=Path(binary);self.runner=runner or ProcessRunner();self.validator=validator;self.real_enabled=real_enabled;self.synthetic=runner is not None
 def acknowledge(self,jid):self.journal.mark(jid,'RESULT_SENT')
 def execute(self,job,check,progress=None):
  profile=ExecutionProfile.model_validate(job['profile']);ph=digest(profile.model_dump())
  if ph!=job['profile_hash']:raise ValueError('CODEX_PROFILE_CHANGED')
  self.journal.prepare(job['job_id'],{'profile_hash':ph,'lease_id':job['lease_id'],'device_id':job['device_id']})
  start=time.monotonic();deadline=start+min(profile.max_duration,max(0,(datetime.fromisoformat(job['expires_at'])-datetime.now(timezone.utc)).total_seconds()))
  changes={};exit_code=None;summary='';usage={};status='FAILED';code='CODEX_NOT_STARTED';passed=False
  def bounded_check():
   if time.monotonic()>=deadline:return 'CODEX_TIMEOUT'
   permit=check()
   return 'CODEX_TIMEOUT' if time.monotonic()>=deadline else permit
  def demand():
   permit=bounded_check()
   if permit is not True:raise ValueError(permit if isinstance(permit,str) and permit.startswith('CODEX_') else 'CODEX_AUTHORIZATION_REVOKED')
  def phase(value):
   if progress:progress(value)
  def started(pid):
   self.journal.annotate(job['job_id'],pid=pid)
   self.journal.mark(job['job_id'],'PROCESS_STARTED');phase('PROCESS_STARTED')
  try:
   if not self.real_enabled and not self.synthetic:raise ValueError('CODEX_REAL_GATE_REQUIRED')
   reject_links(self.binary)
   if hashlib.sha256(self.binary.read_bytes()).hexdigest()!=profile.binary_sha256:raise ValueError('CODEX_BINARY_CHANGED')
   demand();phase('BINARY_VALIDATED')
   root=self.registry.resolve(profile.workspace_id,job['project_id'],job['device_id'],profile.mapping_fingerprint,profile.mapping_version,execution_mode=profile.execution_mode,binary_sha256=profile.binary_sha256,model=profile.model)
   if not self.synthetic:
    if not (root/'.git').is_dir() or not (root/'.luma-fixture.json').is_file():raise ValueError('CODEX_FIXTURE_REQUIRED')
    reject_links(root/'.git')
   before=snapshot(root)
   if profile.snapshot_hash!='0'*64 and fingerprint(before)!=profile.snapshot_hash:raise ValueError('CODEX_WORKSPACE_CHANGED')
   if not self.synthetic and profile.snapshot_hash=='0'*64:raise ValueError('CODEX_PREFLIGHT_REQUIRED')
   self.journal.annotate(job['job_id'],before=before)
   context=read_context(root,profile.read_paths);demand()
   if self.synthetic:
    argv=[str(self.binary),'exec'];prompt=profile.task_prompt;options={}
   else:
    from .codex_invocation import prepare_invocation
    argv,prompt,options=prepare_invocation(self.binary,self.journal.root,root,profile,context,job,deadline=deadline)
   env=minimal_environment()
   temp=self.journal.root/job['job_id']/'tmp';temp.mkdir(parents=True,exist_ok=True)
   env['TEMP']=str(temp);env['TMP']=str(temp)
   demand();self.journal.mark(job['job_id'],'START_INTENT')
   output=self.runner.run(argv,prompt,check=bounded_check,timeout=max(0,deadline-time.monotonic()),max_output=profile.max_output_bytes,cwd=root,env=env,on_started=started,**options)
   if output.get('process_started'):
    self.journal.mark(job['job_id'],'PROCESS_EXITED');phase('PROCESS_EXITED')
   exit_code=output['exit_code'];summary=redact(output.get('summary',''));usage=output.get('usage',{})
   after=snapshot(root);self.journal.annotate(job['job_id'],after=after)
   changes=verify_changes(before,after,profile.allowed_paths,profile.max_changed_files,profile.max_changed_bytes,profile.execution_mode)
   if output['code']!='CODEX_EXITED':raise ValueError(output['code'])
   if exit_code!=0:raise ValueError('CODEX_PROCESS_FAILED')
   if not self.synthetic and not output.get('final_schema_valid'):raise ValueError('CODEX_RESULT_INVALID')
   demand()
   if self.validator:passed=bool(self.validator(root,profile,bounded_check))
   else:
    from .codex_invocation import validate_fixture
    passed=validate_fixture(self.binary,root,profile,bounded_check,deadline=deadline)
   demand()
   if not passed:raise ValueError('CODEX_VALIDATION_FAILED')
   verified=snapshot(root)
   if verified!=after:raise ValueError('CODEX_VALIDATION_CHANGED_FILES')
   demand();phase('VERIFIED');code='CODEX_VERIFIED';status='SUCCEEDED'
  except (ValueError,OSError,KeyError,sqlite3.Error) as exc:
   value=str(exc);code=value if value.startswith('CODEX_') and len(value)<80 and all(c.isupper() or c=='_' for c in value) else 'CODEX_LOCAL_OPERATION_FAILED'
   if 'REVOKED' in code or 'CANCEL' in code or 'KILL' in code:status='CANCELLED'
   if 'AMBIGUOUS' in code or 'TERMINATION_UNCONFIRMED' in code:status='RECONCILIATION_REQUIRED'
  result=ExecutionResult(execution_kind='SIMULATED_TEST' if self.synthetic else 'CODEX_REAL',execution_id=job['job_id'],job_id=job['job_id'],workspace_id=profile.workspace_id,status=status,code=code,binary_sha256=profile.binary_sha256,profile_hash=ph,exit_code=exit_code,duration_ms=round((time.monotonic()-start)*1000),changed_files=changes.get('changed_files',[]),changed_bytes=changes.get('changed_bytes',0),validation_pass=passed,summary=summary,usage=usage)
  self.journal.mark(job['job_id'],'VERIFIED' if status=='SUCCEEDED' else 'RESULT_READY',result.model_dump())
  return result
