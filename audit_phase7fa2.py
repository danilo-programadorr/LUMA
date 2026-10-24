"""Integrity and executable evidence audit for Phase 7F-A2."""
import ast,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parent
base=subprocess.run([sys.executable,str(ROOT/'audit_phase7f.py')],cwd=ROOT,capture_output=True,text=True)
result=json.loads(base.stdout)
errors=list(result['errors'])
runtime_files=('backend/runtime_processor.py','backend/local_runtime_app.py','backend/local_dev_transport.py','backend/remote_protocol.py')
for file in runtime_files:
    tree=ast.parse((ROOT/file).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
        for name in names:
            if name.startswith(('sqlalchemy','psycopg')) or any(name.endswith(x) for x in ('app.database','app.control','app.trust','app.execution','control_plane_app','control_plane_tasks')):
                errors.append('RUNTIME_AUTHORITY_IMPORT:'+file+':'+name)
reports=('FASE_7F_A2_FINAL_TESTES.xml','FASE_7F_A2_BOUNDARY_FINAL_TESTES.xml','FASE_7F_A2_POSTGRES_TESTES.xml')
unique=set();runs={}
for name in reports:
    root=ET.parse(ROOT/'reports'/name).getroot()
    cases=list(root.iter('testcase'));failed=list(root.iter('failure'))+list(root.iter('error'));skipped=list(root.iter('skipped'))
    runs[name]=dict(tests=len(cases),failures=len(failed),skipped=len(skipped))
    if failed or skipped:errors.append('TEST_EVIDENCE_NOT_GREEN:'+name)
    unique.update((case.attrib.get('classname'),case.attrib['name']) for case in cases)
if len(unique)<532:errors.append('INSUFFICIENT_TEST_COVERAGE')
result.update(phase='7F-A2',status='VERIFIED' if not errors else 'FAILED',errors=errors,
    runtime_authority_import_check='PASSED' if not any('RUNTIME_AUTHORITY_IMPORT' in e for e in errors) else 'FAILED',
    evidence_runs=runs,unique_tests=len(unique),public_or_cloud_operation_tested=False,
    boundary_evidence='Clean-process tests and local ADK with synthetic model; no Gemini network or Codex execution')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
