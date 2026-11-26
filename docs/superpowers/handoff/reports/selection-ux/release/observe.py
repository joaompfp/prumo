"""Bounded foreground reader-release observation, without data writes."""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--minimum-uptime', type=int, default=900)
    args = parser.parse_args()
    before = json.loads(args.baseline.read_text())['containers']
    latest_start = max(datetime.fromisoformat(before[name]['started'].replace('Z', '+00:00')) for name in ('prumo', 'prumo-backoffice'))
    samples = []
    complete = False
    try:
        while True:
            current = {}
            for item in json.loads(subprocess.check_output(['docker', 'inspect', 'prumo', 'prumo-ingest', 'prumo-backoffice'])):
                current[item['Name'].removeprefix('/')] = {
                    'id': item['Id'], 'image': item['Image'], 'started': item['State']['StartedAt'],
                    'restarts': item['RestartCount'], 'running': item['State']['Running'],
                    'health': item['State'].get('Health', {}).get('Status'),
                }
            at = datetime.now(timezone.utc)
            elapsed = (at - latest_start).total_seconds()
            verdict = current == before
            samples.append({'at': at.isoformat(), 'reader_minimum_uptime_seconds': elapsed, 'containers_match': verdict})
            assert verdict, 'A service identity/image/start/restart/readiness field changed during observation'
            assert all(current[name]['health'] == 'healthy' and current[name]['restarts'] == 0 for name in ('prumo', 'prumo-backoffice'))
            if elapsed >= args.minimum_uptime:
                complete = True
                break
            args.output.write_text(json.dumps({'completed': False, 'passed': False, 'samples': samples}, indent=2))
            time.sleep(min(30, args.minimum_uptime - elapsed))
    finally:
        result = {'completed': complete, 'passed': complete and all(row['containers_match'] for row in samples),
                  'required_uptime_seconds': args.minimum_uptime, 'samples': samples}
        args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({'passed': result['passed'], 'samples': len(samples), 'reader_minimum_uptime_seconds': samples[-1]['reader_minimum_uptime_seconds']}))


if __name__ == '__main__':
    main()
