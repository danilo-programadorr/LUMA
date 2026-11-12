from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json,time,uuid
import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from backend.tests.private_library_support import build,enable,register,create,delivery,HEADERS
from backend.private_library.schema import TABLES
from backend.private_library.service import LibraryService
from backend.owner_auth import AuthenticatedOwnerPrincipal
from backend.migrate import migrate

@pytest.fixture
def library_pg(pg_url,monkeypatch):
 monkeypatch.setenv('LUMA_ENV','test');ctx=build(pg_url,'postgresql');enable(ctx[1],ctx[3],ctx[4]);register(ctx[1],ctx[3],ctx[4]);yield ctx
 ctx[1].__exit__(None,None,None);ctx[0].state.control.close()

def test_pg_library_concurrent_idempotency(library_pg):
 app,c,t,d,send=library_pg;key=uuid.uuid4().hex;gate=Barrier(2)
 def issue(_):gate.wait();return create(c,d,idempotency_key=key)
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(issue,range(2)))
 assert all(x.status_code==200 for x in responses) and len({x.json()['query_id'] for x in responses})==1
 with app.state.control.store.read() as r:assert len(r.rows('library_queries'))==1

def test_pg_library_one_claim(library_pg):
 app,c,t,d,send=library_pg;create(c,d);gate=Barrier(2)
 def claim(_):gate.wait();return send('poll',{})
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(claim,range(2)))
 assert all(x.status_code in (200,409) for x in responses) and sum(bool(x.json().get('request')) for x in responses)==1

def test_pg_private_payload_database_constraint(library_pg):
 app,c,t,d,send=library_pg;qid=create(c,d).json()['query_id']
 with app.state.control.store.read() as r:row=r.get('library_queries',qid)
 for key in ('result','matches'):
  with pytest.raises(IntegrityError):
   with app.state.control.store.engine.begin() as conn:conn.execute(update(TABLES['library_queries']).where(TABLES['library_queries'].c.id==qid).values(data={**row,key:{'excerpt':'Synthetic forbidden persisted quote'}}))

def test_pg_restart_preserves_metadata_drops_excerpts(library_pg):
 app,c,t,d,send=library_pg;m=register(c,d,send);qid=create(c,d).json()['query_id'];assert send('result',delivery(send,m)).status_code==200
 with app.state.control.store.read() as r:
  row=r.get('library_queries',qid);assert 'Synthetic private cancellation procedure.' not in json.dumps(row)
 restarted=LibraryService(app.state.control,app.state.device_service);owner=AuthenticatedOwnerPrincipal(row['principal_id'],'google.com','synthetic',int(time.time()),'test-restart')
 assert restarted.get(owner,qid)['result'] is None
 assert c.get('/v1/library/projects/meu-gestor/sources',headers=HEADERS).json()[0]['source_id']==m.source_id

def test_pg_library_upgrade_idempotent(library_pg,pg_url):
 assert migrate(pg_url,'postgresql',library=True) is False

def test_pg_archive_blocks_pending_delivery(library_pg):
 app,c,t,d,send=library_pg;m=register(c,d,send);qid=create(c,d).json()['query_id'];payload=delivery(send,m)
 c.post('/v1/library/projects/meu-gestor/sources/'+m.source_id+'/archive',headers=HEADERS,json={})
 assert send('result',payload).status_code!=200
 assert c.get('/v1/library/queries/'+qid,headers=HEADERS).json()['result'] is None
