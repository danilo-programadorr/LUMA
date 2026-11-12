"""Research evidence audit; never promotes a real gate from synthetic tests."""
import json,hashlib,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parent;r=root/'reports'
previous=json.loads(subprocess.run([sys.executable,'audit_phase7fb.py'],cwd=root,capture_output=True,text=True).stdout)
errors=list(previous['errors']);pre=json.loads((r/'FASE_7F_D_A_PREFLIGHT.json').read_text())
protected=[*['backend/migrations/'+p.name for p in (root/'backend/migrations').glob('v000[1-6]*.py')],'contracts/RUNTIME_PROTOCOL_V1.json','contracts/DEVICE_PROTOCOL_V1.json','backend/device_protocol.py','backend/device_service.py','backend/local_runtime_app.py','backend/runtime_processor.py','device_agent/identity.py']
for name in protected:
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=pre['files'][name]:errors.append('PROTECTED_BASELINE_CHANGED:'+name)
owner=(root/'backend/owner_auth.py').read_bytes().replace(b'not in (5,6,7):',b'not in (5,6):')
if hashlib.sha256(owner).hexdigest()!=pre['files']['backend/owner_auth.py']:errors.append('OWNER_AUTH_CHANGED_BEYOND_SCHEMA_ACCEPTANCE')
unique={};runs={}
for name in ('FASE_7F_D_A_FULL_BACKEND_TESTES.xml','FASE_7F_D_A_FINAL_RESEARCH_TESTES.xml','FASE_7F_D_A_POSTGRES_TESTES.xml','FASE_7F_D_A_FRONTEND_TESTES.xml'):
    cases=list(ET.parse(r/name).iter('testcase'));runs[name]=len(cases)
    for case in cases:
        unique[(case.get('classname'),case.get('name'))]=case
        if any(case.find(t) is not None for t in ('failure','error','skipped')):errors.append('TEST_NOT_GREEN:'+name+':'+case.get('name'))
for name in ('FASE_7F_D_A_BROWSER_TESTES.json','FASE_7F_D_A_PRODUCTION_SMOKE.json'):
    data=json.loads((r/name).read_text(encoding='utf-8-sig'))
    if any(data['stats'][k] for k in ('unexpected','skipped','flaky')):errors.append('BROWSER_NOT_GREEN:'+name)
    def visit(suites):
        for suite in suites:
            for spec in suite.get('specs',[]):
                key=('browser.'+spec['file'],spec['title']);unique[key]=ET.Element('testcase',classname=key[0],name=key[1])
            visit(suite.get('suites',[]))
    visit(data['suites'])
baseline={(c.get('classname'),c.get('name')) for c in ET.parse(r/'FASE_7F_C_FINAL_TESTES.xml').iter('testcase')}
if not baseline<=set(unique):errors.append('BASELINE_TESTS_MISSING')
scan=json.loads((r/'FASE_7F_D_A_SECRET_SCAN.json').read_text(encoding='utf-8-sig'))
if scan['status']!='PASSED':errors.append('SECRET_SCAN_FAILED')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if head!=pre['head']:errors.append('UNAUTHORIZED_COMMIT')
suite=ET.Element('testsuite',name='7F-D-A unique automated evidence',tests=str(len(unique)),failures=str(len(errors)))
for case in unique.values():suite.append(case)
ET.ElementTree(suite).write(r/'FASE_7F_D_A_FINAL_TESTES.xml',encoding='utf-8',xml_declaration=True)
result={'date':'2026-10-27','phase':'7F-D-A','status':'VERIFIED' if not errors else 'FAILED','errors':errors,'head':head,'baseline_unique':len(baseline),'total_unique':len(unique),'new_unique':len(unique)-len(baseline),'runs':runs,'brain_and_source_integrity':previous['brain_unchanged_hash_counts'],'ui_source_unchanged':previous['ui_source_unchanged'],'protected_files':protected,'owner_auth_change':'schema7 acceptance only','real_web_calls':0,'real_device_enrollment':'NOT_STARTED','voice_real':'NOT_IMPLEMENTED_BY_DESIGN','final_gate':'LOCAL_VALIDATION_ONLY_REAL_SEARCH_COST_AND_ATTRIBUTION_GATES_PENDING','commit':False,'push':False,'deploy':False}
print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
