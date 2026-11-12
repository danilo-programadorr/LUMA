import json,secrets
from types import SimpleNamespace
import pytest
from backend.tests.test_codex_channel import channel
from backend.tests.device_support import HEADERS
from backend.tests.test_codex_adapter import FakeRunner
from device_agent.codex_adapter import CodexExecutorAdapter
from device_agent.codex_workspace import WorkspaceRegistry

def test_prepare_fixture_refuses_human_or_unknown_content(tmp_path):
 from device_agent.codex_agent import prepare_fixture
 root=tmp_path/'fixture';root.mkdir();(root/'human.txt').write_text('human')
 with pytest.raises(ValueError,match='NOT_OWNED'):prepare_fixture(root,'read')
 assert (root/'human.txt').read_text()=='human'

def test_prepare_fixture_stages_and_no_dependencies(tmp_path):
 from device_agent.codex_agent import prepare_fixture
 root=tmp_path/'fixture';prepare_fixture(root,'read');assert 'return a+b' in (root/'src/calc.py').read_text()
 prepare_fixture(root,'write');assert 'return a-b' in (root/'src/calc.py').read_text()
 assert (root/'.git/HEAD').read_text().strip()=='ref: refs/heads/codex-acceptance'
 assert not (root/'.git/refs/heads/codex-acceptance').exists()

def test_agent_without_real_gate_does_not_claim():
 from device_agent.codex_agent import CodexAgent
 client=SimpleNamespace(signed=lambda *args:pytest.fail('claim before gate'),identity=SimpleNamespace(binding=lambda:('a'*32,'')))
 adapter=SimpleNamespace(real_enabled=False,synthetic=False)
 assert CodexAgent(client,adapter,'a'*64,['fixture']).once()['status']=='CODEX_REAL_GATE_REQUIRED'

def test_fake_adapter_full_signed_pipeline_and_delivery_recovery(channel,tmp_path):
 from device_agent.codex_agent import CodexAgent
 app,c,d,send=channel
 work=tmp_path/'managed/fixture';(work/'src').mkdir(parents=True);(work/'src/calc.py').write_text('value=1\n')
 binary=tmp_path/'fake.exe';binary.write_bytes(b'FAKE')
 import hashlib
 sha=hashlib.sha256(binary.read_bytes()).hexdigest()
 registry=WorkspaceRegistry(tmp_path/'mapping',tmp_path/'managed')
 entry=registry.register('fixture','meu-gestor',d['device_id'],work,['WORKSPACE_WRITE'],binary_sha256=sha,model='fixture-model')
 manifest=registry.public(entry);manifest['enabled']=False
 assert send('codex/discovery',{'manifest':manifest}).status_code==200
 assert c.post('/v1/codex/devices/'+d['device_id']+'/grant',headers=HEADERS,json={'enabled':True,'confirmation':'CODEX_EXECUTION_ONE_SHOT_ONLY'}).status_code==200
 manifest['enabled']=True
 assert c.post('/v1/codex/workspaces',headers=HEADERS,json={'manifest':manifest,'confirmation':'APPROVE_CODEX_WORKSPACE'}).status_code==200
 profile=dict(snapshot_hash=entry['snapshot_hash'],workspace_id='fixture',mapping_version=1,mapping_fingerprint=entry['mapping_fingerprint'],task_prompt='Corrigir fixture',execution_mode='WORKSPACE_WRITE',allowed_paths=['src/calc.py'],binary_sha256=sha,model='fixture-model')
 t=c.post('/v1/tasks',headers=HEADERS,json=dict(project_id='meu-gestor',task_type='ACTION_ORIENTED',input='Corrigir fixture',executor='CODEX',codex_profile=profile,target_device_id=d['device_id'],idempotency_key=secrets.token_hex(12))).json()
 assert c.post('/v1/tasks/'+t['task_id']+'/decision',headers=HEADERS,json={'decision':'APPROVE','proposal_hash':t['proposal_hash']}).status_code==200
 from device_agent.client import ChannelError
 class Client:
  identity=SimpleNamespace(binding=lambda:(d['device_id'],''))
  uncertain=True
  def signed(self,op,body):
   r=send(op,body)
   if r.status_code!=200:raise ChannelError(r.json()['error']['code'])
   if op=='codex/result' and self.uncertain:
    self.uncertain=False;raise ChannelError('DEVICE_NETWORK_UNAVAILABLE')
   return r.json()
 fake=FakeRunner(work);adapter=CodexExecutorAdapter(registry,tmp_path/'state',binary,runner=fake,validator=lambda *args:True)
 agent=CodexAgent(Client(),adapter,sha,['fixture'])
 assert agent.once()['status']=='DELIVERY_PENDING'
 assert fake.calls==1 and adapter.journal.pending()
 assert agent.once()['recovered']==1 and not adapter.journal.pending() and fake.calls==1
 assert c.get('/v1/tasks/'+t['task_id'],headers=HEADERS).json()['status']=='COMPLETED'