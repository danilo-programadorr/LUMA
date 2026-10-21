"""Explicit additive upgrade. Historical v0001 source is unchanged."""
from sqlalchemy import select,update,inspect
from backend.app.database import metadata,trust_metadata,version,TABLES,Repository
from backend.app.trust_data import seed,digest

REVISION=2

def upgrade(connection):
    current=connection.execute(select(version.c.version).where(version.c.id==1)).scalar_one()
    names=set(inspect(connection).get_table_names())
    if current==2:
        if names!=set(metadata.tables)|set(trust_metadata.tables): raise ValueError('PARTIAL_OR_UNKNOWN_SCHEMA')
        return False
    if current!=1: raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
    if names!=set(metadata.tables): raise ValueError('PARTIAL_OR_UNKNOWN_SCHEMA')
    # SQLite DDL is enclosed in an explicitly started transaction by the runner.
    for table in trust_metadata.sorted_tables: table.create(connection)
    repo=Repository(connection)
    seed(repo)
    previous='0'*64
    events=repo.rows('audit_events')
    for seq,event in enumerate(events,1):
        event.update(sequence=seq,previous_hash=previous,visibility='ADMIN')
        event['event_hash']=digest(event);previous=event['event_hash']
        connection.execute(update(TABLES['audit_events']).where(TABLES['audit_events'].c.id==event['event_id']).values(data=event))
    repo.add('audit_chain','head',dict(sequence=len(events),event_hash=previous))
    connection.execute(update(version).where(version.c.id==1).values(version=2))
    return True
