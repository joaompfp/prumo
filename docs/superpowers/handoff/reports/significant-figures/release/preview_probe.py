"""Read-only check of the installed Admin's shared public-preview navigation."""
import argparse
import json
import runpy
import subprocess
from html.parser import HTMLParser
from pathlib import Path


class Preview(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.links = []
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'script':
            self.scripts.append(attributes)
        if tag == 'a':
            self.links.append(attributes.get('href', ''))
        if tag in ('link', 'img'):
            self.assets.append(attributes.get('href', attributes.get('src', '')))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path('/home/joao/docker/stacks/web/images/prumo')
    probe = runpy.run_path(str(root / 'docs/superpowers/handoff/reports/tabler-ui/production_probe.py'))
    item = json.loads(subprocess.check_output(['docker', 'inspect', 'prumo-backoffice']))[0]
    env = dict(value.split('=', 1) for value in item['Config']['Env'] if '=' in value)
    headers = {'Host': 'joao.date', 'X-Forwarded-Prefix': '/dados/admin',
               'X-Prumo-Proxy-Secret': env['PRUMO_ADMIN_PROXY_SECRET'],
               'Remote-User': env.get('PRUMO_ADMIN_USER', 'joao')}
    status, response_headers, body = probe['get']('http://100.118.19.6:8089/cms/page/inicio/preview', headers)
    text = body.decode()
    document = Preview()
    document.feed(text)
    lower = {key.lower(): value for key, value in response_headers.items()}
    directives = {part.split()[0]: part.split()[1:] for part in lower.get('content-security-policy', '').split(';') if part.strip()}
    checks = {
        'preview HTTP200': status == 200,
        'shared new masthead': 'wrap masthead' in text,
        'shared destination rail': 'destination-rail' in text,
        'shared native mobile menu': 'class="nav-menu"' in text,
        'public Caderno link': '/dados/caderno' in document.links,
        'public comparison link': '/dados/comparar' in document.links,
        'Admin-prefixed public CSS': '/dados/admin/static/css/prumo.css' in document.assets,
        'no executable scripts': all(script.get('type') == 'application/json' and not script.get('src') for script in document.scripts),
        'static script CSP': directives.get('script-src', directives.get('default-src', [])) == ["'none'"],
        'preview remains private': 'no-store' in lower.get('cache-control', ''),
    }
    checks['public catalogue link'] = '/dados/pesquisa' in document.links
    checks['new discovery CSS'] = '/dados/admin/static/css/discovery.css' in document.assets
    checks['CMS card notebook action'] = 'card-create' in text
    args.output.write_text(json.dumps({'checks': checks, 'passed': all(checks.values())}, indent=2))
    print(json.dumps({'checks': len(checks), 'passed': all(checks.values())}))
    assert all(checks.values()), {key: value for key, value in checks.items() if not value}


if __name__ == '__main__':
    main()
