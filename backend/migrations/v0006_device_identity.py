from sqlalchemy import select,update,inspect
from backend.app.database import version
from backend.device_schema import device_metadata

def upgrade(connection):
    current=connection.execute(select(version.c.version)).scalar_one()
    if current==6:
        if not set(device_metadata.tables)<=set(inspect(connection).get_table_names()):raise ValueError('PARTIAL_DEVICE_SCHEMA')
        return False
    if current!=5:raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
    device_metadata.create_all(connection)
    connection.execute(update(version).where(version.c.id==1).values(version=6))
    return True
