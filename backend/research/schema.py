from sqlalchemy import MetaData,Table,Column,String,JSON
metadata=MetaData();TABLES={}
for name in ('research_requests','research_devices','research_limits'):
    TABLES[name]=Table(name,metadata,Column('id',String(128),primary_key=True),Column('principal_id',String(64)),Column('project_id',String(64),index=True),Column('status',String(40)),Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False),Column('data',JSON,nullable=False))

# Candidate schema7: Google display payloads may never become database history.
# Metadata (provider/model/usage) remains outside result; NULL result is deliberate.
from sqlalchemy import CheckConstraint,or_
t=TABLES['research_requests']
t.append_constraint(CheckConstraint(or_(t.c.data['result']['provider'].as_string().is_(None),t.c.data['result']['provider'].as_string()!='gemini_google_search'),name='no_persisted_google_grounding'))
