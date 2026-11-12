from sqlalchemy import MetaData,Table,Column,String,JSON
metadata=MetaData()
TABLES={}
TABLES['codex_workspaces']=Table('codex_workspaces',metadata,Column('id',String(128),primary_key=True),Column('principal_id',String(64),index=True),Column('project_id',String(64),index=True),Column('status',String(40)),Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False),Column('data',JSON,nullable=False))
