import concurrent.futures
import json
import logging
import secrets
import shutil
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect,select,update
from backend.app.config import Settings
from backend.app.control import Control,stamp
from backend.app.database import Store,TABLES,version,database_path,engine_for
from backend.app.errors import Fault
from backend.app.main import create_app
from backend.app.models import now
from backend.migrate import migrate


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    folder=tmp_path_factory.mktemp('schema-template')
    path=folder/'template.db'
    assert migrate('sqlite:///'+path.as_posix())
    return path


@pytest.fixture
def cfg(tmp_path,template):
    path=tmp_path/'test.db';shutil.copyfile(template,path)
    return Settings(secrets.token_urlsafe(32),secrets.token_urlsafe(32),
        database_url='sqlite:///'+path.as_posix(),admin_confirmation_token=secrets.token_urlsafe(32))


@pytest.fixture
def api(cfg):
    app=create_app(cfg)
    with TestClient(app,base_url='http://127.0.0.1',headers={'Authorization':'Bearer '+cfg.token}) as client:
        yield client


def post(api,path,body=None,key=None,confirmation=None):
    headers={'Idempotency-Key':key or secrets.token_hex(16)}
    if confirmation: headers['X-Admin-Confirmation']=confirmation
    return api.post('/v1/admin/'+path,json=body,headers=headers)


def action(api):
    r=post(api,'actions',{'project_id':'meu-gestor','tool_id':'google_calendar','capability':'calendar.delete',
        'intent':'synthetic cancellation','parameters':{'event_id':'synthetic-reference'}})
    assert r.status_code==200,r.text
    return r.json()


def approve(api,cfg,a,key=None):
    return post(api,'approvals/'+a['action_id']+'/decision',{'decision':'APPROVE','scope':a['scope'],
        'confirmation':'HUMAN_DECISION'},key=key,confirmation=cfg.admin_confirmation_token)


def test_migration_bootstrap(cfg,tmp_path):
    assert migrate(cfg.database_url) is False
    missing='sqlite:///'+(tmp_path/'missing.db').as_posix()
    with pytest.raises(Fault,match='MIGRATION_REQUIRED'): Store(missing)
    assert not database_path(missing).exists()
    first=Control(cfg)
    with first.store.read() as repo:
        before={name:len(repo.rows(name)) for name in TABLES}
        assert before['principals']==1 and before['agents']==9 and before['tools']==9
        assert 'token' not in json.dumps(repo.get('principals','local-owner')).lower()
    first.close()
    second=Control(cfg)
    with second.store.read() as repo: assert before=={name:len(repo.rows(name)) for name in TABLES}
    second.close()


def test_corrupt_schema_no_reset(cfg):
    engine=engine_for(cfg.database_url)
    with engine.begin() as conn: conn.execute(update(version).values(version=999))
    engine.dispose()
    with pytest.raises(Fault,match='SCHEMA_MISMATCH'): Store(cfg.database_url)
    with pytest.raises(ValueError,match='UNSUPPORTED_SCHEMA_VERSION'): migrate(cfg.database_url)


@pytest.mark.parametrize('path',['state','projects','tools','agents','actions','approvals','approval-requests','revocations','sessions','learning','audit'])
def test_admin_reads(api,path):
    assert api.get('/v1/admin/'+path).status_code==200


@pytest.mark.parametrize('authorization',[None,'Bearer invalid'])
def test_admin_auth(api,authorization):
    req=api.build_request('GET','/v1/admin/state');del req.headers['authorization']
    if authorization: req.headers['Authorization']=authorization
    assert api.send(req).status_code==401


def test_capability_not_role(api):
    c=api.app.state.control
    with c.store.transaction() as repo:
        p=repo.get('principals','local-owner');p['capabilities'].remove('admin.state.manage');repo.put('principals','local-owner',p)
    assert api.get('/v1/admin/state').status_code==200
    assert post(api,'state',{'state':'LOCKED'}).status_code==403
    with c.store.transaction() as repo:
        p=repo.get('principals','local-owner');p['status']='DISABLED';repo.put('principals','local-owner',p)
    assert api.get('/v1/admin/state').status_code==403


