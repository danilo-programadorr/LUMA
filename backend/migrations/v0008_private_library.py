from sqlalchemy import select,update,inspect
from backend.app.database import version
from backend.private_library.schema import metadata

def upgrade(connection):
 current=connection.execute(select(version.c.version)).scalar_one()
 if current==8:
  if not set(metadata.tables)<=set(inspect(connection).get_table_names()):raise ValueError('PARTIAL_LIBRARY_SCHEMA')
  return False
 if current!=7:raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
 metadata.create_all(connection)
 connection.execute(update(version).where(version.c.id==1).values(version=8))
 return True
