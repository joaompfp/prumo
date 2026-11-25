"""Read-only installed precision acceptance on both Prumo public addresses."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

CHROME = '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'
BASES = ('https://cae.joao.date', 'https://joao.date/dados')
EXAMPLES = (
    ('worldbank.life_expectancy.DE', '80,79', '80.7926829268293'),
    ('worldbank.trade_balance_pct_gdp.DE', '2,36', '2.35673648910157'),
)
LONG_DECIMAL = re.compile(r'\d,\d{3,}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    checks, cases, errors, warnings, outside = [], [], [], [], []
    completed = False

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
            for base in BASES:
                context = browser.new_context()
                page = context.new_page()
                host = urlparse(base).netloc
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: errors.append(message.text) if message.type == 'error'
                        else warnings.append(message.text) if message.type == 'warning' else None)
                page.on('request', lambda request, host=host: outside.append(request.url)
                        if urlparse(request.url).netloc != host else None)
                for width in (320, 390, 768, 1440):
                    page.set_viewport_size({'width': width, 'height': 1000 if width > 768 else 844})
                    for sid, shown, raw in EXAMPLES:
                        label = f'{base}/{sid}/{width}'
                        response = page.goto(base + '/series/' + sid)
                        check(label + ' status', response is not None and response.status == 200)
                        check(label + ' CSP', "default-src 'none'" in response.headers.get('content-security-policy', ''))
                        page.evaluate('document.fonts.ready')
                        expect(page.locator('.chart-readout')).to_contain_text(shown)
                        check(label + ' headline', page.locator('.figure-value').inner_text().split()[0] == shown)
                        check(label + ' raw hidden by default', raw not in page.locator('body').inner_text())
                        check(label + ' no horizontal overflow', page.evaluate(
                            'document.documentElement.scrollWidth <= innerWidth + 1'))
                        payload = json.loads(page.locator('.chart-data').inner_text())
                        check(label + ' payload reader precision', payload['display'][-1][0].startswith(shown))
                        check(label + ' exact original coordinate', payload['y'][-1][0] == float(raw))
                        check(label + ' all payload values bounded', all(not LONG_DECIMAL.search(value)
                              for row in payload['display'] for value in row if value is not None))
                        control = page.locator('.chart-range')
                        control.focus()
                        control.press('Home')
                        expect(page.locator('.chart-readout')).to_contain_text(payload['display'][0][0])
                        control.press('End')
                        expect(page.locator('.chart-readout')).to_contain_text(payload['display'][-1][0])
                        expect(page.locator('.chart-tip-line').nth(1)).to_contain_text(shown)
                        check(label + ' bounded tooltip', not LONG_DECIMAL.search(
                            '\n'.join(page.locator('.chart-tip-line').all_inner_texts())))
                        cells = page.locator('.table-details .data-table tbody td.num')
                        check(label + ' source-detail table cap', cells.count() == min(60, len(payload['y'])))
                        check(label + ' table rounding', not LONG_DECIMAL.search('\n'.join(cells.all_text_contents())))
                        csv = page.request.get(base + '/series/' + sid + '.csv')
                        check(label + ' exact CSV', csv.status == 200 and raw in csv.text())
                        if base.endswith('/dados') and width in (390, 1440):
                            page.locator('.figure-value').scroll_into_view_if_needed()
                            page.locator('.figure-value').locator('..').locator('..').screenshot(
                                path=str(args.output / f'{sid}-{width}.png'))
                        cases.append(label)
                for path in (
                    '/', '/pesquisa?fonte=worldbank&geografia=DE',
                    '/caderno?s=worldbank.life_expectancy.DE&s=worldbank.trade_balance_pct_gdp.DE&escala=dupla',
                    '/comparar/taxas-juro-credito-depositos', '/calculadas/derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct',
                ):
                    response = page.goto(base + path)
                    check(base + path + ' status', response is not None and response.status == 200)
                    page.evaluate('document.fonts.ready')
                    numbers = page.locator('.figure-value, .card-value, .result-value, .series-result-value, .chart-readout')
                    check(base + path + ' populated', numbers.count() > 0)
                    check(base + path + ' bounded reader values', not LONG_DECIMAL.search('\n'.join(numbers.all_inner_texts())))
                    check(base + path + ' no overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                    if '/comparar/' in path:
                        check(base + path + ' no public authoring', page.locator('select[name^="series_"], select[name^="axis_"]').count() == 0)
                asset = page.request.get(base + '/static/css/prumo.css')
                check(base + ' exact installed CSS', asset.status == 200 and asset.body() == (args.root / 'static/css/prumo.css').read_bytes())
                nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
                p = nojs.new_page()
                p.goto(base + '/series/worldbank.life_expectancy.DE')
                check(base + ' nojs headline', p.locator('.figure-value').inner_text().startswith('80,79'))
                check(base + ' nojs SVG', p.locator('svg[role="img"]').count() > 0)
                nojs.close()
                context.close()
            auth = browser.new_context()
            response = auth.request.get('https://joao.date/dados/admin/cms', max_redirects=0)
            check('anonymous Admin remains Authelia protected', response.status in (301, 302, 303, 307)
                  and 'authelia.joao.date' in response.headers.get('location', ''))
            auth.close()
            check('no browser application errors', not errors)
            check('no off-origin browser requests', not outside)
            check('only the existing shared-edge warning', all('Permissions-Policy' in text and 'vr' in text for text in warnings))
            browser.close()
            completed = True
    finally:
        receipt = {'completed': completed, 'passed': completed and all(row['passed'] for row in checks),
                   'checks': checks, 'cases': cases, 'errors': errors, 'warnings': warnings, 'outside': outside}
        (args.output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': receipt['passed'], 'checks': len(checks), 'cases': len(cases),
                          'errors': len(errors), 'warnings': len(warnings), 'outside': len(outside)}))


if __name__ == '__main__':
    main()
