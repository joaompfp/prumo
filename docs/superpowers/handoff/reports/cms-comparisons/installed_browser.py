"""Read-only installed acceptance of CMS comparisons on both public addresses."""
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
from playwright.sync_api import sync_playwright

SLUGS = {
    'inflacao-e-desemprego': 2, 'euribor-e-inflacao': 2, 'credito-e-taxa': 2,
    'taxas-juro-credito-depositos': 4, 'divida-saldo-pib-per-capita': 3,
    'comercio-externo-pib-per-capita': 3, 'eletricidade-domestica': 5,
    'pib-por-habitante': 5, 'divida-publica': 5,
}
OUT = Path(__file__).resolve().parent / 'production'


def main():
    OUT.mkdir(exist_ok=True)
    checks, warnings, errors, requests = [], [], [], []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        assert condition, name
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
        for origin in ('https://cae.joao.date', 'https://joao.date/dados'):
            for width in (390, 1440):
                context = browser.new_context(viewport={'width': width, 'height': 1000 if width > 768 else 844})
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: warnings.append(message.text) if message.type in ('warning', 'error') else None)
                page.on('request', lambda request: requests.append(request.url))
                response = page.goto(origin + '/comparar')
                check(f'{origin}-{width}-directory-200', response is not None and response.status == 200)
                links = page.locator('.compare-link')
                check(f'{origin}-{width}-nine-real-links', links.count() == len(SLUGS))
                check(f'{origin}-{width}-directory-script-free', page.locator('script').count() == 0)
                check(f'{origin}-{width}-no-notebook-composition-links', not any('/caderno?' in link for link in links.evaluate_all('(nodes)=>nodes.map(n=>n.href)')))
                for slug, series_count in SLUGS.items():
                    response = page.goto(origin + '/comparar/' + slug)
                    page.evaluate('document.fonts.ready')
                    page.wait_for_selector('.chart-shell.chart-enhanced canvas')
                    data = json.loads(page.locator('.chart-data').inner_text())
                    label = f'{origin}-{width}-{slug}'
                    check(label+'-200', response is not None and response.status == 200)
                    check(label+'-all-sides', len(data['series']) == series_count)
                    check(label+'-complete-table', page.locator('.notebook-table-scroll tbody tr').count() == len(data['x']))
                    check(label+'-no-public-authoring', page.locator('select[name^=series_],select[name^=axis_],select[name=escala],.notebook-chart-form').count() == 0)
                    check(label+'-no-overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    slider = page.locator('.chart-range')
                    for key, index in (('Home', 0), ('End', -1)):
                        slider.focus()
                        slider.press(key)
                        readout = page.locator('.chart-readout').inner_text()
                        check(label+'-'+key+'-period', data['periods'][index] in readout)
                        check(label+'-'+key+'-values', all(value in readout for value in data['display'][index]))
                    if slug == 'taxas-juro-credito-depositos':
                        page.locator('h1').click()
                        box = page.locator('.chart-canvas').bounding_box()
                        assert box is not None
                        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        page.mouse.move(0,0)
                        page.evaluate('window.scrollTo(0,0)')
                        page.wait_for_timeout(100)
                        if origin.endswith('/dados'):
                            page.screenshot(path=str(OUT / f'comparison-{width}.png'))
                context.close()
        browser.close()
    check('no-application-errors', not errors)
    unexpected = [warning for warning in warnings if 'vr' not in warning]
    check('no-unexpected-console-warning', not unexpected)
    check('no-external-requests', all(urlparse(url).netloc in {'cae.joao.date','joao.date'} for url in requests if url.startswith('http')))
    with httpx.Client(follow_redirects=False, timeout=30) as client:
        admin = client.get('https://joao.date/dados/admin/cms')
        check('admin-challenges-through-authelia', admin.status_code in (301,302,303,307) and 'authelia.joao.date' in admin.headers.get('location',''))
        for origin in ('https://cae.joao.date','https://joao.date/dados'):
            response = client.get(origin+'/comparar/paises/eletricidade-domestica')
            check(origin+'-legacy-country-redirect', response.status_code == 301 and response.headers['location'].endswith('/comparar/eletricidade-domestica'))
            check(origin+'-unknown-404', client.get(origin+'/comparar/not-a-published-comparison').status_code == 404)
    result = {'passed': len(checks), 'checks': checks, 'warnings': warnings, 'errors': errors}
    (OUT/'browser.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed': len(checks), 'shared_edge_vr_warnings':len(warnings), 'receipt':str(OUT/'browser.json')}))


if __name__ == '__main__':
    main()
