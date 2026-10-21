import json
import secrets
from dataclasses import replace
from datetime import timedelta
import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select,update,delete
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.trust import Control
from backend.app.trust_data import grant,verify,RUNTIME_CAPS,NEW_ADMIN_CAPS
from backend.app.models import now
from backend.app.database import TABLES,version,engine_for,Repository,Store
from backend.app.errors import Fault
from backend.app.knowledge import KnowledgeClient
from backend.app.model_contracts import ModelDecision,AgentExecutionContext,SecretRef,model_input,sanitized_worker_environment
from backend.migrate import migrate
from backend.tests.test_foundation import transport

@pytest.fixture
def cfg(tmp_path):
    url='sqlite:///'+(tmp_path/'trust.db').as_posix();migrate(url)
    return Settings(secrets.token_urlsafe(32),secrets.token_urlsafe(32),runtime_token=secrets.token_urlsafe(32),
        admin_confirmation_token=secrets.token_urlsafe(32),database_url=url)

@pytest.fixture
def api(cfg):
    app=create_app(cfg,KnowledgeClient(cfg,httpx.MockTransport(transport)))
    with TestClient(app,base_url='http://127.0.0.1',headers={'Authorization':'Bearer '+cfg.token}) as client: yield client

def headers(cfg,runtime=False): return {'Authorization':'Bearer '+(cfg.runtime_token if runtime else cfg.token),'Idempotency-Key':secrets.token_hex(12)}
def session(api):
    response=api.post('/v1/admin/sessions',json={'project_id':'meu-gestor'},headers={'Idempotency-Key':secrets.token_hex(12)})
    assert response.status_code==200,response.text
    return response.json()['session_id']
def proposal(sid,**extra): return dict(session_id=sid,tool_id='knowledge',capability='knowledge.read',intent='read context',parameters={},**extra)
def revoke(control,principal,cap,status='REVOKED'):
    with control.store.transaction() as repo:
        for g in repo.rows('grants'):
            if g['principal_id']==principal and g['capability']==cap:
                g['status']=status;repo.put('grants',g['grant_id'],g)

@pytest.mark.parametrize('path',['state','grants','tools','audit','audit/verify','approvals','sessions','retention/preview'])
def test_runtime_cannot_read_admin(api,cfg,path):
    assert api.get('/v1/admin/'+path,headers=headers(cfg,True)).status_code==403

@pytest.mark.parametrize('path,body',[
    ('grants',{'principal_id':'luma-runtime','capability':'admin.state.manage'}),
    ('state',{'state':'RUNNING','confirmation':'UNLOCK_LUMA'}),
    ('tools/knowledge/enable',{}),('approvals/x/decision',{'decision':'APPROVE'}),
    ('principals/luma-runtime',{'principal_type':'HUMAN_OWNER'})])
def test_runtime_cannot_mutate_admin(api,cfg,path,body):
    h=headers(cfg,True);h['X-Admin-Confirmation']=cfg.admin_confirmation_token
    assert api.post('/v1/admin/'+path,json=body,headers=h).status_code==403

def test_separate_auth(api,cfg):
    assert api.get('/v1/runtime/status').status_code==403
    assert api.get('/v1/runtime/status',headers=headers(cfg,True)).status_code==200
    assert api.get('/v1/knowledge/query',headers=headers(cfg,True)).status_code==403
    assert api.get('/v1/runtime/status',headers={'Authorization':'Bearer '+cfg.knowledge_token}).status_code==401
    request=api.build_request('GET','/v1/runtime/status');del request.headers['Authorization']
    assert api.send(request).status_code==401
    c=api.app.state.control
    with c.store.transaction() as repo:
        p=repo.get('principals','luma-runtime');p['status']='DISABLED';repo.put('principals','luma-runtime',p)
    assert api.get('/v1/runtime/status',headers=headers(cfg,True)).status_code==403

@pytest.mark.parametrize('field,value',[('principal_id','local-owner'),('origin_type','HUMAN_DIRECT'),('origin_id','local-owner'),
    ('approved',True),('grant','admin.state.manage'),('unlock',True),('permission_override',True),('project_id','other')])
def test_origin_mass_assignment(api,cfg,field,value):
    body=proposal(session(api));body[field]=value
    assert api.post('/v1/runtime/actions/propose',json=body,headers=headers(cfg,True)).status_code in (400,403)

