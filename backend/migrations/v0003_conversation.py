from sqlalchemy import select,update,inspect
from backend.app.database import metadata,trust_metadata,conversation_metadata,version,Repository
from backend.app.trust_data import grant

def upgrade(connection):
    current=connection.execute(select(version.c.version).where(version.c.id==1)).scalar_one()
    expected=set(metadata.tables)|set(trust_metadata.tables)
    names=set(inspect(connection).get_table_names())
    if current==3:
        if names!=expected|set(conversation_metadata.tables): raise ValueError('PARTIAL_OR_UNKNOWN_SCHEMA')
        return False
    if current!=2: raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
    if names!=expected: raise ValueError('PARTIAL_OR_UNKNOWN_SCHEMA')
    for table in conversation_metadata.sorted_tables: table.create(connection)
    seed(Repository(connection))
    connection.execute(update(version).where(version.c.id==1).values(version=3))
    return True

def seed(repo):
    owner=repo.get('principals','local-owner');runtime=repo.get('principals','luma-runtime')
    if not owner or not runtime: return
    for project in set(owner['project_scopes']) & set(runtime['project_scopes']):
        grant(repo,'local-owner','conversation.turn',project,by='MIGRATION_0003')
        grant(repo,'luma-runtime','runtime.model.generate',project,by='MIGRATION_0003')
    for category in ('conversation_windows','conversation_requests'):
        repo.add('retention_policies',category,dict(category=category,mode='NO_AUTO_DELETE',purge_enabled=False,
            expiration_is_deletion=False,context_window_turns=4,context_window_chars=8000,context_ttl_hours=24))
