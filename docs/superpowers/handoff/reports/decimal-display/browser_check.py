"""Read-only numeric-display QA on an archived production copy, never a live DB."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

CHROME = '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', required=True)
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if urlparse(args.origin).hostname not in ('127.0.0.1', 'localhost'):
        raise ValueError('Isolated local server required')
    db = args.db.resolve(strict=True)
    if not db.is_relative_to(Path('/home/joao/.hermes/cache/scratch')):
        raise ValueError('Isolated scratch database required')
    args.output.mkdir(parents=True, exist_ok=False)
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    checks, errors, outside, cases = [], [], [], []
    completed = False

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
            context = browser.new_context()
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text)
                    if message.type in ('error', 'warning') else None)
            page.on('request', lambda request: outside.append(request.url)
                    if not request.url.startswith(args.origin + '/') else None)
            for base in ('', '/dados'):
                for width in (320, 390, 768, 1024, 1440):
                    page.set_viewport_size({'width': width, 'height': 1000 if width > 768 else 844})
                    for sid, shown, raw in (
                        ('worldbank.life_expectancy.DE', '80,79', '80.7926829268293'),
                        ('worldbank.trade_balance_pct_gdp.DE', '2,36', '2.35673648910157'),
                    ):
                        label = f'{base}/{sid}/{width}'
                        response = page.goto(args.origin + base + '/series/' + sid)
                        check(label + ' status', response is not None and response.status == 200)
                        page.evaluate('document.fonts.ready')
                        expect(page.locator('.chart-readout')).to_contain_text(shown)
                        figure = page.locator('.figure-value')
                        check(label + ' headline', figure.inner_text().split()[0] == shown)
                        check(label + ' raw hidden', raw not in page.locator('body').inner_text())
                        check(label + ' overflow', page.evaluate(
                            'document.documentElement.scrollWidth <= innerWidth + 1'))
                        payload = json.loads(page.locator('.chart-data').inner_text())
                        check(label + ' display', payload['display'][-1][0].startswith(shown))
                        check(label + ' geometry', payload['y'][-1][0] == float(raw))
                        # A real keyboard selection also exercises tooltip/readout formatting.
                        control = page.locator('.chart-range')
                        control.focus()
                        control.press('Home')
                        expect(page.locator('.chart-readout')).to_contain_text(payload['display'][0][0])
                        control.press('End')
                        expect(page.locator('.chart-readout')).to_contain_text(payload['display'][-1][0])
                        expect(page.locator('.chart-tip-line')).to_have_count(2)
                        expect(page.locator('.chart-tip-line').nth(1)).to_contain_text(shown)
                        check(label + ' tooltip bounded', not re.search(
                            r'\d,\d{3,}', '\n'.join(page.locator('.chart-tip-line').all_inner_texts())))
                        # Capture the original bug's card, at the real reading scale.
                        if base == '/dados' and width in (390, 1440):
                            figure.scroll_into_view_if_needed()
                            figure.locator('..').locator('..').screenshot(
                                path=str(args.output / f'{sid}-{width}.png'))
                        csv = page.request.get(args.origin + base + '/series/' + sid + '.csv')
                        check(label + ' exact CSV', csv.status == 200 and raw in csv.text())
                        cases.append(label)
            for path in (
                '/dados/pesquisa?fonte=worldbank',
                '/dados/caderno?s=worldbank.life_expectancy.DE&s=worldbank.trade_balance_pct_gdp.DE&escala=dupla',
                '/dados/comparar/taxas-juro-credito-depositos',
                '/dados/admin/cms/chart/taxas-juro-credito-depositos/preview',
            ):
                page.set_viewport_size({'width': 1440, 'height': 1000})
                response = page.goto(args.origin + path)
                check(path + ' status', response is not None and response.status == 200)
                page.evaluate('document.fonts.ready')
                if 'preview' in path:
                    check(path + ' static preview', page.locator('script[src]').count() == 0)
                numbers = page.locator('.figure-value, .card-value, .result-value, .series-result-value, .chart-readout')
                check(path + ' populated', numbers.count() > 0 or page.locator('svg[role="img"]').count() > 0)
                text = '\n'.join(numbers.all_inner_texts())
                check(path + ' bounded values', re.search(r'\d,\d{3,}', text) is None)
            # No-JavaScript fallback keeps the same bounded reader text.
            nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
            p = nojs.new_page()
            p.goto(args.origin + '/dados/series/worldbank.life_expectancy.DE')
            check('nojs headline', p.locator('.figure-value').inner_text().startswith('80,79'))
            check('nojs chart', p.locator('svg[role="img"]').count() > 0)
            check('console clean', not errors)
            check('local requests only', not outside)
            browser.close()
            completed = True
    finally:
        after = hashlib.sha256(db.read_bytes()).hexdigest()
        checks.append({'name': 'database bytes preserved', 'passed': before == after})
        receipt = {'passed': completed and all(item['passed'] for item in checks),
                   'completed': completed, 'checks': checks, 'cases': cases,
                   'errors': errors, 'outside': outside,
                   'before_sha256': before, 'after_sha256': after}
        (args.output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
        print(json.dumps({'passed': receipt['passed'], 'checks': len(checks), 'cases': len(cases)}))


if __name__ == '__main__':
    main()
