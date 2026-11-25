"""Read-only production acceptance of phase C on both approved public addresses."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[6]
CHROME = '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'
BASES = ('https://cae.joao.date', 'https://joao.date/dados')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    checks, errors, warnings, requests, cases, journeys, assets = [], [], [], [], [], [], []
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
            context.on('page', lambda p: p.on('pageerror', lambda e: errors.append(str(e))))
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else warnings.append(m.text) if m.type == 'warning' else None)
            context.on('request', lambda r: requests.append(r.url))
            for base in BASES:
                prefix = urlparse(base).path
                origin = base.removesuffix(prefix) if prefix else base
                for width in (320, 390, 768, 900, 901, 1100, 1101, 1440, 1920):
                    page.set_viewport_size({'width': width, 'height': 844 if width < 700 else 1000})
                    for name, path in (('catalogue', '/pesquisa'), ('search', '/pesquisa?q=desemprego+Portugal'),
                                       ('theme', '/temas/energy'), ('home', '/'), ('demography', '/temas/demography'),
                                       ('comparisons', '/comparar'), ('methodology', '/metodologia')):
                        response = page.goto(base + path)
                        assert response is not None, 'Navigation returned no response'
                        tag = f'{base}-{width}-{name}'
                        check(tag + '-200', response.status == 200)
                        page.evaluate('document.fonts.ready')
                        check(tag + '-overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                        check(tag + '-body', page.locator('body').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 28.05)
                        check(tag + '-single-search', page.locator('input[type=search]').count() == 1)
                        check(tag + '-script-free', page.locator('script').count() == 0)
                        check(tag + '-strict-csp', "default-src 'none'" in response.headers['content-security-policy'])
                        check(tag + '-discovery-css', page.locator('link[rel=stylesheet][href$="/discovery.css"]').count() == 1)
                        if name in ('catalogue', 'search', 'theme'):
                            check(tag + '-populated', page.locator('.series-result').count() > 0)
                            value = page.locator('.series-result-value').first
                            check(tag + '-value-size', value.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 28.05)
                            if name in ('search', 'theme') and width in (390, 1440):
                                box = value.bounding_box()
                                assert box is not None, 'Visible value has no geometry'
                                check(tag + '-value-first-view', box['y'] + box['height'] < page.viewport_size['height'])
                        menu = page.locator('.nav-menu')
                        if menu.is_visible():
                            menu.locator('summary').click()
                            check(tag + '-open-menu-fit', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                            check(tag + '-catalogue-reachable', menu.get_by_role('link', name='Catálogo', exact=True).is_visible())
                            menu.locator('summary').click()
                        else:
                            for disclosure in page.locator('.site-nav > details').all():
                                disclosure.locator('summary').click()
                                box = disclosure.locator('ul').bounding_box()
                                assert box is not None, 'Expanded menu has no geometry'
                                check(tag + '-panel-fit', box['x'] >= 0 and box['x'] + box['width'] <= width + 1)
                                disclosure.locator('summary').click()
                        if prefix and width in (390, 1440) and name in ('search', 'theme'):
                            page.locator('h1').click()
                            page.evaluate('scrollTo(0,0)')
                            check(tag + '-capture-top', page.evaluate('scrollY') == 0)
                            page.screenshot(path=str(args.output / f'{name}-{width}.png'))
                        cases.append({'base': base, 'width': width, 'route': path})
                for javascript in (True, False):
                    task_context = browser.new_context(java_script_enabled=javascript, viewport={'width': 1440 if javascript else 390, 'height': 1000})
                    task = task_context.new_page()
                    task.on('pageerror', lambda e: errors.append(str(e)))
                    task_context.on('request', lambda r: requests.append(r.url))
                    task.goto(base + '/pesquisa')
                    task.get_by_label('Pesquisar indicadores', exact=True).fill('desemprego Portugal')
                    task.get_by_role('button', name='Procurar', exact=True).click()
                    task.locator(f'main a[href="{prefix}/series/ine.unemployment_monthly.PT"]').click()
                    notebook_link = task.locator(f'a[href="{prefix}/caderno?s=ine.unemployment_monthly.PT"]')
                    if not notebook_link.is_visible():
                        task.locator('details').filter(has=notebook_link).locator('summary').first.click()
                    notebook_link.click()
                    form = task.locator('#notebook-search-form')
                    form.locator('input[name=q]').fill('IHPC')
                    form.get_by_role('button').click()
                    result = task.locator('.notebook-results tr').filter(has=task.locator('a[href*="s=ine.hicp_yoy.PT"]')).first
                    result.get_by_role('link', name='Acrescentar ao caderno', exact=True).click()
                    clean = task.locator('#ligacao-limpa').get_attribute('href')
                    assert clean is not None, 'Missing share link'
                    params = parse_qs(urlparse(clean).query)
                    check(f'{base}-{javascript}-ordered-selection', params['s'] == ['ine.unemployment_monthly.PT', 'ine.hicp_yoy.PT'])
                    check(f'{base}-{javascript}-clean-link', 'q' not in params)
                    shared_response = task.goto(urljoin(origin + '/', clean))
                    check(f'{base}-{javascript}-share-200', shared_response is not None and shared_response.status == 200)
                    check(f'{base}-{javascript}-share-cards', task.locator('.notebook-selection .card').count() == 2)
                    task.goto(base + '/pesquisa?q=desemprego')
                    task.get_by_label('Pesquisar indicadores', exact=True).fill('industrial')
                    task.locator('.discovery-filters > summary').click()
                    task.locator('select[name=grupo]').select_option('pt')
                    task.get_by_role('button', name='Aplicar filtros', exact=True).click()
                    params = parse_qs(urlparse(task.url).query)
                    check(f'{base}-{javascript}-query-filter', params.get('q') == ['industrial'] and params.get('grupo') == ['pt'])
                    task.goto(base + '/pesquisa?tema=inexistente')
                    check(f'{base}-{javascript}-unknown-filter', task.locator('select[name=tema]').input_value() == 'inexistente')
                    journeys.append({'base': base, 'javascript': javascript, 'shared_path': clean, 'passed': True})
                    task_context.close()
                page.goto(base + '/pesquisa?q=emprego')
                names = page.locator('.series-result-title').all_text_contents()
                check(base + '-pagination-present', page.locator('a[rel=next]').count() == 1)
                page.locator('a[rel=next]').click()
                check(base + '-pagination-changes-page', page.locator('.series-result-title').all_text_contents() != names)
                page.goto(base + '/')
                check(base + '-home-card-action', page.locator('a.card-create').count() > 0)
                page.locator('a.card-create').first.click()
                check(base + '-home-card-notebook', page.locator('.notebook-selection .card').count() == 1)
                page.goto(base + '/comparar')
                hrefs = sorted(set(page.locator('main a[href*="/comparar/"]').evaluate_all('es=>es.map(e=>e.getAttribute("href"))')))
                check(base + '-nine-published-comparisons', len(hrefs) == 9)
                for href in hrefs:
                    chart_response = page.goto(urljoin(origin + '/', href))
                    check(href + '-200', chart_response is not None and chart_response.status == 200)
                    page.wait_for_selector('.chart-enhanced canvas')
                    check(href + '-no-authoring', page.locator('main select[name=scale],main select[name=escala],main select[name^=series_]').count() == 0)
                    raw_data = page.locator('.chart-data').first.text_content()
                    assert raw_data is not None, 'Missing chart payload'
                    data = json.loads(raw_data)
                    slider = page.locator('.chart-range').first
                    for key, index in (('Home', 0), ('End', -1)):
                        slider.focus()
                        slider.press(key)
                        expected = [v if v is not None else data['missing'] for v in data['display'][index]]
                        expect(page.locator('.chart-readout-value')).to_have_text(expected)
                        check(href + '-' + key + '-exact-values', True)
                page.goto(base + '/pesquisa')
                for link in page.locator('link[rel=stylesheet][href$="/discovery.css"],link[rel=stylesheet][href$="/prumo.css"]').all():
                    href = link.get_attribute('href')
                    assert href is not None, 'Missing stylesheet address'
                    result = context.request.get(urljoin(origin + '/', href))
                    local = ROOT / 'static/css' / Path(urlparse(href).path).name
                    check(base + '-exact-asset-' + local.name, result.status == 200 and result.body() == local.read_bytes())
                    assets.append({'url': urljoin(origin + '/', href), 'sha256': hashlib.sha256(result.body()).hexdigest(), 'bytes': len(result.body())})
                page.get_by_label('Pesquisar indicadores', exact=True).focus()
                page.keyboard.press('Tab')
                check(base + '-keyboard-submit', page.locator(':focus').inner_text() == 'Procurar')
                focus = page.locator(':focus').evaluate('e=>({width:parseFloat(getComputedStyle(e).outlineWidth),style:getComputedStyle(e).outlineStyle})')
                check(base + '-visible-focus', focus['width'] >= 2 and focus['style'] != 'none')
                page.emulate_media(media='print')
                check(base + '-print-query-hidden', not page.locator('.discovery-query').is_visible())
                check(base + '-print-data-visible', page.locator('.series-result').first.is_visible())
                page.emulate_media(media='screen')
                check(base + '-health', context.request.get(base + '/healthz').ok)
                check(base + '-unknown-404', context.request.get(base + '/series/inexistente').status == 404)
            challenge = context.request.get('https://joao.date/dados/admin/cms', max_redirects=0)
            check('anonymous-admin-authelia', challenge.status in (302, 303) and urlparse(challenge.headers.get('location', '')).hostname == 'authelia.joao.date')
            check('no-browser-errors', not errors)
            check('no-unexpected-warnings', all('Permissions-Policy' in w and 'vr' in w for w in warnings))
            check('no-off-origin-requests', all(urlparse(u).hostname in {'cae.joao.date', 'joao.date'} for u in requests))
            browser.close()
        completed = True
    finally:
        report = {'completed': completed, 'passed': completed and all(c['passed'] for c in checks), 'checks': checks,
                  'cases': cases, 'journeys': journeys, 'assets': assets, 'errors': errors, 'warnings': warnings}
        (args.output / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'passed': report['passed'], 'checks': len(checks), 'cases': len(cases), 'journeys': len(journeys), 'warnings': len(warnings)}))


if __name__ == '__main__':
    main()
