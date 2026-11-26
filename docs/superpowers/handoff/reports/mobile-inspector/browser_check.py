"""Read-only real-browser acceptance for responsive chart inspection."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import expect, sync_playwright

from tests.app.test_chart_layout import _chromium

ROUTES = (
    '/series/ine.hicp_yoy.PT',
    '/series/eredes.production_total.PT',
    '/calculadas/derived.unemployment_monthly.PT.yoy_change',
    '/comparar/taxas-juro-credito-depositos',
    '/comparar/paises/eletricidade-domestica',
    '/caderno?s=ine.hicp_yoy.PT&s=worldbank.gdp_per_capita.PT&escala=dupla',
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checks, cases, warnings = [], [], []
    completed = False
    expected_asset = hashlib.sha256(Path('static/js/prumo-charts.min.js').read_bytes()).hexdigest()

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        assert condition, name

    try:
        with sync_playwright() as pw:
            options = {'headless': True, 'args': ['--no-sandbox']}
            executable = _chromium()
            if executable:
                options['executable_path'] = executable
            browser = pw.chromium.launch(**options)
            for base in args.base:
                for width, touch in ((320, True), (390, True), (844, True),
                                     (599, False), (600, False), (1440, False)):
                    for route in ROUTES:
                        if args.baseline and (width != 390 or route != ROUTES[3]):
                            continue
                        ctx = browser.new_context(viewport={'width': width, 'height': 1000},
                                                  has_touch=touch, is_mobile=touch,
                                                  device_scale_factor=1)
                        page = ctx.new_page()
                        errors, offsite = [], []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('console', lambda m: errors.append(m.text)
                                if m.type == 'error' else warnings.append(m.text)
                                if m.type == 'warning' else None)
                        origin = urlparse(base).netloc
                        page.on('request', lambda r: offsite.append(r.url)
                                if urlparse(r.url).netloc != origin else None)
                        response = page.goto(base.rstrip('/') + route, wait_until='networkidle')
                        check('HTTP 200', response is not None and response.status == 200)
                        page.evaluate('() => document.fonts.ready')
                        root = page.locator('.chart-shell').first
                        expect(root.locator('canvas')).to_have_count(1)
                        payload_text = root.locator('script.chart-data').text_content()
                        assert payload_text is not None
                        payload = json.loads(payload_text)
                        asset_url = page.locator('script[src*="prumo-charts.min.js"]').get_attribute('src')
                        assert asset_url is not None
                        asset = page.request.get(urljoin(page.url, asset_url))
                        check('referenced asset HTTP 200', asset.status == 200)
                        if not args.baseline:
                            check('referenced asset exact bytes', hashlib.sha256(asset.body()).hexdigest() == expected_asset)
                        root.locator('.chart-wrap').scroll_into_view_if_needed()
                        box = root.locator('.chart-canvas').bounding_box()
                        assert box is not None
                        inline = touch or width < 600
                        fractions = (0.5,) if args.baseline else (0.005, 0.5, 0.995)
                        for fraction in fractions:
                            x, y = box['x'] + box['width'] * fraction, box['y'] + box['height'] / 2
                            scroll = page.evaluate('() => window.scrollY')
                            if touch:
                                page.touchscreen.tap(x, y)
                            else:
                                page.mouse.move(x, y)
                            page.wait_for_timeout(160)
                            index = int(root.locator('.chart-range').input_value())
                            expect(root.locator('.chart-readout-period')).to_have_text(payload['periods'][index])
                            check('one row for every series', root.locator('.chart-readout-row').count() == len(payload['series']))
                            for side, series in enumerate(payload['series']):
                                row = root.locator('.chart-readout-row').nth(side)
                                display = payload['display'][index][side]
                                expect(row.locator('.chart-readout-value')).to_have_text(
                                    payload['missing'] if display is None else display)
                                if len(payload['series']) > 1:
                                    expect(row.locator('.chart-readout-title')).to_have_text(series['title'])
                                check('prepared value exact', True)
                            check('tap/mouse does not auto-scroll', page.evaluate('() => window.scrollY') == scroll)
                            tips = root.locator('.chart-tooltip')
                            visible = tips.count() > 0 and tips.is_visible() and tips.inner_text().strip() != ''
                            if not args.baseline:
                                check('expected responsive tooltip mode', not visible if inline else visible)
                                if inline:
                                    readout = root.locator('.chart-readout').bounding_box()
                                    controls = root.locator('.chart-controls').bounding_box()
                                    plot = root.locator('.chart-scroll').bounding_box()
                                    assert readout is not None and controls is not None and plot is not None
                                    check('readout below plot', plot['y'] + plot['height'] <= readout['y'] + 1)
                                    check('readout immediately after plot', readout['y'] - plot['y'] - plot['height'] <= 9)
                                    check('readout full width', readout['width'] >= controls['width'] - 1)
                            else:
                                check('baseline reproduces covering overlay', visible)
                        if len(payload['x']) > 1:
                            root.locator('.chart-range').focus()
                            page.keyboard.press('Home')
                            expect(root.locator('.chart-readout-period')).to_have_text(payload['periods'][0])
                            page.keyboard.press('End')
                            expect(root.locator('.chart-readout-period')).to_have_text(payload['periods'][-1])
                            check('native keyboard complete endpoints', True)
                        check('no page horizontal overflow', page.evaluate(
                            '() => document.documentElement.scrollWidth <= innerWidth + 1'))
                        check('no application/CSP errors', not errors)
                        check('no off-origin requests', not offsite)
                        cases.append({'base': base, 'route': route, 'width': width,
                                      'touch': touch, 'points': len(payload['x']), 'series': len(payload['series'])})
                        if route == ROUTES[3] and width in (390, 1440):
                            root.scroll_into_view_if_needed()
                            name = f'{urlparse(base).hostname}-{width}-{"before" if args.baseline else "after"}.png'
                            root.screenshot(path=str(args.output.parent / name))
                        ctx.close()
                # Native no-script fallback is still independent from the new presentation.
                if not args.baseline:
                    ctx = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
                    page = ctx.new_page()
                    response = page.goto(base.rstrip('/') + ROUTES[3], wait_until='networkidle')
                    check('no-JS SVG remains visible', response is not None and response.status == 200 and page.locator('svg.chart[role=img]').is_visible())
                    check('no-JS inspector remains absent', not page.locator('.chart-controls').is_visible())
                    ctx.close()
            browser.close()
        completed = True
    finally:
        report = {'completed': completed, 'passed': completed and all(c['passed'] for c in checks),
                  'checks': checks, 'cases': cases, 'warnings': warnings}
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'completed': completed, 'passed': report['passed'],
                          'checks': len(checks), 'cases': len(cases), 'warnings': len(warnings)}))


if __name__ == '__main__':
    main()
