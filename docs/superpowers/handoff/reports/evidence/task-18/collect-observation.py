"""Collect Prumo evidence; require 24 hours unless --snapshot is explicit.

Read-only against running services/data. Writes operator evidence only, never changes
source/licence flags or closes Task 18. Intended for a one-shot local-only cron job.
"""
import argparse
import json
import shlex
import subprocess
from pathlib import Path

REMOTE_OP = '/home/joao/prumo-operations/task18-49a3602'
REMOTE = r'''
import hashlib, json, os, subprocess, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
op = Path('/home/joao/prumo-operations/task18-49a3602')
require_24h = sys.argv[1] == 'true'
start = datetime.fromisoformat((op/'observation-start.txt').read_text().strip())
now = datetime.now(timezone.utc)
elapsed = (now-start).total_seconds()
if require_24h and elapsed < 86400:
    raise SystemExit('24-hour window is still open; no acceptance claimed')

def run(args, body=None):
    result = subprocess.run(args, input=body, capture_output=True, timeout=150)
    if result.returncode:
        raise RuntimeError('evidence command failed: '+args[0]+' '+str(result.returncode))
    return result.stdout

state = json.loads(run(['docker','inspect','prumo-ingest','--format',
    '{"state":{{json .State}},"restarts":{{.RestartCount}},"image":{{json .Image}}}']))
status = json.loads(run(['docker','exec','prumo','python','-m','ingest',
    '--db','/data/prumo.sqlite3','--raw-dir','/data/raw','status','--json']))
audit = json.loads(run(['docker','exec','-i','prumo','python','-'],
    (op/'production-audit.py').read_bytes()))
logs = run(['docker','logs','--since',start.isoformat(),'prumo-ingest']).decode()
records = []
for line in logs.splitlines():
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        continue
    if record.get('schema') == 'prumo-scheduler':
        records.append(record)
attempts = [r for r in records if r.get('event') == 'attempt']
blocked = sorted({r['source'] for r in records if r.get('event') == 'blocked'})
baseline = json.loads((op/'audit-after-import.json').read_text())
legacy_unchanged = baseline['legacy_fingerprint'] == audit['legacy_fingerprint']
assert legacy_unchanged, 'legacy observation fingerprint changed'
summary = {
    'observed_at': now.isoformat(), 'observation_start': start.isoformat(),
    'elapsed_seconds': elapsed, 'elapsed_24h': elapsed >= 86400,
    'worker': state, 'attempt_log_count': len(attempts), 'blocked_sources': blocked,
    'attempt_states': dict(Counter(r['state'] for r in attempts)),
    'legacy_observations_unchanged': legacy_unchanged,
    'integrity': audit['integrity'], 'licence_violations': audit['licence_violations'],
    'served_by_source': audit['served_by_source'],
    'sources': [], 'task_18_closed': False,
    'acceptance': 'controller review required; source exceptions remain explicit'
}
for source in status['sources']:
    active = [s for s in source['series'] if s['active']]
    summary['sources'].append({
        'name': source['name'], 'active': len(active), 'blockers': source['blockers'],
        'availability': dict(Counter(s['availability'] for s in active)),
        'stale_active': sum(s['stale'] is True for s in active),
        'never_verified_active': sum(s['last_verified'] is None for s in active),
        'last_verified': source['last_verified'], 'real_data_fetched_at': source['real_data_fetched_at'],
        'pending_runs': len(source['pending_runs']), 'datasets': source['datasets']})
# Probe the actual maintenance responses without printing bodies or following a claimed
# health state from container uptime. These are GETs, not outbound user communications.
import urllib.request
public = []
for url in ['http://100.118.19.6:8088/healthz','https://cae.joao.date/','https://joao.date/dados/']:
    with urllib.request.urlopen(url, timeout=20) as response:
        text = response.read().decode()
        is_health = url.endswith('/healthz')
        assert response.status == 200
        assert json.loads(text)['status'] == 'ok' if is_health else 'Em manutenção' in text
        public.append({'url':url,'status':response.status,'maintenance':not is_health})
summary['public_checks'] = public
if require_24h:
    assert state['state']['Running'] and not state['state']['OOMKilled']
    assert state['restarts'] == 0, 'restarts require a new reviewed observation window'
    assert attempts and 'dgeg' in blocked, 'missing scheduler log evidence'
stamp = now.strftime('%Y%m%dT%H%M%SZ')
files = {'status-'+stamp+'.json':status, 'audit-'+stamp+'.json':audit,
         'summary-'+stamp+'.json':summary}
for name, value in files.items():
    p = op/name
    payload = json.dumps(value, indent=2, sort_keys=True).encode()+b'\n'
    with p.open('xb') as f:
        f.write(payload)
    assert p.read_bytes() == payload
(op/('worker-'+stamp+'.log')).write_text(logs)
print(json.dumps({'summary':summary,'remote_evidence_dir':str(op),'files':list(files)}, sort_keys=True))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', action='store_true', help='collect an explicitly non-final snapshot')
    args = parser.parse_args()
    command = 'python3 -c '+shlex.quote(REMOTE)+' '+str(not args.snapshot).lower()
    result = subprocess.run(['ssh','-o','BatchMode=yes','f0nix',command],
                            capture_output=True, text=True, timeout=210)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or 'remote evidence collection failed')
    receipt = json.loads(result.stdout)
    out = Path('/home/joao/prumo-operations/task18-49a3602')
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = receipt['summary']['observed_at'].replace(':','').replace('+','_')
    target = out/('receipt-'+stamp+'.json')
    payload = json.dumps(receipt, indent=2, sort_keys=True)+'\n'
    target.write_text(payload)
    assert target.read_text() == payload
    print(json.dumps({'receipt':str(target),'elapsed_24h':receipt['summary']['elapsed_24h'],
                      'task_18_closed':False,'summary':receipt['summary']}, indent=2))


if __name__ == '__main__':
    main()
