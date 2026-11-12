"""Workspace/profile invariants; no CLI/model involved."""
import hashlib,json,os
from pathlib import Path
import pytest

def profile(**kw):
 from backend.codex.contracts import ExecutionProfile
 return ExecutionProfile(workspace_id='fixture',mapping_version=1,mapping_fingerprint='a'*64,task_prompt='Corrigir soma no fixture sintético.',execution_mode='WORKSPACE_WRITE',allowed_paths=['src/calc.py'],**kw)

def test_profile_strict_and_bounded():
 from pydantic import ValidationError
 with pytest.raises(ValidationError):profile(max_duration=0)
 with pytest.raises(ValidationError):profile(max_changed_files=100)
 with pytest.raises(ValidationError):profile(arbitrary='authority')
 assert profile().network_policy=='MODEL_ONLY_TASK_OFFLINE'
@pytest.mark.parametrize('value',['../x','/x','C:/x','a/../x','a//x','a\\x','x:secret','CON','aux.txt','a/COM1.log','x.','x '])
def test_unsafe_relative_paths(value):
 from backend.codex.contracts import relative_path
 with pytest.raises(ValueError):relative_path(value)

def test_read_only_cannot_authorize_writes():
 from pydantic import ValidationError
 from backend.codex.contracts import ExecutionProfile
 with pytest.raises(ValidationError):
  ExecutionProfile(workspace_id='fixture',mapping_version=1,mapping_fingerprint='a'*64,task_prompt='analisar',execution_mode='READ_ONLY',allowed_paths=['src/x.py'])

def registry(tmp_path):
 from device_agent.codex_workspace import WorkspaceRegistry
 root=tmp_path/'managed';work=root/'fixture';work.mkdir(parents=True)
 (work/'src').mkdir();(work/'src/calc.py').write_text('value=1',encoding='utf8')
 return WorkspaceRegistry(tmp_path/'state',root),work

def test_registry_roundtrip_and_no_path_from_model(tmp_path):
 r,w=registry(tmp_path);entry=r.register('fixture','meu-gestor','a'*32,w,['READ_ONLY','WORKSPACE_WRITE'])
 assert 'canonical_root' not in r.public(entry)
 assert r.resolve('fixture','meu-gestor','a'*32,entry['mapping_fingerprint'],1)==w.resolve()
 with pytest.raises(ValueError,match='SCOPE'):r.resolve('fixture','other','a'*32,entry['mapping_fingerprint'],1)
 with pytest.raises(ValueError,match='SCOPE'):r.resolve('fixture','meu-gestor','b'*32,entry['mapping_fingerprint'],1)

def test_registry_unknown_changed_disabled(tmp_path):
 r,w=registry(tmp_path);entry=r.register('fixture','meu-gestor','a'*32,w,['READ_ONLY'])
 with pytest.raises(ValueError,match='UNKNOWN'):r.resolve('unknown','meu-gestor','a'*32,'a'*64,1)
 with pytest.raises(ValueError,match='CHANGED'):r.resolve('fixture','meu-gestor','a'*32,'0'*64,1)
 with pytest.raises(ValueError,match='CHANGED'):r.resolve('fixture','meu-gestor','a'*32,entry['mapping_fingerprint'],2)
 entry['enabled']=False;r.save(entry)
 with pytest.raises(ValueError,match='DISABLED'):r.resolve('fixture','meu-gestor','a'*32,entry['mapping_fingerprint'],1)

def test_registry_rejects_outside_and_root(tmp_path):
 r,w=registry(tmp_path)
 with pytest.raises(ValueError):r.register('outside','meu-gestor','a'*32,tmp_path,['READ_ONLY'])
 with pytest.raises(ValueError):r.register('root','meu-gestor','a'*32,w.parent,['READ_ONLY'])

def test_snapshots_and_scope_verification(tmp_path):
 from device_agent.codex_workspace import snapshot,verify_changes
 r,w=registry(tmp_path);before=snapshot(w)
 (w/'src/calc.py').write_text('value=2',encoding='utf8')
 result=verify_changes(before,snapshot(w),['src/calc.py'],1,256,'WORKSPACE_WRITE')
 assert result['modified_files']==['src/calc.py'];assert result['changed_files_count']==1
 with pytest.raises(ValueError,match='SCOPE'):verify_changes(before,snapshot(w),[],1,256,'READ_ONLY')
 with pytest.raises(ValueError,match='SCOPE'):verify_changes(before,snapshot(w),['src/calc.py'],1,1,'WORKSPACE_WRITE')

def test_delete_and_unapproved_creation_rejected(tmp_path):
 from device_agent.codex_workspace import snapshot,verify_changes
 r,w=registry(tmp_path);before=snapshot(w);(w/'src/calc.py').unlink()
 with pytest.raises(ValueError,match='SCOPE'):verify_changes(before,snapshot(w),['src/calc.py'],1,256,'WORKSPACE_WRITE')
 (w/'unapproved.txt').write_text('x')
 with pytest.raises(ValueError,match='SCOPE'):verify_changes(before,snapshot(w),['src/calc.py'],1,256,'WORKSPACE_WRITE')

def test_hardlinks_are_rejected(tmp_path):
 from device_agent.codex_workspace import snapshot
 r,w=registry(tmp_path);os.link(w/'src/calc.py',w/'src/alias.py')
 with pytest.raises(ValueError,match='ESCAPE'):snapshot(w)

def test_source_context_is_bounded_and_selected(tmp_path):
 from device_agent.codex_workspace import read_context
 r,w=registry(tmp_path)
 assert 'value=1' in read_context(w,['src/calc.py'],128)
 with pytest.raises(ValueError):read_context(w,['../outside'],128)
 with pytest.raises(ValueError,match='LIMIT'):read_context(w,['src/calc.py'],2)