"""Initial explicit, versioned schema. Never called implicitly by application startup."""
from sqlalchemy import inspect,insert,select
from backend.app.database import metadata,version

REVISION=1

def upgrade(connection):
    names=set(inspect(connection).get_table_names())
    if names:
        if names!=set(metadata.tables): raise ValueError('PARTIAL_OR_UNKNOWN_SCHEMA')
        if connection.execute(select(version.c.version).where(version.c.id==1)).scalar_one()!=REVISION:
            raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
        return False
    for table in metadata.sorted_tables:
        table.create(connection)
    connection.execute(insert(version).values(id=1,version=REVISION,epoch=0))
    return True
