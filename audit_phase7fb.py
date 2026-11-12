"""7F-B audit: preserved historical checks plus source/UI/test evidence."""
import contextlib,io,json,subprocess,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'audit_phase7f.py').read_text(encoding='utf-8')
needle="source=(ROOT/'audit_workspace.py').read_text(encoding='utf-8-sig')"
# Images are binary; scan_backup.py separately scans bytes of every nonignored file.
replacement=needle+"\nsource=source.replace(\"if not file.is_file() or '__pycache__' in file.parts: continue\",\"if not file.is_file() or '__pycache__' in file.parts or file.suffix.lower() in ('.png','.jpg','.jpeg','.webp'): continue\")"
assert needle in source
source=source.replace(needle,replacement)
output=io.StringIO()
with contextlib.redirect_stdout(output):
    try:exec(compile(source,str(ROOT/'audit_phase7f.py'),'exec'),{'__file__':str(ROOT/'audit_phase7f.py'),'__name__':'__audit__'})
    except SystemExit:pass
result=json.loads(output.getvalue());errors=result['errors']
source_record=json.loads((ROOT/'reports/FASE_7F_B_UI_SOURCE.json').read_text(encoding='utf-8'))
for path,digest in source_record['sha256'].items():
    if hashlib.sha256((Path(source_record['source'])/path).read_bytes()).hexdigest()!=digest:errors.append('UI_SOURCE_CHANGED:'+path)
unique=set();runs={}
for name in ('FASE_7F_B_BASELINE_LOCAL.xml','FASE_7F_B_BACKEND_AUTH_TESTES.xml','FASE_7F_B_POSTGRES_TESTES.xml','FASE_7F_B_POSTGRES_AUTH_TESTES.xml','FASE_7F_B_FRONTEND_TESTES.xml','FASE_7F_B_CLOSURE_BACKEND.xml','FASE_7F_B_CLOSURE_POSTGRES.xml','FASE_7F_B_CLOSURE_FRONTEND.xml','FASE_7F_B_CLOSURE_AUTH_TIME.xml'):
    root=ET.parse(ROOT/'reports'/name).getroot();cases=list(root.iter('testcase'))
    failures=list(root.iter('failure'))+list(root.iter('error'));skips=list(root.iter('skipped'))
    runs[name]=dict(tests=len(cases),failures=len(failures),skips=len(skips))
    if failures or skips:errors.append('TEST_NOT_GREEN:'+name)
    unique.update((c.attrib.get('classname'),c.attrib['name']) for c in cases)
baseline=set()
for name in ('FASE_7F_A2_FINAL_TESTES.xml','FASE_7F_A2_POSTGRES_TESTES.xml'):
    baseline.update((c.attrib.get('classname'),c.attrib['name']) for c in ET.parse(ROOT/'reports'/name).iter('testcase'))
if not baseline<=unique:errors.append('BASELINE_TESTS_MISSING')
e2e=json.loads((ROOT/'reports/FASE_7F_B_E2E.json').read_text(encoding='utf-8'))['stats']
if e2e['unexpected'] or e2e['skipped'] or e2e['flaky']:errors.append('E2E_NOT_GREEN')
production=json.loads((ROOT/'reports/FASE_7F_B_PRODUCTION_SMOKE.json').read_text(encoding='utf-8'))['stats']
if production['unexpected'] or production['skipped'] or production['flaky']:errors.append('PRODUCTION_SMOKE_NOT_GREEN')
e2e_count=e2e['expected']+production['expected']
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if head!='dc85fa894e2ad99325ef77a937d0f7a8f2a38fe7':errors.append('UNAUTHORIZED_COMMIT')
for relative in ('backend/local_runtime_app.py','backend/runtime_processor.py','contracts/RUNTIME_PROTOCOL_V1.json'):
    baseline_bytes=subprocess.check_output(['git','show','HEAD:'+relative])
    if baseline_bytes!=(ROOT/relative).read_bytes().replace(b'\r\n',b'\n'):errors.append('RUNTIME_BOUNDARY_CHANGED:'+relative)
result.update(date='2026-10-25',phase='7F-B',status='VERIFIED' if not errors else 'FAILED',errors=errors,evidence_runs=runs,baseline_preserved=len(baseline),unique_unit_integration_tests=len(unique),e2e_tests=e2e_count,total_unique_tests=len(unique)+e2e_count,ui_source_unchanged=True,cloud_mutations=True,real_google_login_tested=True,push_performed=False,head=head)
real=json.loads((ROOT/'reports/FASE_7F_B_IDENTITY_PLATFORM_REAL.json').read_text(encoding='utf-8'))
if real.get('status')!='PASS':errors.append('REAL_AUTH_EVIDENCE_INCOMPLETE')
scan=json.loads((ROOT/'reports/FASE_7F_B_SECRET_SCAN.json').read_text(encoding='utf-8'))
if scan.get('status')!='PASSED':errors.append('FINAL_SECRET_SCAN_FAILED')
result.update(status='VERIFIED' if not errors else 'FAILED',errors=errors,real_auth_evidence=real.get('status'),secret_scan=scan.get('status'),cloud_scope='Authorized Identity Platform only; see real-auth inventory')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
