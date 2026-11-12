import argparse
import os
from .app.database import DEFAULT_URL,validate_database,engine_for
from sqlalchemy import inspect,select
from .app.database import version
from .migrations.v0001_initial import upgrade as initial
from .migrations.v0002_trust_boundary import upgrade as trust_upgrade
from .migrations.v0003_conversation import upgrade as conversation_upgrade
from .migrations.v0004_execution import upgrade


def migrate(url,backend='sqlite', *, owner=False, devices=False, research=False, library=False, codex=False):
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
                current=connection.execute(select(version.c.version)).scalar_one()
                changed=upgrade(connection) if current not in (5,6,7,8,9) else False
                if (owner or devices or research or library or codex) and current not in (6,7,8,9):
                    from .migrations.v0005_owner import upgrade as owner_upgrade
                    changed=owner_upgrade(connection) or changed
                if (devices or research or library or codex) and current not in (7,8,9):
                    from .migrations.v0006_device_identity import upgrade as device_upgrade
                    changed=device_upgrade(connection) or changed
                if (research or library or codex) and connection.execute(select(version.c.version)).scalar_one() in (6,7):
                    from .migrations.v0007_research import upgrade as research_upgrade
                    changed=research_upgrade(connection) or changed
                if (library or codex) and connection.execute(select(version.c.version)).scalar_one() != 9:
                    from .migrations.v0008_private_library import upgrade as library_upgrade
                    changed=library_upgrade(connection) or changed
                if codex:
                    from .migrations.v0009_codex import upgrade as codex_upgrade
                    changed=codex_upgrade(connection) or changed
                connection.commit()
                return changed
            except Exception:
                connection.rollback()
                raise
    finally: engine.dispose()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['upgrade'])
    parser.add_argument('--owner',action='store_true')
    parser.add_argument('--devices',action='store_true')
    parser.add_argument('--research',action='store_true')
    parser.add_argument('--library',action='store_true')
    parser.add_argument('--codex',action='store_true')
    args=parser.parse_args()
    changed=migrate(os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL),os.environ.get('LUMA_DATABASE_BACKEND','sqlite'),owner=args.owner,devices=args.devices,research=args.research,library=args.library,codex=args.codex)
    print('Migration applied' if changed else 'Schema already current')

if __name__=='__main__': main()
