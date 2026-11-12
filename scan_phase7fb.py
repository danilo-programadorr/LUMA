"""Sanitized closure scan; public Web key is allowed only in local config/build."""
import hashlib,json,os,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
base=subprocess.run([os.sys.executable,'scan_backup.py'],cwd=root,capture_output=True,text=True)
result=json.loads(base.stdout)
public={}
for line in (root/'web/.env.local').read_text(encoding='utf-8').splitlines():
    if '=' in line:
        key,value=line.split('=',1)
        public[key]=value
webkey=public['VITE_FIREBASE_API_KEY'].encode()
patterns={
 'oauth_client_secret':rb'GOCSPX-[A-Za-z0-9_-]{15,}',
 'refresh_token':rb'1//[A-Za-z0-9_-]{25,}',
 'id_token':rb'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}',
 'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
 'google_api_key':rb'AIza[0-9A-Za-z_-]{30,}',
}
files=[root/'web/.env.local',*list((root/'web/dist').rglob('*')),*list((root/'runtime').glob('owner-7fb-*.log'))]
tracked=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root).decode().split('\0')
files+= [root/x for x in tracked if x]
count=0;public_occurrences=0
for path in set(files):
    if not path.is_file():continue
    count+=1;data=path.read_bytes();relative=path.relative_to(root).as_posix()
    for kind,pattern in patterns.items():
        for match in re.finditer(pattern,data):
            if kind=='google_api_key' and match.group()==webkey and (relative=='web/.env.local' or relative.startswith('web/dist/')):
                public_occurrences+=1;continue
            result['findings'].append({'path':relative,'kind':kind})
    for variable in ('LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD'):
        value=os.environ.get(variable,'')
        if value and value.encode() in data:result['findings'].append({'path':relative,'kind':'local_password_literal'})
result.update(status='FAILED' if result['findings'] else 'PASSED',additional_files_scanned=count,public_web_key_occurrences=public_occurrences,public_web_key_sha256=hashlib.sha256(webkey).hexdigest(),public_key_exception_scope=['web/.env.local','web/dist/'],limitations='Pattern scan plus known local PostgreSQL password literals; no claim of exhaustive detection of unknown arbitrary secrets. SDK-managed browser session storage is outside repository/report scope.')
print(json.dumps(result,indent=2))
raise SystemExit(bool(result['findings']))