def test_state_unlock_and_idempotency(api,cfg):
    key='same-state-key'
    first=post(api,'state',{'state':'LOCKED'},key=key)
    assert first.status_code==200
    assert post(api,'state',{'state':'LOCKED'},key=key).json()==first.json()
    assert post(api,'state',{'state':'RUNNING'},key=key).status_code==409
    assert post(api,'state',{'state':'RUNNING'}).status_code==403
    assert post(api,'state',{'state':'RUNNING','confirmation':'UNLOCK_LUMA'}).status_code==403
    assert post(api,'state',{'state':'RUNNING','confirmation':'UNLOCK_LUMA'},confirmation=cfg.admin_confirmation_token).status_code==200
    # An old idempotent response is a snapshot; replay cannot overwrite later state.
    post(api,'state',{'state':'PAUSED'})
    post(api,'state',{'state':'LOCKED'},key=key)
    assert api.get('/v1/admin/state').json()['state']=='PAUSED'
    r=api.post('/v1/knowledge/query',json={'project_id':'meu-gestor','query':'architecture'})
    assert r.status_code==403
    audit=api.get('/v1/admin/audit').json()
    assert sum(e['event_type']=='ADMIN_STATE' for e in audit)==3


def test_action_approval_consume(api,cfg):
    a=action(api)
    bad=post(api,'approvals/'+a['action_id']+'/decision',{'approved':True})
    assert bad.status_code==400
    body={'decision':'APPROVE','scope':a['scope'],'confirmation':'HUMAN_DECISION'}
    assert post(api,'approvals/'+a['action_id']+'/decision',body).status_code==403
    wrong={**body,'scope':'0'*64}
    assert post(api,'approvals/'+a['action_id']+'/decision',wrong,confirmation=cfg.admin_confirmation_token).status_code==403
    decision=approve(api,cfg,a,key='approve-same-key')
    assert decision.status_code==200
    assert approve(api,cfg,a,key='approve-same-key').json()==decision.json()
    assert approve(api,cfg,a).status_code==409
    aid=decision.json()['approval_id']
    consumed=post(api,'approvals/'+aid+'/consume',confirmation=cfg.admin_confirmation_token,key='consume-same-key')
    assert consumed.status_code==200 and consumed.json()['execution_performed'] is False
    assert post(api,'approvals/'+aid+'/consume',confirmation=cfg.admin_confirmation_token).status_code==409
    assert post(api,'approvals/'+aid+'/consume',confirmation=cfg.admin_confirmation_token,key='consume-same-key').json()==consumed.json()
    assert api.get('/v1/admin/actions/'+a['action_id']).json()['status']=='CANCELLED'
    assert post(api,'actions/'+a['action_id']+'/transition',{'status':'SUCCEEDED'}).status_code==400


@pytest.mark.parametrize('damage',['expired','other_principal','parameters','revoked','locked'])
def test_invalid_approvals(api,cfg,damage):
    a=action(api);record=approve(api,cfg,a).json();c=api.app.state.control
    with c.store.transaction() as repo:
        if damage in ('expired','other_principal'):
            x=repo.get('approvals',record['approval_id'])
            x['expires_at' if damage=='expired' else 'principal_id']=(now()-timedelta(seconds=1)).isoformat() if damage=='expired' else 'someone-else'
            repo.put('approvals',record['approval_id'],x)
        elif damage=='parameters':
            x=repo.get('actions',a['action_id']);x['parameters']={'event_id':'different'};repo.put('actions',a['action_id'],x)
    if damage=='revoked': post(api,'revocations',{'project_id':'meu-gestor','tool_id':'google_calendar','capability':'calendar.delete','reason':'test'})
    if damage=='locked': post(api,'state',{'state':'LOCKED'})
    assert post(api,'approvals/'+record['approval_id']+'/consume',confirmation=cfg.admin_confirmation_token).status_code>=400
    with c.store.read() as repo: assert repo.get('approvals',record['approval_id'])['consumed_at'] is None


def test_session_learning(api):
    session=post(api,'sessions',{'project_id':'meu-gestor'}).json()
    assert api.app.state.control.session(api.app.state.control.principal(),session['session_id'])['status']=='ACTIVE'
    assert post(api,'sessions/'+session['session_id']+'/close').status_code==200
    with pytest.raises(Fault,match='SESSION_EXPIRED'):
        api.app.state.control.session(api.app.state.control.principal(),session['session_id'])
    l=post(api,'learning',{'project_id':'meu-gestor','source':'synthetic','claim':'unverified','evidence':['synthetic-reference'],'confidence':'LOW'}).json()
    assert post(api,'learning/'+l['candidate_id']+'/status',{'status':'PROMOTED'}).status_code==400
    assert post(api,'learning/'+l['candidate_id']+'/status',{'status':'VALIDATED'}).status_code==200
    assert api.get('/v1/admin/learning').json()[0]['status']=='VALIDATED'


