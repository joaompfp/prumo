"""Read-only browser proof for the installed legibility/notebook/country release."""
import gzip
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(os.environ['PRUMO_PROD_OUT']).resolve()
OUT.mkdir(parents=True, exist_ok=False)
BASES = ('https://cae.joao.date', 'https://joao.date/dados')
SLUGS = ('eletricidade-domestica', 'pib-por-habitante', 'divida-publica')
report = {'checks': [], 'errors': [], 'warnings': [], 'external': [], 'assets': {}}


def check(name, condition):
    report['checks'].append({'check': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)


def exact(payload, index):
    return payload['periods'][index] + ' - ' + '; '.join(
        f'{item["title"]}: {payload["display"][index][i]}'
        for i, item in enumerate(payload['series']))


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',
            args=['--no-sandbox'])
        for base in BASES:
            context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            origin = base.split('/dados')[0]
            context.on('request', lambda r, allowed=origin: report['external'].append(r.url)
                       if not r.url.startswith(allowed + '/') else None)
            page = context.new_page()
            page.on('pageerror', lambda e: report['errors'].append(str(e)))
            page.on('console', lambda m: report['errors'].append(m.text) if m.type == 'error'
                    else report['warnings'].append(m.text) if m.type == 'warning' else None)
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({'width': width, 'height': 1100})
                for route in ('/', '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT',
                              '/comparar/paises/eletricidade-domestica'):
                    response = page.goto(base + route)
                    tag = f'{base}{route} {width}'
                    check(tag + ' HTTP200', response is not None and response.status == 200)
                    page.evaluate('document.fonts.ready')
                    check(tag + ' root/body28.05', page.evaluate(
                        'Math.abs(parseFloat(getComputedStyle(document.body).fontSize)-28.05)<0.01'))
                    check(tag + ' local fonts', page.evaluate("document.fonts.check('28px Lato')"))
                    check(tag + ' no page overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    check(tag + ' authored punctuation', chr(0x2014) not in page.locator('body').inner_text())
                    if route == '/':
                        check(tag + ' existing twelve cards', page.locator('.card-value').count() == 12)
                        check(tag + ' lightweight summaries', page.locator('script').count() == 0)
                        check(tag + ' carmim', page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()") == '#9b1c2e')
                        if width in (390, 1440):
                            suffix = 'mounted' if '/dados' in base else 'direct'
                            page.screenshot(path=str(OUT / f'home-{suffix}-{width}.png'))
                    elif route.startswith('/caderno'):
                        check(tag + ' two cards scriptfree', page.locator('.cards .card').count() == 2 and page.locator('script').count() == 0)
                    else:
                        page.locator('.chart-enhanced canvas').wait_for()
                        payload = json.loads(page.locator('script.chart-data').inner_text())
                        check(tag + ' five countries complete table', len(payload['series']) == 5
                              and page.locator('.country-table tbody tr').count() == len(payload['x']))
                        slider = page.locator('.chart-range')
                        slider.focus()
                        for key, index in (('Home', 0), ('End', -1)):
                            slider.press(key)
                            check(tag + ' exact keyboard ' + key, page.locator('.chart-readout').inner_text() == exact(payload, index))
                        if width == 1440:
                            page.locator('.chart-figure').scroll_into_view_if_needed()
                            suffix = 'mounted' if '/dados' in base else 'direct'
                            page.screenshot(path=str(OUT / f'electricity-{suffix}-1440.png'))
            for route in ('/healthz', '/comparar', '/fontes', '/metodologia', '/paginas',
                          '/series/ine.hicp_yoy.PT', '/series/ine.hicp_yoy.PT.csv',
                          '/comparar/credito-e-taxa', *(f'/comparar/paises/{slug}' for slug in SLUGS)):
                response = context.request.get(base + route)
                check(base + route + ' HTTP200', response.status == 200)
            for asset in ('static/css/prumo.css', 'static/css/fonts.css',
                          'static/images/prumo/favicon.svg', 'static/js/prumo-charts.min.js'):
                response = context.request.get(base + '/' + asset)
                data = response.body()
                check(base + '/' + asset + ' exact bytes', response.status == 200 and data == (ROOT / asset).read_bytes())
                report['assets'][base + '/' + asset] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            page.goto(base + '/comparar/credito-e-taxa')
            page.locator('.chart-enhanced canvas').wait_for()
            payload = json.loads(page.locator('script.chart-data').inner_text())
            check(base + ' prior two-axis comparison', len(payload['axes']) == 2)
            check(base + ' unknown404', context.request.get(base + '/comparar/paises/inexistente').status == 404)
            check(base + ' strict script policy', "script-src 'self'" in context.request.get(base + '/comparar/paises/eletricidade-domestica').headers.get('content-security-policy', ''))
            context.close()
        context = browser.new_context()
        response = context.request.get('https://joao.date/dados/admin/cms/page/inicio', max_redirects=0)
        check('Admin still challenges through Authelia', response.status in (302, 303, 307)
              and response.headers.get('location', '').startswith('https://authelia.joao.date/'))
        context.close()
        browser.close()
    check('no off-origin public requests', not report['external'])
    check('no page or CSP errors', not report['errors'])
    known = [w for w in report['warnings'] if 'Permissions-Policy' in w and 'vr' in w]
    check('no unexpected warnings', len(known) == len(report['warnings']))
    report['known_shared_edge_vr_warnings'] = len(known)
    request = Request(BASES[1] + '/static/js/prumo-charts.min.js', headers={'Accept-Encoding': 'gzip'})
    with urlopen(request, timeout=40) as response:
        wire = response.read()
        encoding = response.headers.get('Content-Encoding', '')
        body = gzip.decompress(wire) if encoding == 'gzip' else wire
        check('actual edge bundle transfer', body == (ROOT / 'static/js/prumo-charts.min.js').read_bytes())
        report['transfer'] = {'content_encoding': encoding, 'wire_body_bytes': len(wire),
                              'decoded_bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    report['complete'] = True


try:
    main()
finally:
    (OUT / 'public-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'complete': report.get('complete', False), 'checks': len(report['checks']),
                      'errors': report['errors'], 'known_edge_warnings': report.get('known_shared_edge_vr_warnings')}))