def test_proposal_no_execution_and_replay(api,cfg):
    sid=session(api);body=proposal(sid);h=headers(cfg,True)
    first=api.post('/v1/runtime/actions/propose',json=body,headers=h)
    assert first.status_code==200,first.text
    a=first.json();assert a['origin_type']=='MODEL_PROPOSED' and a['status']=='PROPOSED'
    assert api.post('/v1/runtime/actions/propose',json=body,headers=h).json()==a
    assert api.post('/v1/runtime/actions/propose',json={**body,'intent':'changed'},headers=h).status_code==409
    read=api.get('/v1/runtime/actions/'+a['action_id'],params={'session_id':sid},headers=headers(cfg,True))
    assert read.json()==a
    other=session(api)
    assert api.get('/v1/runtime/actions/'+a['action_id'],params={'session_id':other},headers=headers(cfg,True)).status_code==403
    external={**body,'tool_id':'google_calendar','capability':'calendar.create'}
    denied=api.post('/v1/runtime/actions/propose',json=external,headers=headers(cfg,True)).json()
    assert denied['status']=='DENIED' and denied['approval_requirement']=='DENY'
    assert api.get('/v1/admin/actions/'+a['action_id']).status_code==200
    revoke(api.app.state.control,'luma-runtime','runtime.actions.propose')
    assert api.post('/v1/runtime/actions/propose',json=body,headers=h).status_code==403

@pytest.mark.parametrize('mutation',['expired','revoked','human_scope','runtime_scope','human_revocation','tool','project','lock','closed','wrong_runtime'])
def test_effective_intersection(api,cfg,mutation):
    sid=session(api);c=api.app.state.control
    with c.store.transaction() as repo:
        if mutation in ('expired','revoked'):
            g=next(g for g in repo.rows('grants') if g['principal_id']=='luma-runtime' and g['capability']=='knowledge.read')
            if mutation=='expired': g['expires_at']=(now()-timedelta(seconds=1)).isoformat()
            else: g['status']='REVOKED'
            repo.put('grants',g['grant_id'],g)
        elif mutation in ('human_scope','runtime_scope'):
            pid='local-owner' if mutation=='human_scope' else 'luma-runtime';p=repo.get('principals',pid);p['project_scopes']=[];repo.put('principals',pid,p)
        elif mutation=='human_revocation':
            repo.add('revocations','synthetic',dict(principal_id='local-owner',capability='knowledge.read',project_id='meu-gestor',tool_id='knowledge'))
        elif mutation=='tool':
            t=repo.get('tools','knowledge');t['enabled']=False;repo.put('tools','knowledge',t)
        elif mutation=='project':
            p=repo.get('projects','meu-gestor');p['enabled']=False;repo.put('projects','meu-gestor',p)
        elif mutation=='lock':
            s=repo.get('system_state','global');s['state']='LOCKED';repo.put('system_state','global',s)
        else:
            s=repo.get('sessions',sid);s['status' if mutation=='closed' else 'runtime_principal_id']='CLOSED' if mutation=='closed' else 'another-runtime';repo.put('sessions',sid,s)
    response=api.post('/v1/runtime/knowledge/query',json={'session_id':sid,'project_id':'meu-gestor','query':'test'},headers=headers(cfg,True))
    assert response.status_code==403,response.text

def test_json_roles_and_caps_are_not_authority(api,cfg):
    c=api.app.state.control
    revoke(c,'local-owner','admin.state.manage')
    with c.store.transaction() as repo:
        p=repo.get('principals','local-owner');p['roles']=['OWNER'];p['capabilities']=['admin.state.manage'];repo.put('principals','local-owner',p)
    assert api.post('/v1/admin/state',json={'state':'LOCKED'},headers=headers(cfg)).status_code==403

