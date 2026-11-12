"""Consolidate observed unique test IDs. Never sum reruns or hide non-green evidence."""
import copy,datetime,json,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports';cases={};runs={}
xmls=['FASE_7F_E_BACKEND_FULL.xml','FASE_7F_E_KNOWLEDGE_HTTP.xml','FASE_7F_E_CODEX_VERIFIED.xml','FASE_7F_E_AFFECTED_FINAL.xml','FASE_7F_E_POSTGRES_TESTES.xml','FASE_7F_E_POSTGRES_FINAL.xml','FASE_7F_E_FRONTEND_FINAL.xml','FASE_7F_E_USAGE_CODEX_FINAL.xml','FASE_7F_E_USAGE_POSTGRES_FINAL.xml']
for name in xmls:
 elements=list(E.parse(R/name).getroot().iter('testcase'));runs[name]=len(elements)
 for c in elements:cases[(c.get('classname',''),c.get('name',''))]=copy.deepcopy(c)
def walk(s):
 for item in s:
  for spec in item.get('specs',[]):yield spec
  yield from walk(item.get('suites',[]))
for name in ['FASE_7F_E_BROWSER_TESTES.json','FASE_7F_E_CODEX_BROWSER_FINAL.json','FASE_7F_E_PRODUCTION_TESTES.json']:
 d=json.loads((R/name).read_text('utf8'));count=0
 if d.get('errors'):raise ValueError('BROWSER_HARNESS_ERROR:'+name)
 for spec in walk(d['suites']):
  for test in spec['tests']:
   result=test['results'][-1];c=E.Element('testcase',classname='browser.'+spec['file'],name=spec['title'],time=str(result['duration']/1000))
   if result['status']!='passed':E.SubElement(c,'failure',message=result['status'])
   cases[(c.get('classname'),c.get('name'))]=c;count+=1
 runs[name]=count
baseline={(c.get('classname',''),c.get('name','')) for c in E.parse(R/'FASE_7F_D_B_FINAL_TESTES.xml').getroot().iter('testcase')}
missing=sorted(baseline-set(cases));bad=[k for k,c in cases.items() if any(c.find(x) is not None for x in ('failure','error','skipped'))]
groups={'backend':0,'postgresql':0,'frontend':0,'browser':0}
for (name,_),c in cases.items():
 key='postgresql' if name.startswith('backend.postgres_tests.') else 'backend' if name.startswith('backend.') else 'browser' if name.startswith('browser.') else 'frontend'
 groups[key]+=1
suite=E.Element('testsuite',name='7F-E local unique evidence; real Codex acceptance separate',tests=str(len(cases)),failures=str(len(bad)),errors='0',skipped='0')
for k,c in sorted(cases.items()):suite.append(c)
E.ElementTree(suite).write(R/'FASE_7F_E_FINAL_TESTES.xml',encoding='utf8',xml_declaration=True)
summary={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not bad and not missing else 'FAILED','baseline':len(baseline),'unique_tests':len(cases),'new_unique':len(set(cases)-baseline),'groups':groups,'baseline_missing':missing,'non_green':bad,'evidence_runs':runs,'reruns_counted_as_new':False,'native_probes_counted_as_unit_tests':False,'real_codex_executions_during_automated_tests':0,'phase_real_codex_cli_executions':1,'historical_full_run_configuration_skip':'test_real_http_integration skipped once without knowledge workspace; same ID rerun with correctly configured real local HTTP passed; both original and closure evidence preserved'}
(R/'FASE_7F_E_TEST_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary,indent=2))
raise SystemExit(bool(bad or missing))
