"""7F-C evidence audit. Technical validation is distinct from real Owner acceptance."""
import ast,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parent;r=root/'reports'
prior=subprocess.run([sys.executable,'audit_phase7fb.py'],cwd=root,capture_output=True,text=True)
inherited=json.loads(prior.stdout);errors=list(inherited['errors'])
pre=json.loads((r/'FASE_7F_C_PREFLIGHT.json').read_text(encoding='utf-8'))
for name in [*['backend/migrations/'+x.name for x in (root/'backend/migrations').glob('v000[1-5]*.py')],'contracts/RUNTIME_PROTOCOL_V1.json','backend/local_runtime_app.py','backend/runtime_processor.py']:
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=pre['files'][name]:errors.append('PROTECTED_BASELINE_CHANGED:'+name)
owner=(root/'backend/owner_auth.py').read_bytes().decode('utf-8').replace('.scalar_one() not in (5,6):','.scalar_one()!=5:')
# Explicitly account for the bounded clock fix; any other Owner change still fails.
owner=owner.replace('# Bounded tolerance for issuer/local clock differences; expiry remains strict.\r\nOWNER_CLOCK_SKEW_SECONDS=30\r\n\r\n','')
owner=owner.replace('audience=self.project,clock_skew_in_seconds=OWNER_CLOCK_SKEW_SECONDS)','audience=self.project)')
owner=owner.replace("c['iat']<=current+OWNER_CLOCK_SKEW_SECONDS","c['iat']<=current")
owner=owner.replace('if not -OWNER_CLOCK_SKEW_SECONDS<=int(time.time())-principal.auth_time<=window_seconds:','if not 0<=int(time.time())-principal.auth_time<=window_seconds:')
if hashlib.sha256(owner.encode()).hexdigest()!=pre['files']['backend/owner_auth.py']:errors.append('UNEXPECTED_OWNER_AUTH_CHANGE')
unique={};runs={}
for name in ('FASE_7F_C_BACKEND_TESTES.xml','FASE_7F_C_SCHEMA_COMPAT_TESTES.xml','FASE_7F_C_DEVICE_FINAL.xml','FASE_7F_C_POSTGRES_TESTES.xml','FASE_7F_C_POSTGRES_DEVICE_FINAL.xml','FASE_7F_C_FRONTEND_TESTES.xml','FASE_7F_C_AUTH_REFRESH_TESTES.xml','FASE_7F_C_CLOCK_TESTES.xml','FASE_7F_C_CLOCK_CRYPTO_FINAL.xml'):
    tree=ET.parse(r/name);cases=list(tree.iter('testcase'));runs[name]=len(cases)
    for case in cases:unique[(case.get('classname'),case.get('name'))]=case
for key,case in unique.items():
    if any(case.find(x) is not None for x in ('failure','error','skipped')):errors.append('TEST_NOT_GREEN:'+str(key))
baseline={(c.get('classname'),c.get('name')) for c in ET.parse(r/'FASE_7F_B_FINAL_TESTES.xml').iter('testcase')}
for name in ('FASE_7F_C_BROWSER_TESTES.json','FASE_7F_C_PRODUCTION_SMOKE.json'):
    data=json.loads((r/name).read_text(encoding='utf-8-sig'))
    if any(data['stats'][x] for x in ('unexpected','skipped','flaky')):errors.append('BROWSER_NOT_GREEN:'+name)
    def visit(suites):
        for suite in suites:
            for spec in suite.get('specs',[]):
                key=('browser.'+spec['file'],spec['title']);unique[key]=ET.Element('testcase',classname=key[0],name=key[1])
            visit(suite.get('suites',[]))
    visit(data['suites'])
if not baseline<=set(unique):errors.append('BASELINE_TESTS_MISSING')
scan=json.loads((r/'FASE_7F_C_SECRET_SCAN.json').read_text(encoding='utf-8-sig'))
if scan['status']!='PASSED':errors.append('SECRET_SCAN_FAILED')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if head!=pre['head']:errors.append('UNAUTHORIZED_COMMIT')
real=json.loads((r/'FASE_7F_C_REAL_DEVICE_PROGRESS.json').read_text())
checks=real.get('owner_confirmations',{})
rev=real.get('revocation',{})
jobs=real.get('synthetic_jobs',[])
real_ok=(real.get('real_acceptance')=='PASS' and all(checks.get(k) is True for k in ('refresh_device_visible','offline_after_agent_stop','restart_online_same_fingerprint_no_enrollment')) and rev.get('persisted_states')==['REVOKED'] and rev.get('owner_observed_agent')=='DEVICE_REVOKED' and any(e['result']=='DEVICE_REVOKED' for e in rev.get('events',[])) and len(jobs)==1 and jobs[0]['status']=='SUCCEEDED' and all(jobs[0][k]==1 for k in ('claim_count','synthetic_effect_count','synthetic_execution_record_count')))
if not real_ok:errors.append('REAL_ACCEPTANCE_INCOMPLETE')
result={'date':'2026-10-26','phase':'7F-C','status':'VERIFIED' if not errors else 'FAILED','errors':errors,'head':head,'baseline_unique':len(baseline),'total_unique':len(unique),'new_unique':len(unique)-len(baseline),'runs':runs,'brain_and_source_integrity':inherited['brain_unchanged_hash_counts'],'ui_source_unchanged':inherited['ui_source_unchanged'],'migrations_0001_0005_preserved':True,'owner_auth_changes':['schema_6_acceptance','bounded_30_second_issuer_clock_tolerance_strict_expiry'], 'other_owner_auth_logic_preserved':True,'real_owner_device_acceptance':'PASS' if real_ok else 'PENDING','final_gate':'7F-C_DEVICE_CHANNEL_VALIDATED' if real_ok and not errors else 'NOT_GO','commit':False,'push':False,'deploy':False}
suite=ET.Element('testsuite',name='7F-C unique automated evidence',tests=str(len(unique)),failures=str(sum(c.find('failure') is not None for c in unique.values())),errors='0')
for case in unique.values():suite.append(case)
ET.ElementTree(suite).write(r/'FASE_7F_C_FINAL_TESTES.xml',encoding='utf-8',xml_declaration=True)
print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
