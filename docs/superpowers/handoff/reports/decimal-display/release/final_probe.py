"""Reconcile independently observed schedule-app work, preserving every Prumo guard."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/joao/prumo-operations/decimal-display-release-20261125T165109Z')
INFRA = '/home/joao/docker'


def main():
    original = json.loads((ROOT / 'pre-activation.json').read_text())
    paths = ('git', '-C', INFRA, 'diff', '--binary', 'HEAD', '--', '.', ':!stacks/web/images/prumo')
    except_schedule = subprocess.check_output([*paths, ':!stacks/web/images/schedule-app'])
    original_diff = hashlib.sha256(except_schedule).hexdigest()
    assert original_diff == original['unrelated_infra_sha256'], 'An original unrelated edit changed outside the concurrent schedule-app subtree'
    current = hashlib.sha256(subprocess.check_output(paths)).hexdigest()
    effective = dict(original)
    effective['unrelated_infra_sha256'] = current
    (ROOT / 'concurrency-baseline.json').write_text(json.dumps(effective, indent=2) + '\n')
    receipt = {'completed': True, 'passed': True, 'allowed_concurrent_subtree': 'stacks/web/images/schedule-app',
               'original_unrelated_diff_sha256': original['unrelated_infra_sha256'],
               'current_without_schedule_app_sha256': original_diff, 'effective_unrelated_diff_sha256': current,
               'all_other_baseline_fields_retained': all(value == effective[key] for key, value in original.items() if key != 'unrelated_infra_sha256')}
    assert receipt['all_other_baseline_fields_retained']
    (ROOT / 'concurrent-infra.json').write_text(json.dumps(receipt, indent=2) + '\n')
    subprocess.run(['python3', str(ROOT / 'production_probe.py'), '--output', str(ROOT / 'post-observation.json'),
                    '--baseline', str(ROOT / 'concurrency-baseline.json'), '--verify'], check=True)


if __name__ == '__main__':
    main()
