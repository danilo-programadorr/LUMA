"""Phase-E scan: inherited history/worktree/build plus executor-owned runtime data."""
import datetime,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
run=subprocess.run([sys.executable,'-B','scan_phase7fb.py'],capture_output=True,cwd=ROOT,timeout=240)
result=json.loads(run.stdout)
# Codex auth files remain SDK-managed; inspect names/references, never contents.
tracked=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
for name in tracked:
 if name and Path(name).name in ('auth.json','credentials.json','id_rsa','id_ed25519'):
  result['findings'].append({'path':name,'kind':'credential_artifact_outside_sdk_storage'})
patterns={'oauth_secret':rb'GOCSPX-[A-Za-z0-9_-]{15,}','refresh_token':rb'1//[A-Za-z0-9_-]{25,}','api_key':rb'(?:sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{35,}|AIza[0-9A-Za-z_-]{30,})','private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----','jwt':rb'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}'}
files=list((ROOT/'runtime/codex-executor').rglob('*'))+list((ROOT/'runtime').glob('*codex*.log'))
count=0
for p in files:
 if not p.is_file():continue
 count+=1;data=p.read_bytes()
 for kind,pattern in patterns.items():
  if re.search(pattern,data):result['findings'].append({'path':p.relative_to(ROOT).as_posix(),'kind':kind})
 for name in ('LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD','LUMA_GEMINI_API_KEY','LUMA_OWNER_TOKEN','LUMA_RUNTIME_TOKEN','LUMA_KNOWLEDGE_TOKEN'):
  value=os.environ.get(name,'')
  if value and value.encode() in data:result['findings'].append({'path':p.relative_to(ROOT).as_posix(),'kind':'known_secret_literal'})
result.update(executed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase='7F-E',status='FAILED' if result['findings'] else 'PASSED',executor_runtime_files_scanned=count,codex_credential_contents_read=False,device_private_keys_decrypted_for_this_scan=False,real_codex_executions_during_scan=0,phase_real_codex_cli_executions=1,limitations='Pattern scan and known PostgreSQL literals when supplied. No exhaustive claim for unknown opaque tokens, binary keys or SDK-managed browser/Codex auth stores. Synthetic redaction tests are separate evidence, not real secret exfiltration tests.')
print(json.dumps(result,indent=2));raise SystemExit(bool(result['findings']))
