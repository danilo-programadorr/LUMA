"""Portable SQLAlchemy repository primitives; SQLite is deployment policy, not business SQL."""
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import MetaData,Table,Column,String,Integer,JSON,create_engine,select,update,insert,inspect,or_
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from .errors import Fault

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_URL='sqlite:///'+(ROOT/'runtime/luma.db').as_posix()
metadata=MetaData()
version=Table('schema_version',metadata,Column('id',Integer,primary_key=True),Column('version',Integer,nullable=False),Column('epoch',Integer,nullable=False))
TABLES={}
for name in ('principals','projects','tools','agents','system_state','actions','approvals','approval_requests','revocations','sessions','learning','audit_events','idempotency'):
    TABLES[name]=Table(name,metadata,Column('id',String(128),primary_key=True),
        Column('principal_id',String(64),index=True),Column('project_id',String(64),index=True),
        Column('status',String(40)),Column('created_at',String(40),nullable=False),
        Column('updated_at',String(40),nullable=False),Column('data',JSON,nullable=False))

# v0001 continues importing its original metadata unchanged.
trust_metadata=MetaData()
for name in ('retention_policies','audit_chain'):
    TABLES[name]=Table(name,trust_metadata,Column('id',String(128),primary_key=True),
        Column('principal_id',String(64)),Column('project_id',String(64)),Column('status',String(40)),
        Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False),Column('data',JSON,nullable=False))
TABLES['grants']=Table('grants',trust_metadata,Column('id',String(128),primary_key=True),
    Column('principal_id',String(64),nullable=False,index=True),Column('capability',String(100),nullable=False),
    Column('project_id',String(64)),Column('tool_id',String(64)),Column('scope',String(40),nullable=False),
    Column('granted_by',String(64),nullable=False),Column('created_at',String(40),nullable=False),
    Column('expires_at',String(40)),Column('status',String(40),nullable=False))

conversation_metadata=MetaData()
for name in ('conversation_windows','conversation_requests'):
    TABLES[name]=Table(name,conversation_metadata,Column('id',String(128),primary_key=True),
        Column('principal_id',String(64)),Column('project_id',String(64)),Column('status',String(40)),
        Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False),Column('data',JSON,nullable=False))


def database_path(url):
    try:
        parsed=make_url(url)
        if parsed.drivername!='sqlite' or parsed.host or parsed.username or parsed.password or parsed.query or not parsed.database or parsed.database==':memory:':
            raise ValueError()
        p=Path(parsed.database)
        p=(ROOT/p).resolve() if not p.is_absolute() else p.resolve()
        if not p.is_relative_to((ROOT/'runtime').resolve()) or p.suffix!='.db': raise ValueError()
        return p
    except Exception:
        raise ValueError('INVALID_DATABASE_LOCATION') from None


def engine_for(url):
    p=database_path(url)
    return create_engine('sqlite:///'+p.as_posix(),connect_args={'timeout':10},pool_pre_ping=True)


class Repository:
    def __init__(self,connection): self.connection=connection
    def get(self,table,key):
        if table=='grants':
            row=self.connection.execute(select(TABLES[table]).where(TABLES[table].c.id==key)).mappings().first()
            return {**dict(row),'grant_id':row['id']} if row else None
        row=self.connection.execute(select(TABLES[table].c.data).where(TABLES[table].c.id==key)).first()
        return dict(row[0]) if row else None
    def rows(self,table,principal_id=None,projects=None,limit=None,offset=0):
        target=TABLES[table]
        query=select(target if table=='grants' else target.c.data).order_by(target.c.created_at,target.c.id)
        if principal_id is not None: query=query.where(or_(target.c.principal_id.is_(None),target.c.principal_id==principal_id))
        if projects is not None: query=query.where(or_(target.c.project_id.is_(None),target.c.project_id.in_(projects)))
        if limit is not None: query=query.limit(limit).offset(offset)
        if table=='grants': return [{**dict(row),'grant_id':row['id']} for row in self.connection.execute(query).mappings()]
        return [dict(row[0]) for row in self.connection.execute(query)]
    def add(self,table,key,data):
        if table=='grants':
            self.connection.execute(insert(TABLES[table]).values(id=key,**{k:v for k,v in data.items() if k in TABLES[table].c and k!='id'}))
            return
        from .models import now
        stamp=now().isoformat()
        self.connection.execute(insert(TABLES[table]).values(id=key,principal_id=data.get('principal_id'),project_id=data.get('project_id'),
            status=data.get('status'),created_at=data.get('created_at',stamp),updated_at=stamp,data=data))
    def put(self,table,key,data):
        if table=='grants':
            result=self.connection.execute(update(TABLES[table]).where(TABLES[table].c.id==key).values(**{k:v for k,v in data.items() if k in TABLES[table].c and k!='id'}))
            if result.rowcount!=1: raise Fault('NOT_FOUND',404)
            return
        if table in ('audit_events','idempotency'): raise Fault('APPEND_ONLY',403)
        from .models import now
        result=self.connection.execute(update(TABLES[table]).where(TABLES[table].c.id==key).values(
            principal_id=data.get('principal_id'),project_id=data.get('project_id'),status=data.get('status'),updated_at=now().isoformat(),data=data))
        if result.rowcount!=1: raise Fault('NOT_FOUND',404)


class Store:
    def __init__(self,url):
        if not database_path(url).is_file(): raise Fault('MIGRATION_REQUIRED',503)
        self.engine=engine_for(url)
        try:
            with self.engine.connect() as conn:
                if set(inspect(conn).get_table_names())!=(set(metadata.tables)|set(trust_metadata.tables)|set(conversation_metadata.tables)): raise Fault('SCHEMA_MISMATCH',503)
                if conn.execute(select(version.c.version).where(version.c.id==1)).scalar_one()!=3: raise Fault('SCHEMA_MISMATCH',503)
        except Fault:
            self.engine.dispose()
            raise
        except SQLAlchemyError:
            self.engine.dispose()
            raise Fault('DATABASE_UNAVAILABLE',503) from None
    def close(self): self.engine.dispose()
    @contextmanager
    def read(self):
        try:
            with self.engine.connect() as conn: yield Repository(conn)
        except SQLAlchemyError: raise Fault('DATABASE_UNAVAILABLE',503) from None
    @contextmanager
    def transaction(self):
        try:
            with self.engine.begin() as conn:
                # A portable UPDATE takes a database row write lock before any policy reads.
                locked=conn.execute(update(version).where(version.c.id==1,version.c.version==3).values(epoch=version.c.epoch+1))
                if locked.rowcount!=1: raise Fault('SCHEMA_MISMATCH',503)
                yield Repository(conn)
        except SQLAlchemyError: raise Fault('DATABASE_UNAVAILABLE',503) from None
