"""Candidate 0007: operational research rows only for Google; display is ephemeral.

Owner database remains schema6. Historical migrations are untouched. Isolated
schema7 test databases must be recreated to obtain the no-Google-result constraint.
"""
from sqlalchemy import select,update,inspect
from backend.app.database import version
from backend.research.schema import metadata

def upgrade(connection):
    current=connection.execute(select(version.c.version)).scalar_one()
    if current==7:
        if not set(metadata.tables)<=set(inspect(connection).get_table_names()):raise ValueError('PARTIAL_RESEARCH_SCHEMA')
        return False
    if current!=6:raise ValueError('UNSUPPORTED_SCHEMA_VERSION')
    metadata.create_all(connection)
    connection.execute(update(version).where(version.c.id==1).values(version=7))
    return True
