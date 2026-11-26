"""Read-only acceptance for the catalogue-to-notebook and adjacent inspection iteration."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from playwright.sync_api import expect, sync_playwright

CHROME = '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'
ENERGY = tuple('eurostat.electricity_price_household.' + country for country in ('PT', 'ES', 'DE'))
CHARTS = (
    ('credit', '/comparar/taxas-juro-credito-depositos'),
    ('electricity', '/comparar/eletricidade-domestica'),
    ('mixed', '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT&s=worldbank.gdp_per_capita.PT&escala=dupla'),
    ('primary', '/series/worldbank.life_expectancy.DE'),
    ('derived', '/calculadas/derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct'),
)


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
    complete = False

    def check(label, verdict):
        checks.append({'name': label, 'passed': bool(verdict)})
        if not verdict:
            raise AssertionError(label)

    def refs(page):
        return parse_qs(urlparse(page.url).query).get('s', [])

    def open_catalogue(page, base, query='eletricidade'):
        response = page.goto(base + '/pesquisa?' + urlencode({'q': query}))
        check('catalogue HTTP200', response.status == 200)
        expect(page.locator('input[type=checkbox][name=s]').first).to_be_visible()
        check('single native form', page.locator('form').count() == 1)
        check('query keeps enlarged typography', page.locator('#pesquisa-q').evaluate('el => parseFloat(getComputedStyle(el).fontSize)') >= 28)
        check('summary response has no script', page.locator('script').count() == 0)

    def select(page, sid):
        page.locator('input[type=checkbox][name=s][value="' + sid + '"]').check()

    def selection_journey(browser, base, javascript):
        context = browser.new_context(java_script_enabled=javascript, viewport={'width': 390, 'height': 844})
        page = context.new_page()
        label = base + '/selection/js=' + str(javascript)
        open_catalogue(page, base)
        for sid in ENERGY:
            select(page, sid)
        # First submission works with fresh checkboxes, not only a server-saved selection.
        page.get_by_role('button', name='Abrir caderno', exact=True).click()
        check(label + ' first-click three-series handoff', set(refs(page)) == set(ENERGY))
        check(label + ' no duplicates', len(refs(page)) == 3)
        expect(page.locator('.notebook-chart')).to_be_visible()
        page.locator('.notebook-chart-links a[href*="/pesquisa"]').first.click()
        check(label + ' catalogue preserves current refs', set(refs(page)) == set(ENERGY))
        page.locator('#pesquisa-q').fill('desemprego Portugal')
        page.get_by_role('button', name='Procurar', exact=True).click()
        check(label + ' search preserves selection', set(refs(page)) == set(ENERGY))
        select(page, 'ine.unemployment_monthly.PT')
        page.get_by_role('button', name='Abrir caderno', exact=True).click()
        check(label + ' add without replacing', set(refs(page)) == set(ENERGY) | {'ine.unemployment_monthly.PT'})
        # Current unsaved checkbox selections survive native pagination.
        open_catalogue(page, base)
        select(page, ENERGY[2])
        page.get_by_role('button', name='Página seguinte', exact=True).click()
        check(label + ' unsaved check retained by pager', ENERGY[2] in refs(page))
        second = page.locator('input[type=checkbox][name=s]').first.get_attribute('value')
        select(page, second)
        page.get_by_role('button', name='Página anterior', exact=True).click()
        check(label + ' offpage refs retained in original order', refs(page) == [ENERGY[2], second])
        page.locator('input[type=checkbox][value="' + ENERGY[2] + '"]').uncheck()
        page.get_by_role('button', name='Abrir caderno', exact=True).click()
        check(label + ' unchecked visible reference absent', refs(page) == [second])
        # Search theme titles without broadening the separate quick-suggestion contract.
        open_catalogue(page, base, 'energia')
        check(label + ' real subject discovery', page.locator('input[type=checkbox][name=s]').count() > 0)
        page.evaluate('document.fonts.ready')
        page.evaluate('window.scrollTo(0,0)')
        first_value = page.locator('.series-result-value').first.bounding_box()
        first_check = page.locator('.series-result-select').first.bounding_box()
        assert first_value is not None and first_check is not None
        check(label + ' real value in first view', first_value['y'] + first_value['height'] <= 844)
        check(label + ' selection control in first view', first_check['y'] + first_check['height'] <= 844)
        check(label + ' no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
        if javascript:
            page.evaluate('document.fonts.ready')
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(args.output / (urlparse(base).netloc.replace(':', '_') + '-catalogue-390.png')))
        context.close()

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
                for width in (320, 390, 768, 1440, 1920):
                    page.set_viewport_size({'width': width, 'height': 1000 if width > 768 else 844})
                    for name, path in CHARTS:
                        label = base + '/' + name + '/' + str(width)
                        response = page.goto(base + path)
                        assert response is not None
                        check(label + ' HTTP200', response.status == 200)
                        page.evaluate('document.fonts.ready')
                        page.wait_for_selector('.chart-enhanced canvas')
                        check(label + ' strict CSP', "default-src 'none'" in response.headers.get('content-security-policy', ''))
                        check(label + ' no overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                        payload = json.loads(page.locator('.chart-data').inner_text())
                        count = len(payload['series'])
                        plot = page.locator('.chart-scroll').bounding_box()
                        controls = page.locator('.chart-controls').bounding_box()
                        assert plot is not None and controls is not None
                        check(label + ' adjacent controls', 0 <= controls['y'] - plot['y'] - plot['height'] <= 45)
                        check(label + ' functional chart height', plot['height'] >= 250)
                        check(label + ' point rows', page.locator('.chart-readout-row').count() == count)
                        expected_swatches = count if count > 1 or payload['version'] == 2 else 0
                        check(label + ' prepared style swatches', page.locator('.chart-readout-row .legend-swatch').count() == expected_swatches)
                        check(label + ' unit appears in values only', page.locator('.chart-readout-unit').count() == 0)
                        check(label + ' metadata disclosure', page.locator('details.chart-meta').count() == 1)
                        metadata = page.locator('details.chart-meta').bounding_box()
                        assert metadata is not None
                        check(label + ' metadata after controls', metadata['y'] > controls['y'])
                        slider = page.locator('.chart-range')
                        check(label + ' range outside every form', slider.evaluate('el => el.form === null'))
                        check(label + ' enlarged functional text', page.locator('body').evaluate('el => parseFloat(getComputedStyle(el).fontSize)') >= 28)
                        for key, index in (('Home', 0), ('End', len(payload['x']) - 1)):
                            slider.focus()
                            slider.press(key)
                            expect(slider).to_have_value(str(index))
                            expected = [value if value is not None else payload['missing'] for value in payload['display'][index]]
                            check(label + key + ' exact point display', page.locator('.chart-readout-value').all_text_contents() == expected)
                        if path.startswith('/comparar/'):
                            check(label + ' no public authoring', page.locator('main form').count() == 0)
                        # The authoritative control remains adjacent even when metadata is expanded.
                        before_control = page.locator('.chart-controls').evaluate('el => el.getBoundingClientRect().top + scrollY')
                        page.locator('details.chart-meta > summary').click()
                        after_control = page.locator('.chart-controls').evaluate('el => el.getBoundingClientRect().top + scrollY')
                        check(label + ' expanding sources does not displace inspector', abs(after_control - before_control) < 1)
                        page.locator('details.chart-meta > summary').click()
                        if width in (390, 1440) and name in ('credit', 'mixed'):
                            page.locator('.chart-canvas').hover(position={'x': 2, 'y': 2})
                            page.mouse.move(0, 0)
                            expect(page.locator('.chart-tip-line').first).not_to_be_visible()
                            page.locator('h1').click()
                            page.evaluate('window.scrollTo(0,0)')
                            check(label + ' first-view scroll', page.evaluate('scrollY') == 0)
                            tag = urlparse(base).netloc.replace(':', '_') + ('-mounted' if urlparse(base).path else '')
                            page.screenshot(path=str(args.output / f'{tag}-{name}-{width}.png'))
                        page.emulate_media(media='print')
                        check(label + ' print metadata content visible', page.locator('details.chart-meta').evaluate(
                            "el => [...el.children].some(c => c.tagName !== 'SUMMARY' && c.getBoundingClientRect().height > 0)"))
                        check(label + ' print interactive control hidden', not page.locator('.chart-controls').is_visible())
                        page.emulate_media(media='screen')
                        cases.append(label)
                for relative in ('static/css/discovery.css', 'static/css/chart-inspector.css', 'static/js/prumo-charts.min.js'):
                    asset = page.request.get(base + '/' + relative)
                    check(base + relative + ' actual installed bytes', asset.status == 200 and asset.body() == (args.root / relative).read_bytes())
                context.close()
                selection_journey(browser, base, True)
                selection_journey(browser, base, False)
                for blocked in (False, True):
                    context = browser.new_context(java_script_enabled=blocked, viewport={'width': 390, 'height': 844})
                    if blocked:
                        context.route('**/static/js/prumo-charts*', lambda route: route.abort())
                    fallback = context.new_page()
                    fallback.goto(base + CHARTS[0][1])
                    check(base + '/fallback/' + str(blocked) + ' SVG visible', fallback.locator('svg.chart').is_visible())
                    check(base + '/fallback/' + str(blocked) + ' inspector hidden', not fallback.locator('.chart-controls').is_visible())
                    fallback.locator('details.chart-meta > summary').click()
                    check(base + '/fallback/' + str(blocked) + ' source links accessible', fallback.locator('details.chart-meta a').first.is_visible())
                    context.close()
            check('no application errors', not errors)
            check('no off-origin requests', not outside)
            check('only known edge vr warnings', all('Permissions-Policy' in warning and 'vr' in warning for warning in warnings))
            browser.close()
            complete = True
    finally:
        if args.db:
            checks.append({'name': 'isolated database bytes unchanged', 'passed': before == hashlib.sha256(args.db.read_bytes()).hexdigest()})
        receipt = {'complete': complete, 'passed': complete and all(c['passed'] for c in checks),
                   'checks': checks, 'cases': cases, 'errors': errors, 'warnings': warnings, 'off_origin': outside}
        (args.output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': receipt['passed'], 'checks': len(checks), 'chart_cases': len(cases)}))


if __name__ == '__main__':
    main()
