"""Scoped f0nix incident/release receipts. Never prints credentials or mutates source data.

Use fresh receipt paths. The optional online backup is exclusive-created and verified;
no copy/unlink/recovery operation ever targets a live SQLite file or its sidecars.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DATA = Path('/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3')
REPO = Path('/home/joao/docker/stacks/web/images/prumo')
SERVICES = ('prumo-ingest', 'prumo', 'prumo-backoffice')


def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=120)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def collect(backup=None):
    inspections = json.loads(command(['docker', 'inspect', *SERVICES]))
    report = {'at': datetime.now(timezone.utc).isoformat(), 'containers': {}}
    for item in inspections:
        name = item['Name'].removeprefix('/')
        env = dict(x.split('=', 1) for x in item['Config']['Env'] if '=' in x)
        report['containers'][name] = {
            'id': item['Id'], 'image': item['Image'], 'started': item['State']['StartedAt'],
            'restarts': item['RestartCount'], 'running': item['State']['Running'],
            'oom': item['State']['OOMKilled'], 'pid': item['State']['Pid'],
            'health': item['State'].get('Health', {}).get('Status'),
            'faulthandler': env.get('PYTHONFAULTHANDLER'),
            'mounts': [{'source': m['Source'], 'target': m['Destination'], 'rw': m['RW']}
                       for m in item['Mounts'] if m['Destination'] in ('/data', '/data-w')],
        }
    report['checkout'] = command(['git', '-C', str(REPO), 'rev-parse', 'HEAD']).strip()
    report['sqlite_version'] = sqlite3.sqlite_version
    report['files'] = {}
    for suffix in ('', '-wal', '-shm'):
        path = Path(str(DATA) + suffix)
        if path.exists():
            st = path.stat()
            report['files'][suffix or 'main'] = {
                'device': st.st_dev, 'inode': st.st_ino, 'size': st.st_size,
                'mode': oct(st.st_mode & 0o777), 'uid': st.st_uid, 'mtime_ns': st.st_mtime_ns,
            }
    inodes = [str(info['inode']) for info in report['files'].values()]
    report['locks'] = [line for line in Path('/proc/locks').read_text().splitlines()
                       if any(':' + inode + ' ' in line for inode in inodes)]
    # Always a shared-memory-read-only handle, including on this writable host directory.
    # A missing shm is a refusal, not permission to recover it or ignore committed WAL data.
    conn = sqlite3.connect(DATA.resolve().as_uri() + '?mode=ro&readonly_shm=1', uri=True)
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        report['schema'] = digest(conn.execute(
            'SELECT name,type,sql FROM sqlite_master ORDER BY name').fetchall())
        report['migrations'] = [list(row) for row in conn.execute(
            'SELECT version FROM schema_migration ORDER BY version')]
        report['tables'] = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            hasher = hashlib.sha256()
            count = 0
            quoted = name.replace('"', '""')
            for row in conn.execute(f'SELECT * FROM "{quoted}" ORDER BY rowid'):
                hasher.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode())
                hasher.update(b'\n')
                count += 1
            report['tables'][name] = {'rows': count, 'sha256': hasher.hexdigest()}
        report['scheduler'] = [list(row) for row in conn.execute('SELECT * FROM scheduler_state ORDER BY 1')]
        report['running_runs'] = [list(row) for row in conn.execute(
            "SELECT id,source_id,dataset_key,started_at FROM dataset_run WHERE state='running' ORDER BY id")]
        report['quick_check'] = conn.execute('PRAGMA quick_check').fetchone()[0]
        report['foreign_keys'] = [list(row) for row in conn.execute('PRAGMA foreign_key_check')]
        conn.execute('COMMIT')
        assert report['quick_check'] == 'ok' and not report['foreign_keys']
        if backup is not None:
            backup = backup.resolve()
            if backup.parent == DATA.resolve().parent:
                raise ValueError('Recovery copies must be outside the live data directory')
            backup.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            target = sqlite3.connect(backup.as_uri() + '?mode=rw', uri=True)
            try:
                conn.backup(target, pages=256, sleep=0.05)
                assert target.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
                assert not target.execute('PRAGMA foreign_key_check').fetchall()
            finally:
                target.close()
            report['backup'] = {'path': str(backup), 'bytes': backup.stat().st_size,
                                'sha256': hashlib.sha256(backup.read_bytes()).hexdigest()}
    finally:
        conn.close()
    worker_id = report['containers']['prumo-ingest']['id']
    journal = command(['sudo', '-n', 'journalctl', '-u', 'docker', '--since', '2026-11-17',
                       '--no-pager', '-o', 'short-iso'])
    report['worker_daemon_events'] = [line for line in journal.splitlines() if worker_id in line]
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = collect(args.backup)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'at': report['at'],
                      'containers': report['containers'], 'quick_check': report['quick_check'],
                      'backup': report.get('backup')}))


if __name__ == '__main__':
    main()
