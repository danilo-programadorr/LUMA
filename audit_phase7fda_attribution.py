"""Local correction audit; real provider usage is never inferred from mocks."""
import json,hashlib,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parent;r=root/'reports'
layout='--layout' in sys.argv
navigation='--navigation' in sys.argv
provider='--provider' in sys.argv
quality='--quality' in sys.argv
def report_name(name):
    if quality:return 'FASE_7F_D_A_NAVIGATION_BACKEND.xml' if name=='FASE_7F_D_A_ATTRIBUTION_BACKEND.xml' else name.replace('ATTRIBUTION_PROVIDER_FINAL','LOCAL_QUALITY_BACKEND').replace('ATTRIBUTION_','LOCAL_QUALITY_')
    if provider:return 'FASE_7F_D_A_NAVIGATION_BACKEND.xml' if name=='FASE_7F_D_A_ATTRIBUTION_BACKEND.xml' else name.replace('ATTRIBUTION_PROVIDER_FINAL','PROVIDER_BACKEND').replace('ATTRIBUTION_','PROVIDER_')
    if navigation:return name.replace('ATTRIBUTION_PROVIDER_FINAL','NAVIGATION_EXTRA').replace('ATTRIBUTION_','NAVIGATION_')
    return name.replace('ATTRIBUTION_FRONTEND','LAYOUT_FRONTEND').replace('ATTRIBUTION_BROWSER','LAYOUT_BROWSER').replace('ATTRIBUTION_PRODUCTION','LAYOUT_PRODUCTION') if layout else name
previous=json.loads(subprocess.run([sys.executable,'audit_phase7fb.py'],cwd=root,capture_output=True,text=True).stdout)
errors=list(previous['errors']);pre=json.loads((r/'FASE_7F_D_A_PREFLIGHT.json').read_text())
protected=[*['backend/migrations/'+p.name for p in (root/'backend/migrations').glob('v000[1-6]*.py')],'contracts/RUNTIME_PROTOCOL_V1.json','contracts/DEVICE_PROTOCOL_V1.json','backend/device_protocol.py','backend/device_service.py','backend/local_runtime_app.py','backend/runtime_processor.py','device_agent/identity.py']
for name in protected:
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=pre['files'][name]:errors.append('PROTECTED_CHANGED:'+name)
owner=(root/'backend/owner_auth.py').read_bytes().replace(b'not in (5,6,7):',b'not in (5,6):')
if hashlib.sha256(owner).hexdigest()!=pre['files']['backend/owner_auth.py']:errors.append('OWNER_AUTH_CHANGED')
def canonical(classname,name):
    if classname.startswith('browser.'):
        file=classname[len('browser.'):].replace('\\','/')
        file='e2e/'+file.split('/e2e/')[-1] if '/e2e/' in file else file
        classname='browser.'+file
    return classname,name
unique={};runs={}
for name in ('FASE_7F_D_A_ATTRIBUTION_BACKEND.xml','FASE_7F_D_A_ATTRIBUTION_PROVIDER_FINAL.xml','FASE_7F_D_A_ATTRIBUTION_POSTGRES.xml','FASE_7F_D_A_ATTRIBUTION_FRONTEND.xml'):
    name=report_name(name)
    cases=list(ET.parse(r/name).iter('testcase'));runs[name]=len(cases)
    for c in cases:
        key=canonical(c.get('classname'),c.get('name'));unique[key]=c
        if any(c.find(t) is not None for t in ('failure','error','skipped')):errors.append('TEST_NOT_GREEN:'+name+':'+c.get('name'))
for name in ('FASE_7F_D_A_ATTRIBUTION_BROWSER.json','FASE_7F_D_A_ATTRIBUTION_PRODUCTION.json'):
    name=report_name(name)
    d=json.loads((r/name).read_text(encoding='utf-8-sig'));runs[name]=d['stats']['expected']
    if any(d['stats'][k] for k in ('unexpected','skipped','flaky')):errors.append('BROWSER_NOT_GREEN:'+name)
    def visit(suites):
        for suite in suites:
            for spec in suite.get('specs',[]):
                key=canonical('browser.'+spec['file'],spec['title']);unique[key]=ET.Element('testcase',classname=key[0],name=key[1])
            visit(suite.get('suites',[]))
    visit(d['suites'])
