"""Phase 7F audit: preserve 7E checks with explicitly authorized branch/remote."""
import contextlib,io,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'audit_workspace.py').read_text(encoding='utf-8-sig')
old="if git(ROOT,'remote','-v'): errors.append('REMOTE_CONFIGURED')"
new="""if git(ROOT,'remote').splitlines()!=['origin'] or git(ROOT,'remote','get-url','origin')!='https://github.com/danilo-programadorr/LUMA.git' or git(ROOT,'remote','get-url','--push','origin')!='https://github.com/danilo-programadorr/LUMA.git': errors.append('UNEXPECTED_REMOTE')"""
assert old in source
source=source.replace(old,new).replace("!='codex/fase-7e-adk-orchestration'","!='codex/fase-7f-remote-control-local-executor'")
output=io.StringIO()
with contextlib.redirect_stdout(output):
    try: exec(compile(source,str(ROOT/'audit_workspace.py'),'exec'),{'__file__':str(ROOT/'audit_workspace.py'),'__name__':'__audit__'})
    except SystemExit: pass
result=json.loads(output.getvalue())
for path in ('backend/migrations/v0001_initial.py','backend/migrations/v0002_trust_boundary.py','backend/migrations/v0003_conversation.py','backend/migrations/v0004_execution.py'):
    baseline=subprocess.check_output(['git','show','a2ec0c81f624b62bf3f8d8963188909be763060e:'+path])
    if baseline != (ROOT/path).read_bytes().replace(b'\r\n',b'\n'):
        result['errors'].append('MIGRATION_CHANGED:'+path)
result.update(date='2026-10-24',phase='7F-A',git_local_only=False,
    authorized_adaptations=['exact 7F branch','exact owner-configured origin URL','all four historical migrations compared with preflight baseline'])
result['status']='VERIFIED' if not result['errors'] else 'FAILED'
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(result['errors']))
