from backend.tests.test_codex_adapter import adapter
from backend.app.control import digest
from device_agent.codex_workspace import snapshot,fingerprint

def test_source_change_after_proposal_blocks_before_context_or_process(tmp_path):
 a,f,j,w=adapter(tmp_path)
 j['profile']['snapshot_hash']=fingerprint(snapshot(w));j['profile_hash']=digest(j['profile'])
 (w/'new-human-file.txt').write_text('synthetic private fixture canary')
 result=a.execute(j,lambda:True)
 assert result.code=='CODEX_WORKSPACE_CHANGED' and f.calls==0