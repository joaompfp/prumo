"""Read-only bounded-numeric-text check of real Admin chart previews."""
import argparse
import json
import re
import runpy
import subprocess
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path


class Chart(HTMLParser):
    def __init__(self):
        super().__init__()
        self.svg_depth = 0
        self.svg_text = []
        self.scripts = []
        self.charts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'svg':
            self.svg_depth += 1
            if 'chart' in attrs.get('class', '').split():
                self.charts += 1
        if tag == 'script':
            self.scripts.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'svg':
            self.svg_depth -= 1

    def handle_data(self, data):
        if self.svg_depth:
            self.svg_text.append(data)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--probe', required=True, type=Path)
    args = p.parse_args()
    get = runpy.run_path(str(args.probe))['get']
    cfg = json.loads(subprocess.check_output(['docker', 'inspect', 'prumo-backoffice']))[0]
    env = dict(item.split('=', 1) for item in cfg['Config']['Env'] if '=' in item)
    headers = {'Host': 'joao.date', 'X-Forwarded-Prefix': '/dados/admin',
               'X-Prumo-Proxy-Secret': env['PRUMO_ADMIN_PROXY_SECRET'],
               'Remote-User': env.get('PRUMO_ADMIN_USER', 'joao')}
    slugs = runpy.run_path(str(args.probe.parent / 'admin_probe.py'))['SLUGS']
    checks = []
    completed = False

    def check(name, verdict):
        checks.append({'name': name, 'passed': bool(verdict)})
        assert verdict, name

    try:
        for slug in slugs:
            code, response_headers, body = get('http://100.118.19.6:8089/cms/chart/' + slug + '/preview', headers)
            check(slug + ' preview HTTP200', code == 200)
            parsed = Chart()
            parsed.feed(body.decode())
            check(slug + ' populated static chart', parsed.charts == 1 and len(parsed.svg_text) > 3)
            numbers = re.findall(r'[+-]?\d+(?:\u00a0\d{3})*(?:,\d+)?(?:e[+-]?\d+)?', '\n'.join(parsed.svg_text))
            check(slug + ' four-significant-figure SVG reading', bool(numbers) and all(len(Decimal(n.replace('\u00a0', '').replace(',', '.')).normalize().as_tuple().digits) <= 4 for n in numbers))
            check(slug + ' no executable scripts', all(s.get('type') == 'application/json' and not s.get('src') for s in parsed.scripts))
            lower = {key.lower(): value for key, value in response_headers.items()}
            directives = {part.split()[0]: part.split()[1:] for part in lower.get('content-security-policy', '').split(';') if part.strip()}
            check(slug + ' private strict preview', 'no-store' in lower.get('cache-control', '')
                  and directives.get('script-src', directives.get('default-src', [])) == ["'none'"])
        completed = True
    finally:
        result = {'completed': completed, 'passed': completed and all(c['passed'] for c in checks), 'checks': checks}
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'passed': result['passed'], 'checks': len(checks), 'previews': len(slugs)}))


if __name__ == '__main__':
    main()
