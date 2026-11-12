"""Consolidate unique GREEN A2 cases; later focused executions override earlier results."""
import json,xml.etree.ElementTree as E
from pathlib import Path
r=Path(__file__).resolve().parent/'reports';unique={};runs={};errors=[]
def key(c):return (c.get('classname','').replace('\\','/'),c.get('name',''))
for name in ['FASE_7F_D_A2_BACKEND_CONFIGURED.xml','FASE_7F_D_A2_PRIVATE_FINAL.xml','FASE_7F_D_A2_STORE_ENCODING_FINAL.xml','FASE_7F_D_A2_POSTGRES_FINAL.xml','FASE_7F_D_A2_FRONTEND_FINAL.xml','FASE_7F_D_A2_UI_FINAL.xml']:
 cases=list(E.parse(r/name).iter('testcase'));runs[name]=len(cases)
 for c in cases:
  if any(c.find(n) is not None for n in ('failure','error','skipped')):errors.append('CASE_NOT_GREEN:'+name+':'+c.get('name'))
  unique[key(c)]=c
for name in ['FASE_7F_D_A2_BROWSER.json','FASE_7F_D_A2_BROWSER_REVIEW.json','FASE_7F_D_A2_PRODUCTION.json']:
 d=json.loads((r/name).read_text(encoding='utf-8-sig'));runs[name]=d['stats']['expected']
 if any(d['stats'][x] for x in ('unexpected','skipped','flaky')):errors.append('BROWSER_NOT_GREEN:'+name)
 def visit(suites):
  for suite in suites:
   for spec in suite.get('specs',[]):
    c=E.Element('testcase',classname='browser.'+spec['file'].replace('\\','/'),name=spec['title']);unique[key(c)]=c
   visit(suite.get('suites',[]))
 visit(d['suites'])
baseline={key(c) for c in E.parse(r/'FASE_7F_D_A_REJECTION_FINAL_TESTES.xml').iter('testcase')}
missing=sorted(baseline-set(unique))
if missing:errors.append('BASELINE_MISSING')
groups={name:sum(1 for k in unique if k[0].startswith(prefix)) for name,prefix in [('backend','backend.tests.'),('postgresql','backend.postgres_tests.'),('frontend','src/'),('browser','browser.')]}
if sum(groups.values())!=len(unique):errors.append('UNGROUPED_CASES')
suite=E.Element('testsuite',name='7F-D-A2 unique GREEN local evidence',tests=str(len(unique)),failures='0',errors='0',skipped='0')
for c in unique.values():suite.append(c)
E.ElementTree(suite).write(r/'FASE_7F_D_A2_FINAL_TESTES.xml',encoding='utf-8',xml_declaration=True)
result={'date':'2026-10-30','status':'PASS' if not errors else 'FAIL','unique_tests':len(unique),'groups':groups,'baseline_unique':len(baseline),'baseline_missing':missing,'new_unique':len(unique)-len(baseline),'errors':errors,'evidence_runs':runs,'scope':'Full backend844/PG81/frontend84/browser24 plus latest affected suites, 5 final responsive cases and 2 build smoke cases. Unique IDs counted once. Real Owner document import is not claimed.'}
(r/'FASE_7F_D_A2_TEST_SUMMARY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