def test_tools_and_scope(api):
    assert post(api,'tools/knowledge/disable').status_code==200
    assert post(api,'tools/knowledge/enable').status_code==200
    assert post(api,'tools/google_calendar/enable').status_code==403
    c=api.app.state.control
    with c.store.transaction() as repo:
        t=repo.get('tools','google_calendar');t['enabled']=True;repo.put('tools','google_calendar',t)
        p=repo.get('principals','local-owner');p['capabilities'].append('calendar.read');repo.put('principals','local-owner',p)
        project=repo.get('projects','meu-gestor');project['capabilities'].append('calendar.read');repo.put('projects','meu-gestor',project)
    p=c.principal()
    with pytest.raises(Fault,match='EXTERNAL_EXECUTION_DISABLED'): c.check(p,c.resolve('meu-gestor',p),'google_calendar','calendar.read')
    assert api.patch('/v1/admin/projects/meu-gestor',json={'knowledge_endpoint':'http://evil.example'},headers={'Idempotency-Key':'bad-endpoint'}).status_code==400
    assert post(api,'actions',{'project_id':'mechai','tool_id':'knowledge','capability':'knowledge.read','intent':'test'}).status_code==400


@pytest.mark.parametrize('extra',[{'principal_id':'someone-else'},{'capabilities':['admin.state.manage']},{'database_url':'sqlite:///other.db'},{'path':'../../secrets'},{'status':'SUCCEEDED'}])
def test_mass_assignment(api,extra):
    assert post(api,'actions',{'project_id':'meu-gestor','tool_id':'knowledge','capability':'knowledge.read','intent':'test',**extra}).status_code>=400


def test_sql_injection_audit_and_secrets(api,cfg,caplog):
    a=action(api)
    assert api.get('/v1/admin/actions/'+"x' OR 1=1 --").status_code==404
    assert api.patch('/v1/admin/audit/anything',json={'result':'fake'}).status_code in (404,405)
    assert api.get('/v1/admin/actions/'+a['action_id']).status_code==200
    with caplog.at_level(logging.INFO,logger='luma.audit'):
        r=post(api,'revocations',{'project_id':'meu-gestor','capability':'knowledge.read','reason':cfg.knowledge_token})
        assert r.status_code==400
        assert post(api,'actions',{'project_id':'meu-gestor','tool_id':'knowledge','capability':'knowledge.read','intent':'test','parameters':{'password':'never-save'}}).status_code==400
    raw=database_path(cfg.database_url).read_bytes()
    for token in (cfg.token,cfg.knowledge_token,cfg.admin_confirmation_token):
        assert token.encode() not in raw and token not in caplog.text
    assert b'never-save' not in raw


def test_atomic_rollback(api,monkeypatch):
    c=api.app.state.control;p=c.principal()
    with c.store.read() as repo: before={t:len(repo.rows(t)) for t in ('actions','audit_events','idempotency','approval_requests')}
    def fail(*args,**kwargs): raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(c,'event',fail)
    with pytest.raises(RuntimeError):
        c.mutate(p,'action',{'project_id':'meu-gestor','tool_id':'google_calendar','capability':'calendar.delete','intent':'test','parameters':{}},'rollback-key','test')
    with c.store.read() as repo: assert before=={t:len(repo.rows(t)) for t in before}


def test_restart_preserves_all(cfg):
    c=Control(cfg);p=c.principal()
    def change(op,data,target=None): return c.mutate(p,op,data,secrets.token_hex(12),'restart-test',target=target,confirmed=True)
    a=change('action',{'project_id':'meu-gestor','tool_id':'google_calendar','capability':'calendar.delete','intent':'test','parameters':{}})
    approval=change('decision',{'decision':'APPROVE','scope':a['scope'],'confirmation':'HUMAN_DECISION'},a['action_id'])
    consumed=change('consume',{},approval['approval_id'])
    session=change('session',{'project_id':'meu-gestor'})
    learn=change('learning',{'project_id':'meu-gestor','source':'test','claim':'claim','evidence':['ref'],'confidence':'LOW'})
    change('revoke',{'project_id':'meu-gestor','tool_id':'knowledge','capability':'knowledge.read','reason':'test','expires_at':None})
    change('tool',{'enabled':False},'knowledge')
    change('state',{'state':'LOCKED'})
    with c.store.read() as repo: saved={t:repo.rows(t) for t in TABLES}
    c.close();c=Control(cfg)
    with c.store.read() as repo: assert saved=={t:repo.rows(t) for t in TABLES}
    assert c.state=='LOCKED'
    assert c.listing(c.principal(),'sessions')[0]['session_id']==session['session_id']
    assert c.listing(c.principal(),'learning')[0]['candidate_id']==learn['candidate_id']
    with pytest.raises(Fault): c.mutate(c.principal(),'consume',{},'after-restart','test',target=approval['approval_id'],confirmed=True)
    c.close()


