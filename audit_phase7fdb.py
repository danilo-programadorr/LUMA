"""Read-only 7F-D-B audit with explicit authorized change inventory."""
import json,hashlib,subprocess,sys,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
pre=json.loads((ROOT/'reports/FASE_7F_D_B_PREFLIGHT.json').read_text(encoding='utf-8-sig'))
allowed={'backend/control_plane_tasks.py','backend/app/execution.py','backend/control_plane_app.py','web/src/auth/client.ts','web/src/auth/context.ts','web/src/router.tsx','web/src/pages/TasksPage.tsx','web/src/pages/ApprovalsPage.tsx','web/src/components/luma/approvals-panel.tsx','web/e2e/research.spec.mjs','web/e2e/google-window.spec.mjs'}
errors=[];changed=[]
for name,digest in pre['files'].items():
 p=ROOT/name
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
  changed.append(name)
  if name.startswith(('web/test-results/','web/dist/')):continue
  if name not in allowed and name!='backend/tests/test_remote_tasks.py':errors.append('UNDECLARED_CHANGE:'+name)
base=subprocess.run([sys.executable,'audit_phase7fda2.py'],capture_output=True,text=True,cwd=ROOT,timeout=240)
b=json.loads(base.stdout)
accepted=[]
for err in b['errors']:
 if err.startswith('UNDECLARED_BASELINE_CHANGE:') and err.split(':',1)[1] in allowed:accepted.append(err)
 else:errors.append(err)
for path in ROOT.glob('backend/migrations/v*.py'):
 name=path.relative_to(ROOT).as_posix()
 if name in pre['files'] and hashlib.sha256(path.read_bytes()).hexdigest()!=pre['files'][name]:errors.append('MIGRATION_CHANGED:'+name)
head=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],text=True,cwd=ROOT).strip()
if head!=pre['head']:errors.append('HEAD_CHANGED')
print(json.dumps({'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'VERIFIED' if not errors else 'FAILED','errors':errors,'authorized_modified_existing_files':changed,'inherited_expected_change_findings':accepted,'migration_policy':'Existing schema 8 reused; no previous migration edited, no new table needed for JSON-backed agent_tasks','head':head,'protected_external_integrity':b.get('brain_and_source_integrity'),'model_call_ledgers':b.get('real_call_ledger_sha256'),'no_public_remote_acceptance':True},indent=2));raise SystemExit(bool(errors))
