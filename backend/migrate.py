import argparse
import os
from .app.database import DEFAULT_URL,database_path,engine_for
from sqlalchemy import inspect
from .migrations.v0001_initial import upgrade as initial
from .migrations.v0002_trust_boundary import upgrade


def migrate(url):
    database_path(url).parent.mkdir(parents=True,exist_ok=True)
    engine=engine_for(url)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            try:
                if not inspect(connection).get_table_names(): initial(connection)
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
    changed=migrate(os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL))
    print('Migration 0002 applied' if changed else 'Schema 0002 already current')

if __name__=='__main__': main()
