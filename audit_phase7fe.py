"""Read-only phase-E audit; exact compatibility exceptions, no global changes."""
import hashlib,json,subprocess,sys,datetime,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
pre=read(ROOT/'reports/FASE_7F_E_PREFLIGHT.json')
allowed={'backend/migrate.py','backend/app/database.py','backend/app/execution.py','backend/app/devices.py','backend/control_plane_app.py','backend/device_service.py','backend/remote_tasks.py','backend/remote_tasks_api.py','device_agent/client.py','web/src/pages/RemoteTasksPanel.tsx','web/src/auth/client.ts','backend/owner_auth.py','backend/private_library/service.py'}
baseline=subprocess.run([sys.executable,'-B','audit_phase7fdb.py'],cwd=ROOT,capture_output=True,timeout=300)
base=json.loads(baseline.stdout);errors=[];exceptions=[]
for err in base['errors']:
 parts=err.split(':',1)
 if len(parts)==2 and parts[0] in ('UNDECLARED_CHANGE','UNDECLARED_BASELINE_CHANGE','PROTECTED_CHANGED') and parts[1] in allowed:
  exceptions.append({'finding':err,'reason':'Explicit local phase-E implementation change; historical audit predates this phase'})
 elif err=='OWNER_AUTH_BEYOND_SCHEMA_WHITELIST':
  old=read(ROOT/'reports/FASE_7F_D_A2_PREFLIGHT.json')['files']['backend/owner_auth.py']
  normalized=(ROOT/'backend/owner_auth.py').read_bytes().replace(b'not in (5,6,7,8,9):',b'not in (5,6,7):')
  if hashlib.sha256(normalized).hexdigest()!=old:errors.append(err)
  else:exceptions.append({'finding':err,'reason':'Exact schema-version whitelist addition only; normalized hash matches original'})
 else:errors.append(err)
changed=[];immutable=[]
for name,expected in pre['hashes'].items():
 p=ROOT/name
 if not p.exists() or sha(p)!=expected:
  changed.append(name)
  if name not in allowed:errors.append('UNAUTHORIZED_PHASE_E_CHANGE:'+name)
 else:immutable.append(name)
for name in ('backend/migrations/v0009_codex.py','contracts/CODEX_EXECUTION_PROFILE_V1.json','contracts/CODEX_DEVICE_EXTENSION_V1.json'):
 if not (ROOT/name).is_file():errors.append('MISSING_PHASE_E_ARTIFACT:'+name)
# Code-specific exclusion in the legacy channel must be the only edit there.
p=ROOT/'backend/device_service.py';raw=p.read_bytes();normalized=raw.replace(b"            if action['tool_id']=='codex-executor':continue\r\n",b'').replace(b"            if action['tool_id']=='codex-executor':continue\n",b'')
if hashlib.sha256(normalized).hexdigest()!=pre['hashes']['backend/device_service.py']:errors.append('LEGACY_DEVICE_CHANNEL_CHANGED_BEYOND_CODEX_EXCLUSION')
for name,expected in {'config.toml':'ab69d60589b0152fc2f05b2af0d9483d67a7cb889252d03bcd19598edaaa05e8','hooks.json':'fc0f4b77e889e6b47a210bb850afd2a98e6c48795a42229f7a62156c450f5cbc'}.items():
 if sha(Path.home()/'.codex'/name)!=expected:errors.append('GLOBAL_CONFIG_CHANGED:'+name)
probe="import sys;import backend.codex.service,backend.codex.api;assert not any(n in sys.modules for n in ('device_agent.codex_adapter','google.genai','openai'))"
if subprocess.run([sys.executable,'-B','-c',probe],capture_output=True,cwd=ROOT).returncode:errors.append('CODEX_CONTROL_PLANE_ISOLATION')
for name in ('backend/codex/service.py','backend/codex/api.py'):
 tree=ast.parse((ROOT/name).read_text('utf8'))
 for node in ast.walk(tree):
  names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
  if any(n.startswith(('subprocess','openai','google.genai','device_agent')) for n in names):errors.append('AUTHORITY_PROCESS_IMPORT:'+name)
head=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
if head!=pre['head']:errors.append('HEAD_CHANGED')
result={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':'7F-E','status':'VERIFIED' if not errors else 'FAILED','errors':errors,'authorized_existing_changes':changed,'legacy_findings_explained':exceptions,'immutable_phase_e_files_verified':immutable,'migrations_1_to_8_unchanged':all(n in immutable for n in pre['hashes'] if n.startswith('backend/migrations/')),'protocols_v1_unchanged':all(n in immutable for n in pre['hashes'] if n.startswith('contracts/')),'protected_external_integrity':base.get('protected_external_integrity'),'model_call_ledgers':base.get('model_call_ledgers'),'head':head,'global_configuration_unchanged':not any(e.startswith('GLOBAL_CONFIG') for e in errors),'model_calls_during_audit':0,'phase_real_codex_cli_executions':1,'limitations':['Static source/integrity audit and local test evidence; not real Codex/Owner acceptance.','No claim of general Windows sandbox certification; native probes are bounded to observed fixtures.']}
print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
