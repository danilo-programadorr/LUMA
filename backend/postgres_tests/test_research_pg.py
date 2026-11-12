from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
import uuid
import pytest
from backend.tests.research_support import build,create,HEADERS
from backend.research.contracts import ResearchRequest
from backend.research.provider import MockWebResearchProvider
from backend.research.service import ResearchService

@pytest.fixture
def research_pg(pg_url,monkeypatch):
    monkeypatch.setenv('LUMA_ENV','test');ctx=build(pg_url,'postgresql')
    yield ctx
    ctx[1].__exit__(None,None,None);ctx[0].state.control.close()

def test_pg_concurrent_idempotency(research_pg):
    a,c,t,d,send=research_pg;key=uuid.uuid4().hex;gate=Barrier(2)
    def issue(_):gate.wait();return create(c,d,idempotency_key=key)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(issue,range(2)))
    assert all(x.status_code==200 for x in responses)
    assert len({x.json()['research_id'] for x in responses})==1
    with a.state.control.store.read() as r:assert len(r.rows('research_requests'))==1

def test_pg_concurrent_claim(research_pg):
    a,c,t,d,send=research_pg;create(c,d);gate=Barrier(2)
    def poll(_):gate.wait();return send('poll',{})
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(poll,range(2)))
    assert all(x.status_code in (200,409) for x in responses)
    assert sum(bool(x.json().get('request')) for x in responses)==1

def test_pg_result_restart_sources_and_audit(research_pg):
    a,c,t,d,send=research_pg;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json();result=MockWebResearchProvider().search(ResearchRequest.model_validate(lease['request']))
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    restarted=ResearchService(a.state.control,a.state.device_service)
    with a.state.control.store.read() as r:assert restarted.find(r,rid)['result']['sources'][0]['domain']=='react.dev'
    assert a.state.control.listing(a.state.control.principal(),'audit_verify')['verified']

@pytest.mark.parametrize('action',['cancel','expire','revoke'])
def test_pg_late_delivery_blocked(research_pg,action):
    a,c,t,d,send=research_pg;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json();result=MockWebResearchProvider().search(ResearchRequest.model_validate(lease['request']))
    if action=='cancel':c.post('/v1/research/'+rid+'/cancel',headers=HEADERS)
    elif action=='expire':t[0]+=timedelta(seconds=241)
    else:c.post('/v1/devices/'+d['device_id']+'/revoke',headers=HEADERS,json={})
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code in (403,409)

def test_pg_project_isolation(research_pg):
    a,c,t,d,send=research_pg
    assert create(c,d,project_id='other-project').status_code in (403,404)
    rid=create(c,d).json()['research_id']
    assert c.get('/v1/research/'+rid,headers={'Authorization':'Bearer other-fixture'}).status_code==403

def test_pg_upgrade_idempotent(research_pg,pg_url):
    from backend.migrate import migrate
    from sqlalchemy import select
    from backend.app.database import version
    a,c,t,d,send=research_pg;assert migrate(pg_url,'postgresql',research=True) is False
    with a.state.control.store.read() as r:assert r.connection.execute(select(version.c.version)).scalar_one()==7


def test_pg_google_artifacts_never_written_and_restart_drops_display(research_pg):
    import json
    from backend.tests.google_display_support import google_result,HTML,ANSWER,URL
    a,c,t,d,send=research_pg;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json();result=google_result(ResearchRequest.model_validate(lease['request']))
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    with a.state.control.store.read() as r:
        data=json.dumps([r.rows(x) for x in ('research_requests','audit_events','learning')]);assert all(x not in data for x in (HTML,ANSWER,URL,'Ephemeral title marker'))
    restarted=ResearchService(a.state.control,a.state.device_service)
    assert not restarted.display._items
    with a.state.control.store.read() as r:assert restarted.find(r,rid)['result'] is None

def test_pg_constraint_rejects_google_result_persistence(research_pg):
    from sqlalchemy.exc import IntegrityError
    a,c,t,d,send=research_pg;rid=create(c,d).json()['research_id']
    from backend.app.errors import Fault
    with pytest.raises(Fault) as wrapped:
        with a.state.control.store.transaction() as r:
            row=ResearchService(a.state.control,a.state.device_service).find(r,rid);row['result']={'provider':'gemini_google_search','answer':'must never write'}
            with pytest.raises(IntegrityError) as sql_error:r.put('research_requests',row['key'],row)
            assert sql_error.value.orig.diag.constraint_name=='no_persisted_google_grounding'
            raise sql_error.value
    assert wrapped.value.code=='DATABASE_UNAVAILABLE'


def test_pg_google_failure_is_terminal_with_original_error_and_usage(research_pg):
    import time
    from backend.research.contracts import ResearchResult,Usage
    a,c,t,d,send=research_pg;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json()
    result=ResearchResult(research_id=rid,status='FAILED',error_code='RESEARCH_ATTRIBUTION_NAVIGATION_UNSUPPORTED',provider='gemini_google_search',model='gemini-3.8-flash',usage=Usage(model_calls=1,search_queries=2),completed_at=int(time.time()))
    response=send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()})
    assert response.status_code==200,response.text
    row=c.get('/v1/research/'+rid,headers=HEADERS).json()
    assert row['status']=='FAILED' and row['error_code']=='RESEARCH_ATTRIBUTION_NAVIGATION_UNSUPPORTED'
    assert row['result'] is None and row['usage_metadata']['usage']['search_queries']==2


def test_pg_isolated_window_contains_no_persisted_answer_or_capability(research_pg):
    import json
    from backend.tests.test_google_window import targetless
    a,c,t,d,send=research_pg;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json()
    result,html=targetless(ResearchRequest.model_validate(lease['request']))
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    row=c.get('/v1/research/'+rid,headers=HEADERS).json();assert c.get(row['display_path']).status_code==200
    with a.state.control.store.read() as r:
        stored=json.dumps([r.rows(x) for x in ('research_requests','audit_events','learning')]);assert html not in stored and row['display_path'] not in stored and result.answer not in stored


def test_pg_internal_token_counters_are_numeric_metadata_without_grounded_payload(research_pg):
    from backend.tests.google_display_support import google_result,ANSWER,HTML,URL
    from backend.research.contracts import Usage
    import json
    a,c,t,d,send=research_pg;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json()
    result=google_result(ResearchRequest.model_validate(lease['request'])).model_copy(update={'usage':Usage(model_calls=1,search_queries=1,thought_tokens=3,tool_use_tokens=40,total_tokens=100,cached_tokens=0)})
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    with a.state.control.store.read() as repo:
        row=repo.rows('research_requests')[0];usage=row['usage_metadata']['usage']
        assert row['result'] is None
        assert usage['thought_tokens']==3 and usage['tool_use_tokens']==40 and usage['total_tokens']==100 and usage['cached_tokens']==0
        stored=json.dumps([repo.rows(x) for x in ('research_requests','audit_events','learning')]);assert all(x not in stored for x in (ANSWER,HTML,URL))
