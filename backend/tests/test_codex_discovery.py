from backend.tests.test_codex_channel import channel,setup

def manifest(channel,**kw):
 value=dict(workspace_id='fixture',project_id='meu-gestor',target_device_id=channel[2]['device_id'],display_name='Synthetic fixture',mapping_version=1,mapping_fingerprint='a'*64,allowed_execution_modes=['READ_ONLY','WORKSPACE_WRITE'],enabled=False,binary_sha256='b'*64,model='fixture-model')
 value.update(kw);return value

def test_device_discovery_does_not_grant_or_activate(channel):
 app,c,d,send=channel
 r=send('codex/discovery',{'manifest':manifest(channel)});assert r.status_code==200,r.text
 with app.state.control.store.read() as repo:
  assert not repo.rows('execution_authorizations') and not repo.rows('jobs')
  assert not repo.rows('codex_workspaces')[0]['enabled']
 assert send('codex/poll',{}).status_code==403

def test_device_cannot_self_activate_workspace(channel):
 r=channel[3]('codex/discovery',{'manifest':manifest(channel,enabled=True)})
 assert r.status_code==403

def test_discovery_cannot_replace_owner_approved_mapping(channel):
 setup(channel)
 r=channel[3]('codex/discovery',{'manifest':manifest(channel,mapping_fingerprint='0'*64)})
 assert r.status_code==409
 with channel[0].state.control.store.read() as repo:
  row=repo.rows('codex_workspaces')[0]
  assert row['enabled'] and row['mapping_fingerprint']=='a'*64