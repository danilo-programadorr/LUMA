"""Additive owner identity schema; historical migration metadata is unchanged."""
from sqlalchemy import MetaData,Table,Column,String,Integer,CheckConstraint,UniqueConstraint
owner_metadata=MetaData()
owner_bindings=Table('owner_bindings',owner_metadata,
 Column('id',Integer,primary_key=True),Column('provider',String(40),nullable=False),
 Column('subject_uid',String(128),nullable=False),Column('internal_owner_id',String(64),nullable=False),
 Column('status',String(16),nullable=False),Column('created_at',String(40),nullable=False),
 Column('bound_at',String(40),nullable=False),Column('revoked_at',String(40)),Column('version',Integer,nullable=False),
 CheckConstraint('id = 1',name='single_owner_slot'),UniqueConstraint('provider','subject_uid'))
owner_bootstrap=Table('owner_bootstrap',owner_metadata,
 Column('id',Integer,primary_key=True),Column('digest',String(64),nullable=False),
 Column('expires_at',Integer,nullable=False),Column('attempts',Integer,nullable=False),
 Column('status',String(16),nullable=False),CheckConstraint('id = 1',name='single_bootstrap_slot'))
