"""Read-only installed notebook/navigation proof on the two actual public prefixes."""
import gzip
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(os.environ['PRUMO_PROD_OUT']).resolve()
OUT.mkdir(parents=True, exist_ok=False)
BASES = ('https://cae.joao.date', 'https://joao.date/dados')
HICP = 'ine.hicp_yoy.PT'
UNEMP = 'ine.unemployment_monthly.PT'
EUR12 = 'bportugal.euribor_12m.EA'
CREDIT = 'bportugal.credit_housing.PT'
BP = [f'bportugal.{name}.{geo}' for name, geo in (
    ('euribor_1m', 'EA'), ('euribor_3m', 'EA'), ('euribor_6m', 'EA'),
    ('euribor_12m', 'EA'), ('pt_10y', 'PT'), ('de_10y', 'DE'))]
ELECTRICITY = [f'eurostat.electricity_price_household.{geo}' for geo in ('PT', 'ES', 'FR', 'DE', 'IT')]
REPORT = {'checks': [], 'errors': [], 'warnings': [], 'external': [], 'assets': {}, 'screens': []}


def check(name, condition):
    REPORT['checks'].append({'check': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)


def address(series, **settings):
    return '/caderno?' + urlencode([('s', item) for item in series] + list(settings.items()))


def exact(payload, point):
    if len(payload['series']) == 1:
        return payload['periods'][point] + ': ' + payload['display'][point][0]
    return payload['periods'][point] + ' - ' + '; '.join(
        f'{side["title"]}: {payload["display"][point][i]}'
        for i, side in enumerate(payload['series']))


def painted_bounds(page):
    return page.locator('.chart-canvas canvas').evaluate('''c => {
      const ctx=c.getContext('2d', {willReadFrequently:true});
      const d=ctx.getImageData(0,0,c.width,c.height).data;
      const probe=document.createElement('canvas').getContext('2d', {willReadFrequently:true});
      probe.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--rule').trim();
      probe.fillRect(0,0,1,1); const target=probe.getImageData(0,0,1,1).data;
      let left=0,right=0,best=0;
      for(let y=0;y<c.height;y++) { let start=-1;
        for(let x=0;x<=c.width;x++) { const i=(y*c.width+x)*4;
          const match=x<c.width && d[i+3]>100 && Math.abs(d[i]-target[0])<5 && Math.abs(d[i+1]-target[1])<5 && Math.abs(d[i+2]-target[2])<5;
          if(match && start<0)start=x;
          if(!match && start>=0){if(x-start>best){best=x-start;left=start;right=x-1}start=-1}
        }
      }
      const r=c.getBoundingClientRect();
      return {left:r.x+left*r.width/c.width,right:r.x+right*r.width/c.width,
        y:r.y+r.height/2,valid:best>c.width/3};
    }''')


def capture(page, name):
    page.mouse.move(0, 0)
    page.screenshot(path=str(OUT / name))
    REPORT['screens'].append(name)


def observe(context, origin):
    context.on('request', lambda req: REPORT['external'].append(req.url)
               if urlsplit(req.url).netloc != urlsplit(origin).netloc else None)


def page_events(page):
    page.on('pageerror', lambda error: REPORT['errors'].append(str(error)))
    page.on('console', lambda msg: REPORT['errors'].append(msg.text) if msg.type == 'error'
            else REPORT['warnings'].append(msg.text) if msg.type == 'warning' else None)


def main():
    paths = [('/', 0), ('/caderno', 0), (address([HICP], janela='max'), 1), (address([HICP, UNEMP]), 2),
             (address(BP, janela='max'), 6), (address(ELECTRICITY), 5),
             (address([EUR12, CREDIT], escala='dupla'), 2),
             (address([HICP, CREDIT]), 0), (address([*BP, HICP]), 0),
             (address(['eredes.production_market.PT', 'eredes.production_special.PT']), 2)]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',
            args=['--no-sandbox'])
        for base in BASES:
            context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            observe(context, base)
            page = context.new_page()
            page_events(page)
            suffix = 'mounted' if '/dados' in base else 'direct'
            for width in (320, 390, 768, 900, 901, 1024, 1440):
                page.set_viewport_size({'width': width, 'height': 1100})
                for path, series_count in paths:
                    tag = base + path + '@' + str(width)
                    response = page.goto(base + path)
                    check(tag + ' HTTP200', response is not None and response.status == 200)
                    assert response is not None
                    page.evaluate('document.fonts.ready')
                    check(tag + ' no overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    check(tag + ' large local type', page.evaluate("parseFloat(getComputedStyle(document.body).fontSize)>=28.04 && document.fonts.check('28.05px Lato')"))
                    sizes = page.locator('.site-header .search').evaluate('e=>{const i=e.querySelector("input").getBoundingClientRect(),b=e.querySelector("button").getBoundingClientRect();return {a:i.height,b:b.height,y:i.y,z:b.y,right:i.right,left:b.left}}')
                    check(tag + ' aligned joined search', abs(sizes['a']-sizes['b']) < .6 and abs(sizes['y']-sizes['z']) < .6 and abs(sizes['right']-sizes['left']) < .6)
                    check(tag + ' typography', chr(0x2014) not in page.locator('body').inner_text())
                    if path.startswith('/caderno'):
                        robots = {token.strip().lower() for token in response.headers.get('x-robots-tag', '').split(',')}
                        meta = page.locator('meta[name="robots"]').get_attribute('content')
                        check(tag + ' noindex', bool({'noindex', 'none'} & robots) and meta == 'noindex, follow')
                        REPORT.setdefault('effective_edge_robots', {})[base] = response.headers.get('x-robots-tag')
                    if series_count:
                        page.locator('.chart-enhanced canvas').wait_for()
                        payload = json.loads(page.locator('script.chart-data').inner_text())
                        check(tag + ' correct series', len(payload['series']) == series_count)
                        check(tag + ' complete table', page.locator('.table-details tbody tr').count() == len(payload['x']))
                        check(tag + ' exact table columns', page.locator('.table-details thead th').count() == series_count + 1)
                        check(tag + ' strict scripts', "script-src 'self'" in response.headers['content-security-policy'])
                        slider = page.locator('.chart-range')
                        for key, point in (('Home', 0), ('End', len(payload['x'])-1)):
                            slider.focus()
                            slider.press(key)
                            expect(page.locator('.chart-readout')).to_have_text(exact(payload, point))
                            check(tag + ' exact keyboard ' + key, page.locator('.chart-live').inner_text() == exact(payload, point))
                        if 'escala=dupla' in path:
                            check(tag + ' dual axes retained', len(payload['axes']) == 2)
                        for selector in ('.table-details', '.notebook-definitions', '.provenance-details'):
                            disclosure = page.locator('.notebook-chart ' + selector)
                            disclosure.locator('summary').first.click()
                            check(tag + ' open contained ' + selector, page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                            disclosure.locator('summary').first.click()
                        if width in (390, 1440) and path == address([HICP, UNEMP]):
                            page.locator('.chart-canvas').scroll_into_view_if_needed()
                            capture(page, f'notebook-{suffix}-{width}.png')
                    else:
                        check(tag + ' scriptfree', page.locator('script[src]').count() == 0)
                    if path == address([*BP, HICP]):
                        check(tag + ' seven cards not truncated', page.locator('article.card').count() == 7)
                        check(tag + ' no implicit six', page.locator('#notebook-chart-form input[name="g"]:checked').count() == 0)
                    if width > 900:
                        for index in (0, 1):
                            summary = page.locator('.site-nav > .nav-disclosure > summary').nth(index)
                            summary.click()
                            check(tag + ' open panel contained ' + str(index), page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                            summary.click()
                    else:
                        summary = page.locator('.nav-menu > summary')
                        summary.focus()
                        summary.press('Enter')
                        check(tag + ' native menu opens', page.locator('.nav-menu').get_attribute('open') is not None)
                        check(tag + ' open menu contained', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                        check(tag + ' destinations visible', page.locator('.site-nav-compact a:visible').count() == 9)
                        summary.press('Enter')
                    if path == '/' and width in (390, 1440):
                        page.evaluate('window.scrollTo(0,0)')
                        capture(page, f'home-{suffix}-{width}.png')
            page.set_viewport_size({'width': 1440, 'height': 1100})
            page.goto(base + address([HICP, UNEMP, BP[1]]))
            page.locator('.notebook-chart-settings > summary').click()
            form = page.locator('#notebook-chart-form')
            form.locator(f'input[name="g"][value="{BP[1]}"]').uncheck()
            form.locator('select[name="janela"]').select_option('5a')
            form.locator('button[type="submit"]').click()
            page.locator('.chart-enhanced canvas').wait_for()
            payload = json.loads(page.locator('script.chart-data').inner_text())
            check(base + ' reader GET form subset', len(payload['series']) == 2)
            clean = page.locator('#ligacao-limpa').get_attribute('href') or ''
            check(base + ' share retains configuration', 'grafico=on' in clean and 'janela=5a' in clean and clean.count('g=') == 2)
            page.locator('.notebook-chart-settings > summary').click()
            for checkbox in page.locator('#notebook-chart-form input[name="g"]').all():
                checkbox.uncheck()
            page.locator('#notebook-chart-form button[type="submit"]').click()
            check(base + ' explicit empty preserves cards', page.locator('script.chart-data').count() == 0 and page.locator('article.card').count() == 3)
            page.goto(base + address([HICP, UNEMP]))
            page.locator('.chart-enhanced canvas').wait_for()
            payload = json.loads(page.locator('script.chart-data').inner_text())
            page.locator('.chart-canvas').scroll_into_view_if_needed()
            bounds = painted_bounds(page)
            check(base + ' painted grid', bounds['valid'])
            for point in (0, len(payload['x'])//2, len(payload['x'])-1):
                x = bounds['left'] + (bounds['right']-bounds['left'])*(payload['x'][point]-payload['x'][0])/(payload['x'][-1]-payload['x'][0])
                x += 1 if point == 0 else -1 if point == len(payload['x'])-1 else 0
                page.mouse.move(x, bounds['y'])
                expect(page.locator('.chart-readout')).to_have_text(exact(payload, point))
                check(base + ' exact pointer ' + str(point), True)
            page.emulate_media(media='print')
            check(base + ' print fallback', page.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1' and not page.locator('.notebook-chart-settings').is_visible())
            page.emulate_media(media='screen')
            for route in ('/healthz', '/comparar', '/fontes', '/metodologia', '/paginas', '/pesquisa?q=inflacao',
                          '/series/ine.hicp_yoy.PT', '/series/ine.hicp_yoy.PT.csv',
                          '/comparar/credito-e-taxa', '/comparar/paises/eletricidade-domestica'):
                check(base + route + ' HTTP200', context.request.get(base + route).status == 200)
            for asset in ('static/css/prumo.css', 'static/css/fonts.css', 'static/images/prumo/favicon.svg', 'static/js/prumo-charts.min.js'):
                response = context.request.get(base + '/' + asset)
                body = response.body()
                check(base + '/' + asset + ' exact bytes', response.status == 200 and body == (ROOT / asset).read_bytes())
                REPORT['assets'][base + '/' + asset] = {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
            check(base + ' invalid graph404', context.request.get(base + address([HICP], escala='invalid')).status == 404)
            context.close()
            for mode in ('no-js', 'blocked'):
                fallback = browser.new_context(java_script_enabled=mode != 'no-js', viewport={'width': 390, 'height': 1100})
                if mode == 'blocked':
                    fallback.route('**/static/js/prumo-charts.min.js*', lambda route: route.abort())
                p = fallback.new_page()
                p.goto(base + address([HICP, UNEMP]))
                check(base + ' SVG ' + mode, p.locator('svg.chart[role="img"]').count() == 1 and p.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1')
                check(base + ' full table ' + mode, p.locator('.table-details tbody tr').count() == len(payload['x']))
                p.locator('.nav-menu > summary').click()
                check(base + ' native menu ' + mode, p.locator('.site-nav-compact a:visible').count() == 9)
                fallback.close()
            mobile = browser.new_context(viewport={'width': 390, 'height': 1100}, has_touch=True, is_mobile=True)
            observe(mobile, base)
            p = mobile.new_page()
            page_events(p)
            p.goto(base + address([HICP, UNEMP]))
            p.locator('.chart-enhanced canvas').wait_for()
            payload = json.loads(p.locator('script.chart-data').inner_text())
            p.locator('.chart-canvas').scroll_into_view_if_needed()
            bounds = painted_bounds(p)
            check(base + ' touch grid', bounds['valid'])
            for point in (0, len(payload['x'])//2, len(payload['x'])-1):
                x = bounds['left']+(bounds['right']-bounds['left'])*(payload['x'][point]-payload['x'][0])/(payload['x'][-1]-payload['x'][0])
                p.touchscreen.tap(x, bounds['y'])
                expect(p.locator('.chart-readout')).to_have_text(exact(payload, point))
                check(base + ' exact touch ' + str(point), True)
            check(base + ' touch scroll', p.locator('.chart-canvas').evaluate('e=>getComputedStyle(e).touchAction') in ('pan-y', 'auto'))
            tree = mobile.new_cdp_session(p).send('Accessibility.getFullAXTree')['nodes']
            images = [n for n in tree if not n.get('ignored') and n.get('role', {}).get('value') == 'image']
            sliders = [n for n in tree if not n.get('ignored') and n.get('role', {}).get('value') == 'slider']
            check(base + ' named accessible chart', len(images) == 1 and 'Evolução conjunta' in images[0].get('name', {}).get('value', ''))
            check(base + ' named slider', len(sliders) == 1 and bool(sliders[0].get('name', {}).get('value')))
            mobile.close()
        request_context = browser.new_context()
        response = request_context.request.get('https://joao.date/dados/admin/cms/page/inicio', max_redirects=0)
        check('Admin challenges through Authelia', response.status in (302, 303, 307) and response.headers.get('location', '').startswith('https://authelia.joao.date/'))
        request_context.close()
        browser.close()
    check('no off-origin requests', not REPORT['external'])
    check('no page or CSP errors', not REPORT['errors'])
    known = [w for w in REPORT['warnings'] if 'Permissions-Policy' in w and 'vr' in w]
    check('only previously documented edge warnings', len(known) == len(REPORT['warnings']))
    REPORT['known_shared_edge_vr_warnings'] = len(known)
    with urlopen(Request(BASES[1] + '/static/js/prumo-charts.min.js', headers={'Accept-Encoding': 'gzip'}), timeout=40) as response:
        wire = response.read()
        encoding = response.headers.get('Content-Encoding', '')
        body = gzip.decompress(wire) if encoding == 'gzip' else wire
        check('actual edge bundle', body == (ROOT / 'static/js/prumo-charts.min.js').read_bytes())
        REPORT['transfer'] = {'content_encoding': encoding, 'wire_bytes': len(wire), 'decoded_bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    REPORT['complete'] = True


try:
    main()
except Exception as error:
    REPORT['failure'] = type(error).__name__ + ': ' + str(error)
    raise
finally:
    (OUT / 'public-smoke.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2))
    print(json.dumps({'complete': REPORT.get('complete', False), 'checks': len(REPORT['checks']), 'passed': sum(c['passed'] for c in REPORT['checks']), 'failure': REPORT.get('failure'), 'errors': REPORT['errors'], 'known_edge_warnings': REPORT.get('known_shared_edge_vr_warnings')}, ensure_ascii=False))
