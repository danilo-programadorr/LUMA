"""A2 read-only integrity audit against immutable phase preflight and original sources."""
import ast, contextlib, hashlib, io, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPORTS=ROOT/'reports'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),*args],cwd=ROOT,text=True).strip()
pre=read(REPORTS/'FASE_7F_D_A2_PREFLIGHT.json');errors=[]
# Reuse historical source, model isolation and external repository checks, handling binary QA images.
source=(ROOT/'audit_phase7f.py').read_text(encoding='utf-8')
needle="source=(ROOT/'audit_workspace.py').read_text(encoding='utf-8-sig')"
source=source.replace(needle,needle+"\nsource=source.replace(\"if not file.is_file() or '__pycache__' in file.parts: continue\",\"if not file.is_file() or '__pycache__' in file.parts or file.suffix.lower() in ('.png','.jpg','.jpeg','.webp'): continue\")")
output=io.StringIO()
with contextlib.redirect_stdout(output):
 try:exec(compile(source,str(ROOT/'audit_phase7f.py'),'exec'),{'__file__':str(ROOT/'audit_phase7f.py'),'__name__':'__audit__'})
 except SystemExit:pass
base=json.loads(output.getvalue());errors.extend(base['errors'])
if git('rev-parse','HEAD')!=pre['head']:errors.append('HEAD_CHANGED')
if git('branch','--show-current')!=pre['branch']:errors.append('BRANCH_CHANGED')
changes=read(REPORTS/'FASE_7F_D_A2_CHANGESET.json')['changes']
allowed=set(changes)|{'README.md','phase-status.json'}
changed=[]
for name,digest in pre['files'].items():
 p=ROOT/name
 if not p.exists() or sha(p)!=digest:
  changed.append(name)
  if name not in allowed:errors.append('UNDECLARED_BASELINE_CHANGE:'+name)
protected=[n for n in pre['files'] if n.startswith(('backend/migrations/v0001','backend/migrations/v0002','backend/migrations/v0003','backend/migrations/v0004','backend/migrations/v0005','backend/migrations/v0006','backend/migrations/v0007','backend/model_worker/','backend/adk_worker/','backend/requirements/lock','backend/requirements/adk'))]
protected+=['contracts/DEVICE_PROTOCOL_V1.json','contracts/RUNTIME_PROTOCOL_V1.json','backend/device_protocol.py','backend/device_service.py','backend/local_runtime_app.py','backend/runtime_processor.py','device_agent/identity.py']
for name in protected:
 if sha(ROOT/name)!=pre['files'][name]:errors.append('PROTECTED_CHANGED:'+name)
owner=(ROOT/'backend/owner_auth.py').read_bytes().replace(b'not in (5,6,7,8):',b'not in (5,6,7):')
if hashlib.sha256(owner).hexdigest()!=pre['files']['backend/owner_auth.py']:errors.append('OWNER_AUTH_BEYOND_SCHEMA_WHITELIST')
ui=read(REPORTS/'FASE_7F_B_UI_SOURCE.json')
for name,digest in ui['sha256'].items():
 if sha(Path(ui['source'])/name)!=digest:errors.append('EXTERNAL_UI_CHANGED:'+name)
ledgers={}
for label,path,key in [('original_six','runtime/research-google-acceptance-usage.json','original_six_ledger_sha256'),('final_three','runtime/research-google-final-three-usage.json','final_three_ledger_sha256')]:
 ledgers[label]=sha(ROOT/path)
 if ledgers[label]!=pre[key]:errors.append('REAL_CALL_LEDGER_CHANGED:'+label)
for name in ['runtime/private-library/example/index.db','runtime/research-agent/identity.db','runtime/postgresql-backups/example.dump']:
 if not git('check-ignore',name):errors.append('PRIVATE_RUNTIME_NOT_IGNORED:'+name)
if any(p.startswith(('runtime/','.venv/','web/.env.local')) for p in git('ls-files').splitlines()):errors.append('PRIVATE_RUNTIME_TRACKED')
# CP must not load parser/store/provider modules; exercise actual import boundary in an isolated process.
probe="import sys; import backend.private_library.service; assert not any(n in sys.modules for n in ('backend.private_library.store','backend.private_library.extract','google.genai','openai'))"
if subprocess.run([sys.executable,'-c',probe],cwd=ROOT,capture_output=True).returncode:errors.append('CONTROL_PLANE_IMPORT_BOUNDARY')
result={'date':'2026-10-30','phase':'7F-D-A2','status':'VERIFIED' if not errors else 'FAILED','errors':errors,'head':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'baseline_changed_paths':changed,'protected_files_verified':len(set(protected)),'brain_and_source_integrity':base['brain_unchanged_hash_counts'],'source_head':base['source_commit'],'finance_repository':base['finance_repository'],'ui_source_files_unchanged':len(ui['sha256']),'real_call_ledger_sha256':ledgers,'paid_calls_during_A2':0,'private_owner_import_tested':False,'commit':False,'push':False,'deploy':False,'limitations':['Read-only external repository verification, synthetic local retrieval/permission tests; real Owner document acceptance remains pending.','Encryption does not protect against compromise of the Windows account or OS. PDF worker has time/input/output limits, not a full OS memory sandbox.']}
print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
