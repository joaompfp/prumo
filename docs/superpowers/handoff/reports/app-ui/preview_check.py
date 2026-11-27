"""Read-only acceptance of shared app styling in the private static CMS preview."""
import argparse
import json
import runpy
import subprocess
from html.parser import HTMLParser
from pathlib import Path


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.links = []
        self.scripts = []
        self.nav_links = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link':
            self.assets.append(attrs.get('href', ''))
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
            self.nav_links += 'app-nav-link' in (attrs.get('class') or '').split()
        if tag == 'script':
            self.scripts.append(attrs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    args = parser.parse_args()
    get = runpy.run_path(str(args.probe))['get']
    item = json.loads(subprocess.check_output(['docker', 'inspect', 'prumo-backoffice']))[0]
    env = dict(value.split('=', 1) for value in item['Config']['Env'] if '=' in value)
    headers = {'Host': 'joao.date', 'X-Forwarded-Prefix': '/dados/admin',
               'X-Prumo-Proxy-Secret': env['PRUMO_ADMIN_PROXY_SECRET'],
               'Remote-User': env.get('PRUMO_ADMIN_USER', 'joao')}
    root = Path('/home/joao/docker/stacks/web/images/prumo')
    checks = []

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        assert condition, name

    complete = False
    try:
        for route in ('/cms/page/inicio/preview', '/cms/chart/taxas-juro-credito-depositos/preview'):
            status, response_headers, body = get('http://100.118.19.6:8089' + route, headers)
            check('private preview HTTP 200', status == 200)
            doc = Document()
            doc.feed(body.decode())
            policy = {part.split()[0]: part.split()[1:] for part in
                      next(value for key, value in response_headers.items() if key.lower() == 'content-security-policy').split(';') if part.strip()}
            check('static preview has no executable scripts', all(s.get('type') == 'application/json' and not s.get('src') for s in doc.scripts))
            check('static preview strict script policy', policy.get('script-src', policy.get('default-src')) == ["'none'"])
            check('shared primary app navigation present', doc.nav_links == 3)
            check('preview links keep public base', all('/dados' + path in doc.links for path in ('/pesquisa', '/comparar', '/caderno')))
            for name in ('app-shell.css', 'workspace.css', 'chart-inspector.css', 'discovery.css'):
                check('preview uses admin asset prefix ' + name, '/dados/admin/static/css/' + name in doc.assets)
                status, _, asset = get('http://100.118.19.6:8089/static/css/' + name, headers)
                check('preview exact asset bytes ' + name, status == 200 and asset == (root / 'static/css' / name).read_bytes())
        complete = True
    finally:
        args.output.write_text(json.dumps({'completed': complete, 'passed': complete and all(c['passed'] for c in checks), 'checks': checks}, indent=2))
        print(json.dumps({'completed': complete, 'checks': len(checks)}))


if __name__ == '__main__':
    main()
