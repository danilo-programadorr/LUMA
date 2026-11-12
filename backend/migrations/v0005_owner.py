from sqlalchemy import select,update,inspect
from backend.app.database import version
from backend.owner_schema import owner_metadata

def upgrade(connection):
    current=connection.execute(select(version.c.version)).scalar_one()
    if current==5:
        if not set(owner_metadata.tables)<=set(inspect(connection).get_table_names()):raise ValueError('PARTIAL_OWNER_SCHEMA')
        return False
    if current!=4:raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
    owner_metadata.create_all(connection)
    connection.execute(update(version).where(version.c.id==1).values(version=5))
    return True
