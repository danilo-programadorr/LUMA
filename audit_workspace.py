"""Read-only verification of delivery and external evidence; writes no external files."""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BRAIN=Path(r'D:\cerebro do gestor')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def git(path,*args):
    return subprocess.check_output(['git','-c','safe.directory='+path.as_posix(),'-C',str(path),*args],text=True).strip()

errors=[]
counts={}
for filename,skip in [('FASE_6_HASHES_ENTREGA.json',set()),('FASE_5F_HASHES_ENTREGA.json',{'PLANS.md'})]:
    entries=read(BRAIN/'reports'/filename)['files']; counts[filename]=len(entries)-len(skip)
    for item in entries:
        if item['path'] in skip: continue
        if sha(BRAIN/item['path'])!=item['sha256']: errors.append('EXTERNAL_CHANGED:'+item['path'])
source=read(BRAIN/'reports/FASE_3_FONTE_INICIAL.json')
for item in source['files']:
    if sha(BRAIN/'source/meu_gestor'/item['path'])!=item['sha256']: errors.append('SOURCE_CHANGED:'+item['path'])
counts['source_files']=len(source['files'])
source_repo=BRAIN/'source/meu_gestor'
head=git(source_repo,'rev-parse','HEAD')
if head!=source['head'] or git(source_repo,'status','--porcelain'): errors.append('SOURCE_GIT_CHANGED')
if git(ROOT,'remote','-v'): errors.append('REMOTE_CONFIGURED')
patterns={
    'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'google_key':r'AIza[0-9A-Za-z_-]{30,}',
    'github_token':r'gh[pousr]_[0-9A-Za-z]{25,}',
    'jwt':r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}'
}
scanned=0
for folder in ('backend','contracts','docs'):
    for file in (ROOT/folder).rglob('*'):
        if not file.is_file() or '__pycache__' in file.parts: continue
        content=file.read_text(encoding='utf-8-sig'); scanned+=1
        for name,pattern in patterns.items():
            if re.search(pattern,content): errors.append('SENSITIVE_PATTERN:'+file.relative_to(ROOT).as_posix()+':'+name)
for file in (ROOT/'backend/app').glob('*.py'):
    tree=ast.parse(file.read_text(encoding='utf8'))
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): names=[a.name for a in node.names]
        elif isinstance(node,ast.ImportFrom): names=[node.module or '']
        else: continue
        if any(n.startswith(('google','openai','knowledge_api','subprocess')) for n in names):
            errors.append('FORBIDDEN_RUNTIME_IMPORT:'+file.name)
    if str(BRAIN).lower() in file.read_text(encoding='utf8').lower(): errors.append('DIRECT_CORPUS_PATH:'+file.name)
finance=Path(r'D:\projetos\meu_gestor_financeiro')
finance_state={'access':'read-only git metadata; no before-baseline claimed'}
if (finance/'.git').exists():
    finance_state.update(head=git(finance,'rev-parse','HEAD'),working_tree_clean=not bool(git(finance,'status','--porcelain')))
# Durable control-plane delivery checks; migrations must be staged/tracked before final audit.
tracked=git(ROOT,'ls-files').splitlines()
if any(p.startswith(('runtime/','.venv/','__pycache__/','.pytest_cache/')) or p.endswith(('.db','.sqlite','.db-wal','.db-shm')) for p in tracked):
    errors.append('RUNTIME_OR_DATABASE_TRACKED')
for ignored in ('runtime/luma.db','.venv/pyvenv.cfg','backend/app/__pycache__/example.pyc'):
    if not git(ROOT,'check-ignore',ignored): errors.append('RUNTIME_NOT_IGNORED:'+ignored)
if 'backend/migrations/v0001_initial.py' not in tracked: errors.append('MIGRATION_NOT_VERSIONED')
if git(ROOT,'branch','--show-current')!='codex/fase-7b-persistencia-control-plane': errors.append('WRONG_PHASE_BRANCH')
for requirement in (ROOT/'backend/requirements/lock.txt').read_text(encoding='utf-8-sig').splitlines():
    if requirement.lower().startswith(('google-','google_','gemini','openai','google-adk')): errors.append('FORBIDDEN_SDK_DEPENDENCY')
for name in ('package.json','next.config.js','next.config.ts'):
    if (ROOT/name).exists(): errors.append('UNEXPECTED_FRONTEND')
for file in [ROOT/'.env.example',ROOT/'README.md']:
    for label,pattern in patterns.items():
        if re.search(pattern,file.read_text(encoding='utf8')): errors.append('SENSITIVE_PATTERN:'+file.name+':'+label)
result={'date':'2026-10-21','verifier':'Codex','status':'VERIFIED' if not errors else 'FAILED',
    'source_commit':head,'brain_unchanged_hash_counts':counts,'runtime_and_contract_files_scanned':scanned,
    'baseline_7a':'cb06235a3e7b53d097d4851d7cae34130e3c5b38','migrations_versioned':'backend/migrations/v0001_initial.py' in tracked,'runtime_ignored':True,'git_local_only':True,'production_verified':False,'finance_repository':finance_state,'errors':errors}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
