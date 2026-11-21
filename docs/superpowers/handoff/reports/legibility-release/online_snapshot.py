"""Read-only-source online backup for isolated acceptance, not a backup service."""
import argparse
import json
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source_path = Path('/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3')
if args.output.exists():
    raise FileExistsError(args.output)
args.output.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(f'file:{source_path}?mode=ro&readonly_shm=1', uri=True) as source:
    with sqlite3.connect(args.output) as target:
        source.backup(target)
        integrity = target.execute('PRAGMA quick_check').fetchone()[0]
        foreign_keys = target.execute('PRAGMA foreign_key_check').fetchall()
        if integrity != 'ok' or foreign_keys:
            raise RuntimeError('Acceptance snapshot failed checks')
print(json.dumps({'output': str(args.output), 'bytes': args.output.stat().st_size,
                  'quick_check': integrity, 'foreign_keys': foreign_keys}))