def test_grants_learning_retention(api,cfg):
    sid=session(api);body={'principal_id':'luma-runtime','capability':'runtime.learning.propose','project_id':'meu-gestor'}
    assert api.post('/v1/admin/grants',json={**body,'principal_id':'local-owner'},headers=headers(cfg)).status_code==403
    assert api.post('/v1/admin/grants',json={**body,'capability':'admin.grants.manage'},headers=headers(cfg)).status_code==403
    g=api.post('/v1/admin/grants',json=body,headers=headers(cfg));assert g.status_code==200,g.text
    data=dict(session_id=sid,source='synthetic',claim='untrusted proposal',evidence=['synthetic reference'],confidence='LOW')
    candidate=api.post('/v1/runtime/learning/propose',json=data,headers=headers(cfg,True));assert candidate.status_code==200,candidate.text
    assert candidate.json()['status']=='PROPOSED'
    assert api.post('/v1/admin/learning/'+candidate.json()['candidate_id']+'/status',json={'status':'VALIDATED'},headers=headers(cfg)).status_code==403
    assert api.post('/v1/admin/grants/'+g.json()['grant_id']+'/revoke',headers=headers(cfg)).status_code==200
    assert api.post('/v1/runtime/learning/propose',json=data,headers=headers(cfg,True)).status_code==403
    preview=api.get('/v1/admin/retention/preview');assert preview.status_code==200
    assert len(preview.json())==5 and all(r['mode']=='NO_AUTO_DELETE' and r['eligible_for_deletion']==0 for r in preview.json())

@pytest.mark.parametrize('secret_kind',['token','runtime_token','knowledge_token','admin_confirmation_token'])
def test_secrets_not_persisted_or_in_context(api,cfg,secret_kind):
    secret=getattr(cfg,secret_kind);body=proposal(session(api));body['intent']=secret
    assert api.post('/v1/runtime/actions/propose',json=body,headers=headers(cfg,True)).status_code==400
    with pytest.raises(Fault): model_input(api.app.state.control,user_message=secret,project_id='meu-gestor')
    with api.app.state.control.store.read() as repo:
        assert secret not in json.dumps({t:repo.rows(t) for t in TABLES})
    assert secret not in api.get('/v1/admin/audit').text

def test_contracts_environment(cfg):
    env={'LUMA_OWNER_TOKEN':cfg.token,'LUMA_RUNTIME_TOKEN':cfg.runtime_token,'LUMA_ADMIN_CONFIRM_TOKEN':cfg.admin_confirmation_token,
        'LUMA_KNOWLEDGE_TOKEN':cfg.knowledge_token,'DB_PASSWORD':'synthetic','PATH':'untrusted'}
    assert sanitized_worker_environment(env)=={}
    assert sanitized_worker_environment(env,runtime_credential=cfg.runtime_token)=={'LUMA_RUNTIME_TOKEN':cfg.runtime_token}
    with pytest.raises(ValueError): sanitized_worker_environment(env,runtime_credential=cfg.token)
    assert SecretRef(secret_id='calendar.future').secret_id=='calendar.future'
    for field in ('approved','grant','unlock','identity_override','permission_override','admin_capability'):
        with pytest.raises(ValueError): ModelDecision(assistant_message='text',intent='test',confidence=.5,**{field:True})
    with pytest.raises(ValueError): AgentExecutionContext(agent_id='future',runtime_principal='local-owner',project_id='meu-gestor',allowed_capabilities=(),session_id='s',correlation_id='c')

@pytest.mark.parametrize('tamper',['edit','delete','anchor'])
def test_audit_tamper(cfg,tamper):
    c=Control(cfg)
    with c.store.read() as repo: assert verify(repo)['sequence']==1
    with c.store.engine.begin() as conn:
        if tamper=='delete': conn.execute(delete(TABLES['audit_events']))
        elif tamper=='anchor': conn.execute(delete(TABLES['audit_chain']))
        else:
            data=conn.execute(select(TABLES['audit_events'].c.data)).scalar_one();data['result']='FORGED'
            conn.execute(update(TABLES['audit_events']).values(data=data))
    with c.store.read() as repo:
        with pytest.raises(Fault,match='AUDIT_INTEGRITY'): verify(repo)
    with pytest.raises(Fault,match='AUDIT_INTEGRITY'): c.http_event(c.principal(),None,'TEST','OK','test')
    c.close()