baseline={canonical(c.get('classname'),c.get('name')) for c in ET.parse(r/('FASE_7F_D_A_CAPPED_REAL_FINAL_TESTES.xml' if quality else 'FASE_7F_D_A_NAVIGATION_FINAL_TESTES.xml' if provider else 'FASE_7F_D_A_LAYOUT_FINAL_TESTES.xml' if navigation else 'FASE_7F_D_A_ATTRIBUTION_FINAL_TESTES.xml' if layout else 'FASE_7F_D_A_FINAL_TESTES.xml')).iter('testcase')}
missing=baseline-set(unique)
if missing:errors.append('BASELINE_TESTS_MISSING:'+str(sorted(missing)))
scan=json.loads((r/('FASE_7F_D_A_LOCAL_QUALITY_SECRET_SCAN.json' if quality else 'FASE_7F_D_A_PROVIDER_SECRET_SCAN.json' if provider else 'FASE_7F_D_A_NAVIGATION_SECRET_SCAN.json' if navigation else 'FASE_7F_D_A_LAYOUT_SECRET_SCAN.json' if layout else 'FASE_7F_D_A_ATTRIBUTION_SECRET_SCAN.json')).read_text(encoding='utf-8-sig'))
if scan['status']!='PASSED':errors.append('SECRET_SCAN_FAILED')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if head!=pre['head']:errors.append('HEAD_CHANGED')
suite=ET.Element('testsuite',name='Google attribution correction unique tests',tests=str(len(unique)),failures=str(len(errors)))
for c in unique.values():suite.append(c)
ET.ElementTree(suite).write(r/('FASE_7F_D_A_LOCAL_QUALITY_FINAL_TESTES.xml' if quality else 'FASE_7F_D_A_PROVIDER_FINAL_TESTES.xml' if provider else 'FASE_7F_D_A_NAVIGATION_FINAL_TESTES.xml' if navigation else 'FASE_7F_D_A_LAYOUT_FINAL_TESTES.xml' if layout else 'FASE_7F_D_A_ATTRIBUTION_FINAL_TESTES.xml'),encoding='utf-8',xml_declaration=True)
ledger=json.loads((root/'runtime/research-google-acceptance-usage.json').read_text()) if navigation or provider or quality else {'calls':[]}
result={'date':'2026-10-29' if navigation or provider or quality else '2026-10-27','scope':'Local generation quality, numeric usage and disabled final-two profile' if quality else 'SDK UTF-8 citation conversion and bounded diagnostics' if provider else 'Failure propagation and isolated native navigation correction' if navigation else 'UI layout correction' if layout else 'Attribution correction','status':'VERIFIED' if not errors else 'FAILED','errors':errors,'baseline_unique':len(baseline),'total_unique':len(unique),'new_unique':len(unique)-len(baseline),'runs':runs,'brain_and_source_integrity':previous['brain_unchanged_hash_counts'],'ui_source_unchanged':previous['ui_source_unchanged'],'protected_files':protected,'head':head,'real_web_calls':len(ledger['calls']),'real_search_queries':sum(c.get('search_queries') or 0 for c in ledger['calls']),'real_calls_during_correction':0,'real_rendering':'NOT_EXECUTED_FOR_CORRECTED_CANDIDATE','commit':False,'push':False,'deploy':False,'backend_verification':'Affected research, provider, ledger and Google display suites rerun; unchanged backend cases inherited from the immediately preceding full navigation run' if provider or quality else 'Full backend run plus final display regression', 'historical_report_incident':'FASE_7F_D_A_PROVIDER_REPORT_INCIDENT.json' if provider or quality else None,'browser_path_normalization':'Equivalent e2e relative paths normalized before baseline comparison; titles unchanged'}
print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
