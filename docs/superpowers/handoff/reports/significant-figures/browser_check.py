"""Read-only significant-figure QA, using actual chart payloads and public exports."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

CHROME = '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'
NUMBER = re.compile(r'(?<!\w)[+-]?\d+(?:\u00a0\d{3})*(?:,\d+)?(?:e[+-]?\d+)?')
EXAMPLES = (
    ('worldbank.life_expectancy.DE', '80,79', '80.7926829268293'),
    ('worldbank.trade_balance_pct_gdp.DE', '2,357', '2.35673648910157'),
)


def bounded(text):
    values = [Decimal(m.group().replace('\u00a0', '').replace(',', '.'))
              for m in NUMBER.finditer(text)]
    return bool(values) and all(len(v.normalize().as_tuple().digits) <= 4 for v in values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--db', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    before = hashlib.sha256(args.db.read_bytes()).hexdigest() if args.db else None
    checks, cases, errors, warnings, outside = [], [], [], [], []
    completed = False

    def check(name, verdict):
        checks.append({'name': name, 'passed': bool(verdict)})
        assert verdict, name

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
            for base in args.base:
                context = browser.new_context()
                page = context.new_page()
                host = urlparse(base).netloc
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error'
                        else warnings.append(msg.text) if msg.type == 'warning' else None)
                page.on('request', lambda req, host=host: outside.append(req.url)
                        if urlparse(req.url).netloc != host else None)
                for width in (320, 390, 768, 1440):
                    page.set_viewport_size({'width': width, 'height': 1000 if width > 768 else 844})
                    for sid, shown, raw in EXAMPLES:
                        label = f'{base}/{sid}/{width}'
                        response = page.goto(base + '/series/' + sid)
                        assert response is not None
                        check(label + ' HTTP200', response.status == 200)
                        check(label + ' strict CSP', "default-src 'none'" in response.headers.get('content-security-policy', ''))
                        page.evaluate('document.fonts.ready')
                        expect(page.locator('.chart-readout')).to_contain_text(shown)
                        check(label + ' headline', page.locator('.figure-value').inner_text().split()[0] == shown)
                        check(label + ' original not printed by default', raw not in page.locator('body').inner_text())
                        check(label + ' no page overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                        payload = json.loads(page.locator('.chart-data').inner_text())
                        check(label + ' payload display', payload['display'][-1][0].startswith(shown))
                        check(label + ' unchanged coordinate', payload['y'][-1][0] == float(raw))
                        check(label + ' all plotted readings bounded', all(bounded(v) for row in payload['display'] for v in row if v is not None))
                        control = page.locator('.chart-range')
                        control.focus()
                        control.press('Home')
                        expect(page.locator('.chart-readout')).to_contain_text(payload['display'][0][0])
                        control.press('End')
                        expect(page.locator('.chart-readout')).to_contain_text(payload['display'][-1][0])
                        expect(page.locator('.chart-tip-line').nth(1)).to_contain_text(shown)
                        check(label + ' tooltip', bounded(page.locator('.chart-tip-line').nth(1).inner_text()))
                        cells = page.locator('.table-details .data-table tbody td.num')
                        check(label + ' table population', cells.count() == min(60, len(payload['y'])))
                        check(label + ' all table readings bounded', all(bounded(v) for v in cells.all_text_contents()))
                        csv = page.request.get(base + '/series/' + sid + '.csv')
                        check(label + ' original CSV', csv.status == 200 and raw in csv.text())
                        if width in (390, 1440):
                            page.locator('.figure-value').scroll_into_view_if_needed()
                            page.locator('.figure-value').locator('..').locator('..').screenshot(path=str(args.output / f'{host.replace(":", "_")}-{sid}-{width}.png'))
                        cases.append(label)
                for path in (
                    '/', '/pesquisa?fonte=worldbank&geografia=DE',
                    '/caderno?s=worldbank.life_expectancy.DE&s=worldbank.trade_balance_pct_gdp.DE&escala=dupla',
                    '/comparar/taxas-juro-credito-depositos', '/comparar/eletricidade-domestica',
                    '/calculadas/derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct',
                ):
                    response = page.goto(base + path)
                    assert response is not None
                    check(base + path + ' HTTP200', response.status == 200)
                    page.evaluate('document.fonts.ready')
                    numbers = page.locator('.figure-value, .card-value, .result-value, .series-result-value, .chart-readout')
                    check(base + path + ' populated', numbers.count() > 0)
                    check(base + path + ' four significant figures', all(bounded(t) for t in numbers.all_inner_texts()))
                    check(base + path + ' no overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                    if '/comparar/' in path:
                        check(base + path + ' no public composition controls', page.locator('select[name^="series_"], select[name^="axis_"]').count() == 0)
                methodology = page.request.get(base + '/metodologia')
                check(base + ' methodology current', methodology.status == 200 and 'até quatro algarismos significativos' in methodology.text() and 'duas casas decimais' not in methodology.text())
                css = page.request.get(base + '/static/css/prumo.css')
                check(base + ' CSS unchanged', css.status == 200 and css.body() == (args.root / 'static/css/prumo.css').read_bytes())
                nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
                fallback = nojs.new_page()
                fallback.goto(base + '/series/worldbank.trade_balance_pct_gdp.DE')
                check(base + ' no-JS headline', fallback.locator('.figure-value').inner_text().startswith('2,357'))
                check(base + ' no-JS SVG', fallback.locator('svg[role="img"]').count() > 0)
                nojs.close()
                context.close()
            check('no application errors', not errors)
            check('no external requests', not outside)
            check('only pre-existing edge warning', all('Permissions-Policy' in w and 'vr' in w for w in warnings))
            browser.close()
            completed = True
    finally:
        if args.db:
            checks.append({'name': 'isolated DB bytes unchanged', 'passed': before == hashlib.sha256(args.db.read_bytes()).hexdigest()})
        receipt = {'completed': completed, 'passed': completed and all(c['passed'] for c in checks),
                   'checks': checks, 'cases': cases, 'errors': errors, 'warnings': warnings, 'outside': outside}
        (args.output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': receipt['passed'], 'checks': len(checks), 'cases': len(cases), 'warnings': len(warnings)}))


if __name__ == '__main__':
    main()
