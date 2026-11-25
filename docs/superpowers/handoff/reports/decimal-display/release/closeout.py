"""Advance report-only checkout and commit only its infrastructure gitlink."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.request import urlopen

ROOT = Path('/home/joao/docker/stacks/web/images/prumo')
INFRA = Path('/home/joao/docker')
POINTER = 'stacks/web/images/prumo'
RELEASE = '1ad4f16d53adc9bcb59768368aefbf8e1090bf66'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def containers():
    return {item['Name']: {'id': item['Id'], 'image': item['Image'], 'started': item['State']['StartedAt'],
                           'restarts': item['RestartCount'], 'running': item['State']['Running'],
                           'health': item['State'].get('Health', {}).get('Status')}
            for item in json.loads(subprocess.check_output(['docker', 'inspect', 'prumo', 'prumo-ingest', 'prumo-backoffice']))}


def unrelated():
    return hashlib.sha256(subprocess.check_output(['git', '-C', str(INFRA), 'diff', '--binary', 'HEAD', '--', '.', ':!' + POINTER])).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}', args.target)
    report = {'completed': False, 'passed': False, 'target': args.target, 'runtime_release': RELEASE}
    try:
        assert not git(ROOT, 'status', '--porcelain'), 'Dirty deployment checkout'
        assert git(ROOT, 'rev-parse', 'HEAD') == RELEASE
        assert not git(INFRA, 'diff', '--cached', '--name-only'), 'Infrastructure index is not empty'
        git(ROOT, 'fetch', 'origin')
        assert git(ROOT, 'rev-parse', 'origin/main') == args.target
        paths = git(ROOT, 'diff', '--name-only', RELEASE, args.target).splitlines()
        assert paths and all(p.startswith('docs/') for p in paths), paths
        runtime = ('app', 'analysis', 'static', 'ingest', 'backoffice', 'presentation', 'registry', 'Dockerfile', 'entrypoint.sh', 'requirements.txt', 'requirements-dev.txt', '.github')
        git(ROOT, 'diff', '--exit-code', RELEASE, args.target, '--', *runtime)
        report['before'] = containers()
        report['unrelated_infra_before'] = unrelated()
        assert all(c['running'] for c in report['before'].values())
        assert all(report['before'][name]['health'] == 'healthy' for name in ('/prumo', '/prumo-backoffice'))
        git(ROOT, 'merge', '--ff-only', args.target)
        assert git(ROOT, 'rev-parse', 'HEAD') == args.target
        report['after'] = containers()
        assert report['before'] == report['after'], 'A service changed during report checkout advance'
        assert report['unrelated_infra_before'] == unrelated()
        git(INFRA, 'add', '--', POINTER)
        assert git(INFRA, 'diff', '--cached', '--name-only').splitlines() == [POINTER]
        git(INFRA, 'commit', '-m', 'chore(web): record Prumo numeric display release')
        report['infra_commit'] = git(INFRA, 'rev-parse', 'HEAD')
        assert git(INFRA, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').splitlines() == [POINTER]
        assert git(INFRA, 'ls-tree', 'HEAD', POINTER).split()[2] == args.target
        assert report['unrelated_infra_before'] == unrelated(), 'Unrelated infrastructure edit changed'
        assert not git(INFRA, 'diff', '--cached', '--name-only')
        assert not git(ROOT, 'status', '--porcelain')
        report['public'] = []
        for base in ('https://cae.joao.date', 'https://joao.date/dados'):
            with urlopen(base + '/healthz', timeout=30) as response:
                assert response.status == 200
            with urlopen(base + '/pesquisa?q=desemprego+Portugal', timeout=30) as response:
                body = response.read().decode()
                assert response.status == 200 and 'series-result-value' in body and 'Criar caderno' in body
            report['public'].append({'base': base, 'health_and_discovery': True})
        report['report_paths'] = paths
        report['completed'] = True
        report['passed'] = True
    finally:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'passed': report['passed'], 'checkout': args.target, 'infra_commit': report['infra_commit'], 'containers_unchanged': report['before'] == report['after']}))


if __name__ == '__main__':
    main()
