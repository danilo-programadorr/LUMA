from sqlalchemy import MetaData,Table,Column,String,JSON,CheckConstraint,and_
metadata=MetaData();TABLES={}
for name in ('library_devices','library_sources','library_queries'):
 TABLES[name]=Table(name,metadata,Column('id',String(128),primary_key=True),Column('principal_id',String(64)),Column('project_id',String(64),index=True),Column('status',String(40)),Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False),Column('data',JSON,nullable=False))
t=TABLES['library_queries']
t.append_constraint(CheckConstraint(and_(t.c.data['result'].as_string().is_(None),t.c.data['matches'].as_string().is_(None)),name='no_persisted_private_excerpts'))
