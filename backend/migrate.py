import argparse
import os
from .app.database import DEFAULT_URL,validate_database,engine_for
from sqlalchemy import inspect,select
from .app.database import version
from .migrations.v0001_initial import upgrade as initial
from .migrations.v0002_trust_boundary import upgrade as trust_upgrade
from .migrations.v0003_conversation import upgrade as conversation_upgrade
from .migrations.v0004_execution import upgrade


def migrate(url,backend='sqlite'):
    path=validate_database(url,backend)
    if path is not None: path.parent.mkdir(parents=True,exist_ok=True)
    engine=engine_for(url,backend)
    try:
        with engine.connect() as connection:
            if backend == 'sqlite': connection.exec_driver_sql('BEGIN IMMEDIATE')
            else:
                connection.begin()
                # Serialize bootstrap even before schema_version exists.
                connection.exec_driver_sql('SELECT pg_advisory_xact_lock(76400601)')
            try:
                if not inspect(connection).get_table_names(): initial(connection)
                if connection.execute(select(version.c.version)).scalar_one()==1: trust_upgrade(connection)
                if connection.execute(select(version.c.version)).scalar_one()==2: conversation_upgrade(connection)
                changed=upgrade(connection)
                connection.commit()
                return changed
            except Exception:
                connection.rollback()
                raise
    finally: engine.dispose()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['upgrade'])
    parser.parse_args()
    changed=migrate(os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL),os.environ.get('LUMA_DATABASE_BACKEND','sqlite'))
    print('Migration 0004 applied' if changed else 'Schema 0004 already current')

if __name__=='__main__': main()
