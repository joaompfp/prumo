"""Advance report-only code and its infrastructure pointer without a reader rollout."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--sha', required=True)
args = parser.parse_args()
root = Path('/home/joao/docker/stacks/web/images/prumo')
infra = Path('/home/joao/docker')
op = Path('/home/joao/prumo-operations/frontend-toolkit-20261127')


def git(directory, *arguments):
    return subprocess.check_output(['git', '-C', str(directory), *arguments])


def snapshot(name):
    subprocess.run(['python3', str(op / 'production_probe.py'), '--output', str(op / name)], check=True)
    return json.loads((op / name).read_text())


assert not git(root, 'status', '--porcelain').strip()
git(root, 'fetch', 'origin', 'main')
assert git(root, 'rev-parse', 'origin/main').decode().strip() == args.sha
paths = git(root, 'diff', '--name-only', 'HEAD', args.sha).decode().splitlines()
assert paths and all(path.startswith('docs/') for path in paths), paths
before = snapshot('before-docs.json')
# Keep the operator directory private but Git-materialised source/documentation readable.
os.umask(0o022)
git(root, 'merge', '--ff-only', args.sha)
after = snapshot('after-docs.json')
for key in ('containers', 'schema', 'migrations', 'cms', 'unrelated_infra_sha256'):
    assert before[key] == after[key], key
assert not git(infra, 'diff', '--cached', '--name-only').strip(), 'Preserve another operator index'
relative = 'stacks/web/images/prumo'
assert git(infra, 'ls-files', '--stage', '--', relative).startswith(b'160000 ')
unrelated = git(infra, 'diff', '--binary', 'HEAD', '--', '.', ':!' + relative)
git(infra, 'add', '--', relative)
assert git(infra, 'diff', '--cached', '--name-only').decode().splitlines() == [relative]
git(infra, 'commit', '-m', 'chore(prumo): record compact public component release')
assert git(infra, 'diff', '--binary', 'HEAD', '--', '.', ':!' + relative) == unrelated
assert git(infra, 'rev-parse', 'HEAD:' + relative).decode().strip() == args.sha
result = {'code': git(root, 'rev-parse', 'HEAD').decode().strip(),
          'infra_commit': git(infra, 'rev-parse', 'HEAD').decode().strip(),
          'containers_unchanged': True, 'schema_cms_unchanged': True,
          'unrelated_infra_sha256': hashlib.sha256(unrelated).hexdigest(),
          'changed_report_paths': paths}
(op / 'closeout.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
