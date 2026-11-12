"""7F-C scan extends baseline with local agent logs and private-key literal checks."""
import json,os,subprocess,re,sqlite3,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
base=subprocess.run([os.sys.executable,'scan_phase7fb.py'],cwd=root,capture_output=True,text=True)
r=json.loads(base.stdout)
paths=set(subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root).decode().split('\0'))
paths.update(p.relative_to(root).as_posix() for p in (root/'runtime').glob('*7fc*.log'))
private=[];identity=root/'runtime/device-agent/identity.db'
if identity.exists():
    from device_agent.identity import Identity
    private=[Identity(identity).key().private_bytes_raw()]
for relative in paths:
    p=root/relative
    if not p.is_file():continue
    data=p.read_bytes()
    for value in private:
        import base64
        if any(x in data for x in (value,base64.b64encode(value),base64.urlsafe_b64encode(value),value.hex().encode())):r['findings'].append({'path':relative,'kind':'device_private_key_literal'})
    if re.search(rb'GOCSPX-[A-Za-z0-9_-]{15,}|1//[A-Za-z0-9_-]{25,}|-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',data):r['findings'].append({'path':relative,'kind':'secret_pattern'})
ignored=subprocess.run(['git','check-ignore','runtime/device-agent/identity.db'],cwd=root,capture_output=True,text=True).returncode==0
if not ignored:r['findings'].append({'path':'runtime/device-agent/identity.db','kind':'identity_not_ignored'})
r.update(status='FAILED' if r['findings'] else 'PASSED',phase='7F-C',device_storage_ignored=ignored,real_device_identity_exists=identity.exists(),private_key_values_printed=False,enrollment_code_policy='Raw code only in response/temporary UI memory and hidden local input; central persistence is digest only. Unknown arbitrary codes cannot be exhaustively recognized by pattern scan.')
print(json.dumps(r,indent=2));raise SystemExit(bool(r['findings']))
