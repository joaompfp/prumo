"""Read-only UI acceptance with real populated charts and native controls."""
import argparse
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import expect, sync_playwright

from tests.app.test_chart_layout import _chromium

ROUTES = {
    'notebook': '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT',
    'catalogue': '/pesquisa?q=eletricidade',
    'comparison': '/comparar/taxas-juro-credito-depositos',
    'comparisons': '/comparar',
    'series': '/series/ine.hicp_yoy.PT',
    'derived': '/calculadas/derived.unemployment_monthly.PT.yoy_change',
    'home': '/',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checks, cases, warnings = [], [], []

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        assert condition, name

    complete = False
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=_chromium(), args=['--no-sandbox'])
            widths = (390, 1440) if args.quick else (320, 360, 390, 600, 768, 900, 901, 1120, 1440, 1920)
            for base in args.base:
                for width in widths:
                    ctx = browser.new_context(viewport={'width': width, 'height': 1000 if width > 600 else 844}, has_touch=width <= 600, is_mobile=width <= 600)
                    page = ctx.new_page()
                    for name, route in ROUTES.items():
                        errors, external = [], []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else warnings.append(m.text) if m.type == 'warning' else None)
                        page.on('request', lambda r: external.append(r.url) if urlparse(r.url).netloc != urlparse(base).netloc else None)
                        response = page.goto(base.rstrip('/') + route, wait_until='networkidle')
                        check('route HTTP 200', response is not None and response.status == 200)
                        page.evaluate('() => document.fonts.ready')
                        check('approved compact root', page.evaluate('() => getComputedStyle(document.documentElement).fontSize') == '22px')
                        toolkit = page.locator('link[href*="/vendor/bootstrap/bootstrap-subset.css"]')
                        check('pinned Bootstrap referenced by document', toolkit.count() == 1)
                        vendor = page.request.get(urljoin(page.url, toolkit.get_attribute('href')))
                        check('exact toolkit bytes', vendor.status == 200 and vendor.body() == Path('static/vendor/bootstrap/bootstrap-subset.css').read_bytes())
                        check('three direct task links visible', page.locator('.site-nav > a').count() == 3 and all(a.is_visible() for a in page.locator('.site-nav > a').all()))
                        check('no horizontal page overflow', page.evaluate('() => document.documentElement.scrollWidth <= innerWidth + 1'))
                        check('no page or CSP errors', not errors)
                        check('no off-origin requests', not external)
                        for asset in ('bootstrap-theme.css', 'prumo.css', 'app-shell.css', 'workspace.css', 'discovery.css', 'chart-inspector.css'):
                            asset_url = page.locator(f'link[href*="/{asset}"]').get_attribute('href')
                            fetched = page.request.get(urljoin(page.url, asset_url))
                            check('exact served CSS ' + asset, fetched.status == 200 and fetched.body() == (Path('static/css') / asset).read_bytes())
                        nav_size = page.locator('.app-nav-link').first.evaluate('(e) => parseFloat(getComputedStyle(e).fontSize)')
                        check('navigation remains readable', nav_size >= 18.6)
                        more = page.locator('.app-more')
                        check('utility never covers task navigation', page.evaluate('''() => {
                            const u=document.querySelector('.app-more > summary').getBoundingClientRect();
                            return [...document.querySelectorAll('.app-nav-link')].every(e => {
                                const r=e.getBoundingClientRect();
                                return r.right<=u.left || r.left>=u.right || r.bottom<=u.top || r.top>=u.bottom;
                            });
                        }'''))
                        more.locator('summary').click()
                        check('native more panel opens', more.get_attribute('open') is not None)
                        check('open menu stays within viewport', more.locator('.app-panel').evaluate('(e) => { const r=e.getBoundingClientRect(); return r.x>=-1 && r.right<=innerWidth+1 }'))
                        more.locator('summary').click()
                        if name == 'notebook':
                            configure = page.get_by_role('link', name='Configurar:', exact=False)
                            plot = page.locator('.chart-wrap').first
                            before = plot.evaluate('(e) => e.getBoundingClientRect().top + scrollY')
                            configure.click()
                            check('configure reveals native settings', page.locator('.notebook-chart-settings').get_attribute('open') is not None)
                            check('settings groups present', page.locator('#definicoes fieldset').count() == 4)
                            check('settings do not displace earlier plot', abs(plot.evaluate('(e) => e.getBoundingClientRect().top + scrollY') - before) < 1)
                            controls = page.locator('#definicoes select, #definicoes input[type=date], #definicoes input[name=base]')
                            check('settings use compact readable type', controls.count() == 6 and all(c.evaluate('(e) => parseFloat(getComputedStyle(e).fontSize) >= 19.7') for c in controls.all()))
                            check('settings controls fit their panel', all(c.evaluate('(e) => {const r=e.getBoundingClientRect(); return r.x>=0 && r.right<=innerWidth+1}') for c in controls.all()))
                            if width in (390, 1440):
                                page.locator('.notebook-chart-settings').screenshot(path=str(args.output / f'settings-{width}.png'))
                            page.locator('.notebook-chart-settings > summary').click()
                        if name in ('notebook','comparison','series','derived'):
                            plot = page.locator('.chart-wrap').first
                            check('real canvas painted', page.locator('.chart-canvas canvas').count() >= 1)
                            plot_box = plot.bounding_box()
                            assert plot_box is not None
                            check('usable plot height', plot_box['height'] >= 263)
                            point = page.locator('.chart-range').first
                            check('point inspector outside form', point.evaluate('(e) => e.form === null'))
                            point.focus()
                            page.keyboard.press('Home')
                            payload_text = page.locator('script.chart-data').first.text_content()
                            assert payload_text is not None
                            payload = json.loads(payload_text)
                            expect(page.locator('.chart-readout-period').first).to_have_text(payload['periods'][0])
                            page.keyboard.press('End')
                            expect(page.locator('.chart-readout-period').first).to_have_text(payload['periods'][-1])
                            check('keyboard endpoints exact', True)
                            if width <= 600:
                                check('mobile inspection stays below plot', page.locator('.chart-shell').first.evaluate('(e) => {const r=e.querySelector(".chart-readout").getBoundingClientRect(), p=e.querySelector(".chart-scroll").getBoundingClientRect();return r.y>=p.bottom-1}'))
                            if width > 600:
                                plot.scroll_into_view_if_needed()
                                plot_box = plot.bounding_box()
                                assert plot_box is not None
                                page.mouse.move(plot_box['x'] + 2, plot_box['y'] + 2)
                                page.mouse.move(1, 1)
                                expect(page.locator('.chart-tip-line').first).to_be_hidden()
                            page.locator('h1').click()
                        page.evaluate('() => window.scrollTo(0,0)')
                        check('neutral capture at origin', page.evaluate('() => scrollY') == 0)
                        if width in (390, 1440):
                            label = f'{urlparse(base).hostname}-{name}-{width}'
                            page.screenshot(path=str(args.output / (label + '.png')))
                            if name in ('notebook','catalogue'):
                                page.screenshot(path=str(args.output / (label + '-full.png')), full_page=True)
                        cases.append({'base': base, 'route': route, 'width': width, 'header': page.locator('.site-header').bounding_box(), 'plot': page.locator('.chart-wrap').first.bounding_box() if page.locator('.chart-wrap').count() else None})
                        page.close()
                        page = ctx.new_page()
                    ctx.close()
            browser.close()
        complete = True
    finally:
        receipt = {'completed': complete, 'passed': complete and all(c['passed'] for c in checks), 'checks': checks, 'cases': cases, 'warnings': warnings}
        (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2))
        print(json.dumps({'completed': complete, 'checks': len(checks), 'cases': len(cases), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
