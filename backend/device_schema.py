"""Device identity: public keys only; durable counters and rate limits."""
from sqlalchemy import MetaData,Table,Column,String,JSON
DEVICE_TABLES={}
device_metadata=MetaData()
for name in ('device_identities','device_enrollments','device_rate_limits'):
    DEVICE_TABLES[name]=Table(name,device_metadata,Column('id',String(128),primary_key=True),Column('principal_id',String(64)),Column('project_id',String(64)),Column('status',String(40)),Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False),Column('data',JSON,nullable=False))
