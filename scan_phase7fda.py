"""Research scan extends existing whole-history/working-tree checks."""
import json,subprocess,sys,base64
from pathlib import Path
root=Path(__file__).resolve().parent
result=json.loads(subprocess.run([sys.executable,'scan_phase7fc.py'],cwd=root,capture_output=True,text=True).stdout)
paths=[root/p for p in subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root).decode().split('\0') if p]
# Startup/acceptance logs are local and ignored, but still part of this review.
import re,os
research_logs=list((root/'runtime').glob('research*.log'))
for log in research_logs:
    data=log.read_bytes()
    if re.search(rb'GOCSPX-[A-Za-z0-9_-]{15,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',data):result['findings'].append({'path':str(log.relative_to(root)),'kind':'research_log_secret_pattern'})
    for name in ('LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD','LUMA_GEMINI_API_KEY'):
        value=os.environ.get(name,'')
        if value and value.encode() in data:result['findings'].append({'path':str(log.relative_to(root)),'kind':'known_secret_in_research_log'})
result['research_logs_scanned']=len(research_logs)
identity=root/'runtime/research-agent/identity.db'
if identity.exists():
    from device_agent.identity import Identity
    raw=Identity(identity).key().private_bytes_raw()
    variants=(raw,base64.b64encode(raw),base64.urlsafe_b64encode(raw),raw.hex().encode())
    for p in paths:
        if p.is_file() and any(x in p.read_bytes() for x in variants):result['findings'].append({'path':str(p.relative_to(root)),'kind':'research_device_private_key'})
ignored=subprocess.run(['git','check-ignore','runtime/research-agent/identity.db'],cwd=root,capture_output=True).returncode==0
if not ignored:result['findings'].append({'kind':'research_identity_not_ignored'})
result.update(phase='7F-D-A',status='FAILED' if result['findings'] else 'PASSED',research_identity_exists=identity.exists(),research_identity_ignored=ignored)
print(json.dumps(result,indent=2));raise SystemExit(bool(result['findings']))