def test_migrate_v1_with_data(tmp_path):
    from backend.migrations.v0001_initial import upgrade
    path=tmp_path/'v1.db';url='sqlite:///'+path.as_posix();engine=engine_for(url)
    old={}
    with engine.begin() as conn:
        upgrade(conn);repo=Repository(conn)
        owner=dict(principal_id='local-owner',principal_type='LOCAL_OWNER',display_name='Owner',roles=['OWNER'],project_scopes=['meu-gestor'],
            capabilities=['knowledge.read','admin.sessions.manage'],approval_level='OWNER_SCOPED',status='ACTIVE')
        repo.add('principals','local-owner',owner)
        for table in ('projects','system_state','actions','approvals','sessions','revocations','learning','idempotency'):
            row=dict(principal_id='local-owner',project_id='meu-gestor',status='SYNTHETIC',marker=table)
            if table=='sessions': row['session_id']='s'
            key='s' if table=='sessions' else 'synthetic'
            repo.add(table,key,row);old[table]=(key,row)
        event=dict(event_id='legacy',event_type='SYNTHETIC',result='OK');repo.add('audit_events','legacy',event)
    engine.dispose()
    assert migrate(url) and migrate(url) is False
    store=Store(url)
    with store.read() as repo:
        for table,(key,row) in old.items():
            actual=repo.get(table,key)
            assert all(actual[k]==v for k,v in row.items()),table
        owner=repo.get('principals','local-owner');assert owner['principal_type']=='HUMAN_OWNER'
        assert {g['capability'] for g in repo.rows('grants') if g['principal_id']=='local-owner'}=={'knowledge.read','admin.sessions.manage',*NEW_ADMIN_CAPS}
        assert {g['capability'] for g in repo.rows('grants') if g['principal_id']=='luma-runtime'}==set(RUNTIME_CAPS)
        assert verify(repo)['sequence']==1
    store.close()

def test_runtime_revocation_during_io(api,cfg):
    sid=session(api);c=api.app.state.control;client=api.app.state.service.client if hasattr(api.app.state.service,'client') else None
    service=api.app.state.service;original=service.query
    def race(*args,**kwargs):
        result=original(*args,**kwargs);revoke(c,'local-owner','knowledge.read');return result
    service.query=race
    response=api.post('/v1/runtime/knowledge/query',json=dict(session_id=sid,project_id='meu-gestor',query='test'),headers=headers(cfg,True))
    assert response.status_code==403 and 'results' not in response.json()


def test_backup_schema2_and_chain(cfg,tmp_path):
    import sqlite3,shutil
    from contextlib import closing
    from backend.maintenance import backup
    c=Control(cfg);p=c.principal()
    c.mutate(p,'session',{'project_id':'meu-gestor'},'backup-session','test')
    snapshot=backup(cfg.database_url);target=tmp_path/'restored.db';shutil.copyfile(snapshot,target)
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert connection.execute('SELECT version FROM schema_version').fetchone()[0]==2
    clone=Control(replace(cfg,database_url='sqlite:///'+target.as_posix()))
    with c.store.read() as original,clone.store.read() as restored:
        for table in TABLES: assert original.rows(table)==restored.rows(table),table
        assert verify(original)==verify(restored)
    clone.close();c.close()

def test_precedence_and_grant_scope(api,cfg):
    c=api.app.state.control;p=c.principal()
    with c.store.transaction() as repo:
        s=repo.get('system_state','global');s['state']='LOCKED';repo.put('system_state','global',s)
        t=repo.get('tools','knowledge');t['enabled']=False;repo.put('tools','knowledge',t)
        repo.add('revocations','stop',dict(principal_id=p.principal_id,project_id='meu-gestor',tool_id='knowledge',capability='knowledge.read'))
    with c.store.read() as repo:
        with pytest.raises(Fault,match='LUMA_LOCKED'): c._check(repo,p,'meu-gestor','knowledge','knowledge.read')
    with c.store.transaction() as repo:
        s=repo.get('system_state','global');s['state']='RUNNING';repo.put('system_state','global',s)
    with c.store.read() as repo:
        with pytest.raises(Fault,match='CAPABILITY_DENIED'): c._check(repo,p,'meu-gestor','knowledge','knowledge.read')

def test_migration_failure_rollback(tmp_path):
    from backend.migrations.v0001_initial import upgrade
    path=tmp_path/'rollback.db';url='sqlite:///'+path.as_posix();engine=engine_for(url)
    with engine.begin() as conn:
        upgrade(conn);repo=Repository(conn)
        repo.add('principals','local-owner',dict(principal_id='local-owner',capabilities=[],project_scopes=[]))
        repo.add('principals','unsupported',dict(principal_id='unsupported'))
    engine.dispose()
    with pytest.raises(ValueError,match='UNSUPPORTED_LEGACY_PRINCIPAL'): migrate(url)
    from sqlalchemy import inspect
    engine=engine_for(url)
    with engine.connect() as conn:
        assert conn.execute(select(version.c.version)).scalar_one()==1
        assert 'grants' not in inspect(conn).get_table_names()
    engine.dispose()
