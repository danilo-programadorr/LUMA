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
for folder in ('backend','contracts','docs','reports'):
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
        if any(n.startswith(('google','openai','knowledge_api')) or (n.startswith('subprocess') and file.name not in ('model_provider.py','adk_bridge.py')) for n in names):
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
for ignored in ('runtime/luma.db','runtime/backups/example.db','.venv/pyvenv.cfg','backend/app/__pycache__/example.pyc'):
    if not git(ROOT,'check-ignore',ignored): errors.append('RUNTIME_NOT_IGNORED:'+ignored)
for migration in ('backend/migrations/v0001_initial.py','backend/migrations/v0002_trust_boundary.py','backend/migrations/v0003_conversation.py','backend/migrations/v0004_execution.py'):
    if migration not in tracked: errors.append('MIGRATION_NOT_VERSIONED:'+migration)
if git(ROOT,'hash-object','backend/migrations/v0001_initial.py')!=git(ROOT,'rev-parse','ada01cc344b9307f115069b580a52f1c55022145:backend/migrations/v0001_initial.py'):
    errors.append('HISTORICAL_MIGRATION_CHANGED')
if git(ROOT,'branch','--show-current')!='codex/fase-7e-adk-orchestration': errors.append('WRONG_PHASE_BRANCH')
for requirement in (ROOT/'backend/requirements/lock.txt').read_text(encoding='utf-8-sig').splitlines():
    package=requirement.split('==')[0].lower()
    if package.startswith(('google-','google_','gemini','openai')) and package not in ('google-genai','google-auth'): errors.append('FORBIDDEN_SDK_DEPENDENCY')
for name in ('package.json','next.config.js','next.config.ts'):
    if (ROOT/name).exists(): errors.append('UNEXPECTED_FRONTEND')
for file in [ROOT/'.env.example',ROOT/'README.md']:
    for label,pattern in patterns.items():
        if re.search(pattern,file.read_text(encoding='utf8')): errors.append('SENSITIVE_PATTERN:'+file.name+':'+label)
for migration in ('backend/migrations/v0001_initial.py','backend/migrations/v0002_trust_boundary.py'):
    if git(ROOT,'hash-object',migration)!=git(ROOT,'rev-parse','b9c435c6c5d55833c9027a74bc45c81c0da57741:'+migration):
        errors.append('HISTORICAL_MIGRATION_CHANGED:'+migration)
import importlib.metadata
sdk_versions={}
for name in ('google-genai','google-generativeai','google-adk'):
    try: sdk_versions[name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: sdk_versions[name]=None
if not sdk_versions['google-genai'] or sdk_versions['google-generativeai'] or sdk_versions['google-adk']:
    errors.append('MODEL_DEPENDENCY_BOUNDARY')
for file in (ROOT/'backend/model_worker').glob('*.py'):
    tree=ast.parse(file.read_text(encoding='utf8'))
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): names=[a.name for a in node.names]
        elif isinstance(node,ast.ImportFrom): names=[node.module or '']
        else: continue
        if any(n.startswith(('sqlalchemy','backend.app.database','backend.app.control','backend.app.trust','knowledge_api','google.adk','google.generativeai')) for n in names):
            errors.append('WORKER_FORBIDDEN_IMPORT:'+file.name)
adk_python=ROOT/'runtime/adk-venv/Scripts/python.exe'
try:
    adk_versions=json.loads(subprocess.check_output([str(adk_python),'-c',"import importlib.metadata as m,json; print(json.dumps({k:m.version(k) for k in ('google-adk','google-genai')}))"],text=True))
    if adk_versions!={'google-adk':'2.12.0','google-genai':'2.32.0'}:errors.append('ADK_VERSION_MISMATCH')
except Exception:
    adk_versions={};errors.append('ADK_RUNTIME_UNAVAILABLE')
for migration in ('backend/migrations/v0001_initial.py','backend/migrations/v0002_trust_boundary.py','backend/migrations/v0003_conversation.py'):
    if git(ROOT,'hash-object',migration)!=git(ROOT,'rev-parse','c461a8f69bddb6c2ead1cb21f69f3a17bd1d378f:'+migration):errors.append('BASELINE_MIGRATION_CHANGED:'+migration)
# Authorized action-mode protocol; generation settings remain pinned to validated 7D.
reviewed_action_protocol={'backend/model_worker/adapter.py': '1d0991c54d03c67f1272ab1da76363edcfde93ab557fa51fe9d337ae4d5074fe', 'backend/app/model_contracts.py': '78299113cc7a6f6f037a19b8537d1f36c55401ab5a6c1bc7008cee8e06a77a20', 'backend/app/model_provider.py': '9a44844416f534cb5fa156bd6b148be93af4940664d6c71ff389959b0c946c03'}
for file,expected in reviewed_action_protocol.items():
    if sha(ROOT/file)!=expected:errors.append('REVIEWED_ACTION_PROTOCOL_CHANGED:'+file)
for file in ('backend/model_worker/worker.py','backend/model_worker/system_instruction.txt','backend/app/model_config.py','backend/requirements/lock.txt'):
    if git(ROOT,'hash-object',file)!=git(ROOT,'rev-parse','c461a8f69bddb6c2ead1cb21f69f3a17bd1d378f:'+file):errors.append('VALIDATED_MODEL_BOUNDARY_CHANGED:'+file)
result={'adk_runtime_versions':adk_versions,'date':'2026-10-23','verifier':'Codex','status':'VERIFIED' if not errors else 'FAILED',
    'sdk_versions':sdk_versions,'source_commit':head,'brain_unchanged_hash_counts':counts,'runtime_and_contract_files_scanned':scanned,
    'baseline_7a':'cb06235a3e7b53d097d4851d7cae34130e3c5b38','migrations_versioned':'backend/migrations/v0001_initial.py' in tracked,'runtime_ignored':True,'git_local_only':True,'production_verified':False,'finance_repository':finance_state,'errors':errors}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
