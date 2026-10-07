"""Explicit, restart-safe backfill for historical events. Run after migrations."""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from app.fingerprints import fingerprint


def backfill(connection):
    last = None
    updated = 0
    while True:
        with connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
            rows = cursor.execute('''SELECT id,exception_type,stack_trace FROM events
                WHERE fingerprint IS NULL AND exception_type IS NOT NULL AND stack_trace IS NOT NULL
                AND (%s::uuid IS NULL OR id>%s::uuid) ORDER BY id LIMIT 500''', (last, last)).fetchall()
            if not rows:
                return updated
            for row in rows:
                value = fingerprint(row['exception_type'], row['stack_trace'])
                if value:
                    updated += cursor.execute('UPDATE events SET fingerprint=%s WHERE id=%s AND fingerprint IS NULL',
                                              (value, row['id'])).rowcount
            last = rows[-1]['id']


if __name__ == '__main__':
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    with psycopg.connect(os.environ['DATABASE_URL'], autocommit=True) as connection:
        print(f'Fingerprints added: {backfill(connection)}')
