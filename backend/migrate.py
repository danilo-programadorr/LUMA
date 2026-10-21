import argparse
import os
from .app.database import DEFAULT_URL,database_path,engine_for
from .migrations.v0001_initial import upgrade


def migrate(url):
    database_path(url).parent.mkdir(parents=True,exist_ok=True)
    engine=engine_for(url)
    try:
        with engine.begin() as connection: return upgrade(connection)
    finally: engine.dispose()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['upgrade'])
    parser.parse_args()
    changed=migrate(os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL))
    print('Migration 0001 applied' if changed else 'Schema 0001 already current')

if __name__=='__main__': main()
