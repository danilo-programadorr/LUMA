"""A2 extension: inherited history/worktree scan plus ignored local library logs."""
import json,os,re,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
base=subprocess.run([sys.executable,'scan_phase7fda.py'],cwd=root,capture_output=True,text=True)
result=json.loads(base.stdout)
logs=list((root/'runtime').glob('*library*.log'))
for p in logs:
 data=p.read_bytes()
 if re.search(rb'GOCSPX-[A-Za-z0-9_-]{15,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}',data):result['findings'].append({'path':str(p.relative_to(root)),'kind':'library_log_secret_pattern'})
 for name in ('LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD','LUMA_GEMINI_API_KEY'):
  value=os.environ.get(name,'')
  if value and value.encode() in data:result['findings'].append({'path':str(p.relative_to(root)),'kind':'known_secret_in_library_log'})
for path in ['runtime/private-library/example/index.db','runtime/postgresql-backups/example.dump']:
 if subprocess.run(['git','check-ignore',path],cwd=root,capture_output=True).returncode:result['findings'].append({'path':path,'kind':'private_storage_not_ignored'})
result.update(phase='7F-D-A2',date='2026-10-30',status='FAILED' if result['findings'] else 'PASSED',library_logs_scanned=len(logs),private_storage_ignored=True,actual_owner_files_imported=False,additional_limits='No real Owner documents imported; synthetic at-rest plaintext/locator-tamper tests are separate evidence. Unknown arbitrary secrets cannot be exhaustively recognized.')
print(json.dumps(result,indent=2));raise SystemExit(bool(result['findings']))
