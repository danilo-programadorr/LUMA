import os,uuid,secrets
from datetime import timedelta
import pytest,psycopg
from psycopg import sql
from sqlalchemy.engine import URL
from backend.migrate import migrate
from backend.app.config import Settings
from backend.app.trust import Control
from backend.app.execution import ExecutionService
from backend.app.models import now

@pytest.fixture
def pg_url():
    password=os.environ['LUMA_PG_TEST_PASSWORD']
    name='luma_test_'+uuid.uuid4().hex
    admin=psycopg.connect(host='127.0.0.1',port=55432,user='luma_admin',
        password=os.environ['LUMA_PG_ADMIN_PASSWORD'],dbname='postgres',autocommit=True)
    admin.execute(sql.SQL('CREATE DATABASE {} OWNER luma_test TEMPLATE template0').format(sql.Identifier(name)))
    url=URL.create('postgresql+psycopg',username='luma_test',password=password,host='127.0.0.1',port=55432,database=name)
    try: yield url
    finally:
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        admin.close()

@pytest.fixture
def engine(pg_url):
    migrate(pg_url,'postgresql')
    cfg=Settings(secrets.token_urlsafe(32),secrets.token_urlsafe(32),
        admin_confirmation_token=secrets.token_urlsafe(32),runtime_token=secrets.token_urlsafe(32),
        database_url=pg_url,database_backend='postgresql')
    control=Control(cfg)
    clock=[now()]
    service=ExecutionService(control,sandbox=True,clock=lambda:clock[0])
    with control.store.transaction() as repo:
        repo.add('tools','sandbox-test',dict(tool_id='sandbox-test',enabled=True,capabilities=['record','review','sensitive','critical']))
    try: yield service,control.principal(),clock
    finally: control.close()
