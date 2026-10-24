"""Sanitized pre-push scan of reachable Git blobs and non-ignored working files."""
import json,os,re,subprocess
from pathlib import Path
patterns={
 'dpapi_blob':rb'01000000d08c9ddf0115d1118c7a00c04fc297eb[0-9a-fA-F]{64,}',
 'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
 'google_key':rb'AIza[0-9A-Za-z_-]{30,}',
 'github_token':rb'(?:gh[pousr]_[0-9A-Za-z]{25,}|github_pat_[A-Za-z0-9_]{40,})',
 'oauth_token':rb'ya29\.[A-Za-z0-9_-]{30,}',
 'jwt':rb'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}',
 'openai_key':rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{35,}',
 'database_password':rb'postgres(?:ql)?(?:\+\w+)?://[^\s:/]+:[^\s@]{4,}@',
}
findings=[]; blobs=0
def check(data,path,oid=None):
 for kind,pattern in patterns.items():
  if re.search(pattern,data):findings.append(dict(path=path,object=oid,kind=kind))
 for name in ('LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD'):
  secret=os.environ.get(name,'')
  if secret and secret.encode() in data:findings.append(dict(path=path,object=oid,kind='local_password_literal'))
 if re.search(r'(^|/)(\.env|auth\.json|credentials\.json|id_rsa|id_ed25519)$',path):
  findings.append(dict(path=path,object=oid,kind='sensitive_filename'))
objects=subprocess.check_output(['git','rev-list','--objects','HEAD']).decode().splitlines()
proc=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for row in objects:
 parts=row.split(' ',1);oid=parts[0];path=parts[1] if len(parts)>1 else ''
 proc.stdin.write((oid+'\n').encode());proc.stdin.flush()
 header=proc.stdout.readline().decode().split()
 data=proc.stdout.read(int(header[2]));proc.stdout.read(1)
 if header[1]=='blob':blobs+=1;check(data,path,oid)
proc.stdin.close();proc.wait()
files=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard']).decode().split('\0')
working=0
for name in set(files):
 if name and Path(name).is_file():working+=1;check(Path(name).read_bytes(),name)
result=dict(status='PASSED' if not findings else 'FAILED',history_blobs=blobs,working_files=working,
 scope='all HEAD history plus tracked/non-ignored working files; known local passwords checked when provided',
 findings=findings)
print(json.dumps(result,indent=2))
raise SystemExit(bool(findings))
