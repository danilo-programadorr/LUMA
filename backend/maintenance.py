"""Local SQLite maintenance adapter, separate from portable business repositories."""
from contextlib import closing
import argparse
import os
import sqlite3
from pathlib import Path
from .app.database import DEFAULT_URL,ROOT,database_path
from .app.models import ident


def backup(url):
    source=database_path(url)
    if not source.is_file(): raise ValueError('DATABASE_NOT_FOUND')
    folder=ROOT/'runtime/backups';folder.mkdir(parents=True,exist_ok=True)
    target=folder/('luma-backup-'+ident()+'.db')
    # SQLite backup creates a consistent snapshot even if another connection writes.
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as origin:
        with closing(sqlite3.connect(target)) as destination:
            origin.backup(destination)
            if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('BACKUP_INTEGRITY_FAILED')
    return target


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['backup'])
    parser.parse_args()
    print(backup(os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL)))

if __name__=='__main__': main()
