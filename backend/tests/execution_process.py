"""Test-only process harness. Never installed as a production tool adapter."""
import os,sys,json,secrets,time
from datetime import datetime,timedelta
from backend.app.models import now
from backend.app.execution import ExecutionService
from backend.app.execution_contracts import CanonicalActionEnvelope
from backend.executor_worker import service,cycle,FORBIDDEN_ENV
from backend.app.trust_data import verify

stage=sys.argv[1];url=os.environ['LUMA_DATABASE_URL']
if stage=='create':
    import httpx
    from fastapi.testclient import TestClient
    from backend.app.config import Settings
    from backend.app.main import create_app
    from backend.app.knowledge import KnowledgeClient
    from backend.app.model_config import ModelSettings
    from backend.tests.test_conversation import FakeModelProvider
    from backend.tests.test_foundation import transport
    from backend.migrate import migrate
    migrate(url)
    cfg=Settings(secrets.token_urlsafe(32),secrets.token_urlsafe(32),runtime_token=secrets.token_urlsafe(32),database_url=url)
    app=create_app(cfg,KnowledgeClient(cfg,httpx.MockTransport(transport)),FakeModelProvider(),ModelSettings(),execution_sandbox=True)
    with TestClient(app,base_url='http://127.0.0.1',headers={'Authorization':'Bearer '+cfg.token}) as api:
        sid=api.post('/v1/admin/sessions',json={'project_id':'meu-gestor'},headers={'Idempotency-Key':secrets.token_hex(12)}).json()['session_id']
        task=api.post('/v1/tasks',json={'project_id':'meu-gestor','session_id':sid,'message':'Olá'},headers={'Idempotency-Key':secrets.token_hex(12)})
        assert task.status_code==200,task.text
        e=app.state.execution;p=app.state.control.principal();at=now()
        with e.store.transaction() as r:r.add('tools','sandbox-test',dict(tool_id='sandbox-test',enabled=True,capabilities=['record']))
        device=e.devices.register(p,dict(device_id='pc-test',name='Synthetic PC',device_type='WINDOWS'),'register-key','process')
        action=e.candidate(p,CanonicalActionEnvelope(project_id='meu-gestor',tool_id='sandbox-test',operation='record',execution_target='LOCAL_DEVICE',target_device_id='pc-test').model_dump(mode='json'),'action-key','process')
        auth=e.authorize(p,action['action_id'],dict(valid_from=at.isoformat(),expires_at=(at+timedelta(minutes=10)).isoformat(),max_executions=1,confirmation='AUTHORIZE_EXACT_ACTION',late_execution_policy='RUN_LATE_WITHIN_GRACE',grace_seconds=300),'auth-key','process')
        job=e.job(p,dict(authorization_id=auth['authorization_id'],action=auth['action_template'],trigger_type='SCHEDULED_AT',scheduled_for=(at+timedelta(seconds=5)).isoformat()),'job-key-1','process')
        app.state.control.mutate(p,'close_session',{},'close-session-key','process',target=sid)
        print(json.dumps({'job_id':job['job_id'],'device_credential':device['device_credential'],'time':(at+timedelta(seconds=6)).isoformat(),'task_id':task.json()['task_id']}))
else:
    assert not any(os.environ.get(k) for k in FORBIDDEN_ENV)
    e=service(url,sandbox=True);e.clock=lambda:datetime.fromisoformat(os.environ['LUMA_TEST_TIME'])
    try:
        start=time.monotonic()
        if stage=='schedule':e.tick();result={'stage':stage}
        elif stage in ('execute','crash'):
            e.devices.heartbeat(dict(device_id='pc-test',executor_version='0.5.0rc1',status='ONLINE',capabilities=['sandbox-test'],current_job_count=0),os.environ['LUMA_DEVICE_CREDENTIAL'])
            e.tick();worker=secrets.token_hex(10);job=e.claim(worker,'pc-test',os.environ['LUMA_DEVICE_CREDENTIAL'])
            if job:
                e.execute(job['job_id'],worker,after_effect=(lambda:os._exit(75)) if stage=='crash' else None)
            result={'claimed':bool(job),'owner_credential_present':False}
        elif stage=='recover':
            result={'recovered':e.reconcile(os.environ['LUMA_TEST_JOB'])['status']}
        elif stage=='inspect':
            with e.store.read() as r:
                result={'jobs':[j['status'] for j in r.rows('jobs')],'effects':len(r.rows('sandbox_effects')),'records':len(r.rows('execution_records')),
                        'authorizations':len(r.rows('execution_authorizations')),'tasks':len(r.rows('agent_tasks')),'audit_verified':bool(verify(r)),
                        'sessions_closed':all(s['status']!='ACTIVE' for s in r.rows('sessions'))}
        result['latency_ms']=int((time.monotonic()-start)*1000)
        print(json.dumps(result))
    finally:e.store.close()
