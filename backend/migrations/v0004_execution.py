from sqlalchemy import select,update,inspect
from backend.app.database import metadata,trust_metadata,conversation_metadata,execution_metadata,version,Repository
from backend.app.trust_data import grant
from backend.app.models import now


def seed(repo):
    owner=repo.get('principals','local-owner')
    if not owner:return
    row=dict(principal_id='luma-executor',principal_type='SERVICE_EXECUTOR',display_name='LUMA executor',roles=[],project_scopes=list(owner['project_scopes']),capabilities=[],approval_level='OWNER_SCOPED',status='ACTIVE',created_at=now().isoformat())
    repo.add('principals','luma-executor',row)
    for project in owner['project_scopes']:
        grant(repo,'luma-executor','executor.jobs.execute',project,by='MIGRATION_0004')
    from backend.app.agent_team import seed as agent_seed
    agent_seed(repo)
    for category in execution_metadata.tables:
        repo.add('retention_policies',category,dict(category=category,mode='NO_AUTO_DELETE',purge_enabled=False,expiration_is_deletion=False))


def upgrade(connection):
    current=connection.execute(select(version.c.version).where(version.c.id==1)).scalar_one()
    expected=set(metadata.tables)|set(trust_metadata.tables)|set(conversation_metadata.tables)
    names=set(inspect(connection).get_table_names())
    if current==4:
        if names!=expected|set(execution_metadata.tables):raise ValueError('PARTIAL_OR_UNKNOWN_SCHEMA')
        return False
    if current!=3 or names!=expected:raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
    for table in execution_metadata.sorted_tables:table.create(connection)
    seed(Repository(connection))
    connection.execute(update(version).where(version.c.id==1).values(version=4))
    return True
