"""Reconcile original CSV hashes allowing only the documented export-clock footer."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--before', required=True, type=Path)
    p.add_argument('--after', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    before = json.loads(args.before.read_text())
    after = json.loads(args.after.read_text())
    checks = []
    result = {'completed': False, 'passed': False, 'checks': checks, 'exports': []}

    def check(label, verdict):
        checks.append({'name': label, 'passed': bool(verdict)})
        assert verdict, label

    try:
        check('same complete route population', set(before['cases']) == set(after['cases']) and len(before['cases']) == 8)
        for route, old in before['cases'].items():
            current = after['cases'][route]
            check(route + ' original coordinates unchanged', old['geometry_sha256'] == current['geometry_sha256']
                  and old['point_rows'] == current['point_rows'])
            if 'csv_sha256' not in old:
                continue
            with urlopen(route + '.csv', timeout=30) as response:
                check(route + ' CSV HTTP200', response.status == 200)
                raw = response.read()
            pattern = re.compile(rb'(?m)^Exportado a (\d{2}/\d{2}/\d{4}, \d{2}:\d{2} UTC)\r?$')
            found = list(pattern.finditer(raw))
            check(route + ' single documented footer clock', len(found) == 1)
            # The old probe retained whole raw hashes, not normalized bytes. Reconstruct
            # only its known clock line and require exact original-hash equality.
            stamps = {}
            for name, receipt, source in (('before', before, args.before), ('after', after, args.after)):
                at = datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).replace(second=0, microsecond=0)
                matches = []
                for minutes in range(4):
                    stamp = (at - timedelta(minutes=minutes)).strftime('%d/%m/%Y, %H:%M UTC').encode()
                    a, b = found[0].span(1)
                    reconstructed = raw[:a] + stamp + raw[b:]
                    if digest(reconstructed) == receipt['cases'][route]['csv_sha256']:
                        matches.append(stamp.decode())
                check(route + ' exact ' + name + ' bytes except export clock', len(matches) == 1)
                stamps[name] = matches[0]
            check(route + ' original CSV length unchanged', old['csv_bytes'] == current['csv_bytes'] == len(raw))
            result['exports'].append({'route': route, 'matched_export_clocks': stamps,
                                      'canonical_body_sha256': digest(pattern.sub(b'Exportado a <clock>', raw))})
        result['completed'] = True
        result['passed'] = True
    finally:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'passed': result['passed'], 'checks': len(checks), 'exports': len(result['exports'])}))


if __name__ == '__main__':
    main()