@pytest.mark.parametrize('case',['same_key','double_approval','double_consume','revocations','state'])
def test_concurrency(cfg,case):
    controls=[Control(cfg),Control(cfg)]
    c=controls[0];p=c.principal()
    a=c.mutate(p,'action',{'project_id':'meu-gestor','tool_id':'google_calendar','capability':'calendar.delete','intent':'test','parameters':{}},'setup-action','test')
    if case=='double_consume':
        approval=c.mutate(p,'decision',{'decision':'APPROVE','scope':a['scope'],'confirmation':'HUMAN_DECISION'},'setup-approval','test',target=a['action_id'],confirmed=True)
    def run(i):
        ctrl=controls[i]
        try:
            if case=='same_key': return ctrl.mutate(p,'state',{'state':'PAUSED'},'same-key-concurrent','test')
            if case=='double_approval': return ctrl.mutate(p,'decision',{'decision':'APPROVE','scope':a['scope'],'confirmation':'HUMAN_DECISION'},'approval-'+str(i),'test',target=a['action_id'],confirmed=True)
            if case=='double_consume': return ctrl.mutate(p,'consume',{},'consume-'+str(i),'test',target=approval['approval_id'],confirmed=True)
            if case=='revocations': return ctrl.mutate(p,'revoke',{'project_id':'meu-gestor','capability':'knowledge.read','reason':'test','expires_at':None,'tool_id':'knowledge'},'same-revocation-key','test')
            return ctrl.mutate(p,'state',{'state':'LOCKED' if i else 'PAUSED'},'state-concurrent-'+str(i),'test')
        except Fault as e: return e.code
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(run,range(2)))
        if case in ('double_approval','double_consume'): assert sum(isinstance(r,dict) for r in results)==1
        elif case in ('same_key','revocations'): assert results[0]==results[1]
        else:
            assert c.state=='LOCKED'
            assert any(isinstance(r,dict) for r in results)
        with c.store.read() as repo:
            if case=='double_approval': assert len(repo.rows('approvals'))==1
            if case=='double_consume': assert repo.get('actions',a['action_id'])['status']=='CANCELLED'
            if case=='revocations': assert len(repo.rows('revocations'))==1
    finally:
        for ctrl in controls: ctrl.close()


def test_revoked_admin_and_expiring_session(api):
    assert post(api,'revocations',{'project_id':'meu-gestor','capability':'admin.state.manage','reason':'test'}).status_code==200
    assert post(api,'state',{'state':'LOCKED'}).status_code==403
    session=post(api,'sessions',{'project_id':'meu-gestor'}).json()
    c=api.app.state.control
    with c.store.transaction() as repo:
        row=repo.get('sessions',session['session_id']);row['expires_at']=(now()-timedelta(seconds=1)).isoformat();repo.put('sessions',session['session_id'],row)
    with pytest.raises(Fault,match='SESSION_EXPIRED'): c.session(c.principal(),session['session_id'])


def test_approval_transaction_rollback(api,cfg,monkeypatch):
    a=action(api);c=api.app.state.control;p=c.principal()
    def fail(*args,**kwargs): raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(c,'event',fail)
    with pytest.raises(RuntimeError):
        c.mutate(p,'decision',{'decision':'APPROVE','scope':a['scope'],'confirmation':'HUMAN_DECISION'},'approval-rollback','test',target=a['action_id'],confirmed=True)
    with c.store.read() as repo:
        assert repo.rows('approvals')==[]
        assert repo.get('actions',a['action_id'])['status']=='WAITING_APPROVAL'
        assert repo.get('approval_requests',a['action_id'])['status']=='PENDING'


def test_backup_consistent(cfg):
    from backend.maintenance import backup
    c=Control(cfg)
    c.mutate(c.principal(),'state',{'state':'LOCKED'},'backup-state','test')
    target=backup(cfg.database_url)
    clone=Control(replace(cfg,database_url='sqlite:///'+target.as_posix()))
    assert clone.state=='LOCKED'
    clone.close();c.close()


def test_missing_transaction_anchor_fails_closed(cfg):
    c=Control(cfg)
    with c.store.engine.begin() as conn: conn.execute(version.delete())
    with pytest.raises(Fault,match='SCHEMA_MISMATCH'):
        c.mutate(c.principal(),'state',{'state':'LOCKED'},'missing-anchor','test')
    with c.store.read() as repo: assert repo.get('system_state','global')['state']=='RUNNING'
    c.close()
