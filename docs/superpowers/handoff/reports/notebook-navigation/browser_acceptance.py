"""Browser acceptance for notebook charts and shared navigation on an isolated copy."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[5]
BASE = os.environ.get('PRUMO_QA_URL', 'http://127.0.0.1:8107')
DB = Path(os.environ['PRUMO_QA_DB']).resolve(strict=True)
OUT = Path(os.environ['PRUMO_QA_OUT'])
if urlsplit(BASE).hostname not in ('localhost', '127.0.0.1'):
    raise ValueError('Only localhost acceptance is allowed')
if not DB.is_relative_to(Path('/home/joao/.hermes/cache/scratch')):
    raise ValueError('An isolated scratch DB is required')
OUT.mkdir(parents=True, exist_ok=True)
REPORT: dict = {'checks': [], 'errors': [], 'external': [], 'screens': [], 'sizes': []}
HICP = 'ine.hicp_yoy.PT'
UNEMP = 'ine.unemployment_monthly.PT'
EUR3 = 'bportugal.euribor_3m.EA'
EUR12 = 'bportugal.euribor_12m.EA'
CREDIT = 'bportugal.credit_housing.PT'
COUNTRIES = [f'eurostat.electricity_price.{geo}' for geo in ('PT', 'ES', 'FR', 'DE', 'IT')]


def check(name, passed):
    REPORT['checks'].append({'name': name, 'passed': bool(passed)})
    if not passed:
        raise AssertionError(name)


def fingerprint():
    answer = {}
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as conn:
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            safe = table.replace('"', '""')
            digest = hashlib.sha256()
            count = 0
            for row in conn.execute(f'SELECT * FROM "{safe}" ORDER BY rowid'):
                digest.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode())
                digest.update(b'\n')
                count += 1
            answer[table] = {'rows': count, 'sha256': digest.hexdigest()}
        check('quick_check', conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok')
        check('foreign_keys', not conn.execute('PRAGMA foreign_key_check').fetchall())
    return answer


def address(ids, **settings):
    return '/caderno?' + urlencode([('s', value) for value in ids] + list(settings.items()))


def exact(payload, point):
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
    page.screenshot(path=str(OUT / (name + '.png')), full_page=False)
    REPORT['screens'].append(name + '.png')


def main():
    before = fingerprint()
    # Resolve the actual existing family rather than inventing new data.
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as conn:
        candidates = conn.execute("SELECT id FROM series WHERE id LIKE 'eurostat.%' AND native_code LIKE 'nrg_pc_204:%' AND active=1 ORDER BY id").fetchall()
    electricity = []
    for geo in ('PT', 'ES', 'FR', 'DE', 'IT'):
        matches = [row[0] for row in candidates if row[0].endswith('.' + geo)]
        check('electricity family ' + geo, len(matches) == 1)
        electricity.append(matches[0])
    paths = [('/', 0), ('/caderno', 0), (address([HICP, UNEMP]), 2),
             (address([EUR3, EUR12, HICP]), 3), (address(electricity), 5),
             (address([EUR12, CREDIT], escala='dupla'), 2),
             (address([HICP, electricity[0]]), 0),
             (address(['eredes.production_market.PT', 'eredes.production_special.PT']), 2),
             ('/caderno?q=desemprego', 0), ('/metodologia', 0), ('/temas/economy', 0)]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('PRUMO_CHROMIUM', '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'), args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 1440, 'height': 1100})
        ctx.on('request', lambda req: REPORT['external'].append(req.url) if not req.url.startswith(BASE) else None)
        page = ctx.new_page()
        page.on('pageerror', lambda error: REPORT['errors'].append(str(error)))
        page.on('console', lambda message: REPORT['errors'].append(message.type + ': ' + message.text) if message.type in ('warning', 'error') else None)
        manifest = json.loads((ROOT / 'static/js/prumo-charts.manifest.json').read_text())
        asset = ctx.request.get(BASE + '/static/' + manifest['asset'])
        check('compiled asset bytes', asset.status == 200 and hashlib.sha256(asset.body()).hexdigest() == manifest['sha256'])
        for prefix in ('', '/dados'):
            for width in (320, 390, 768, 900, 901, 1024, 1440):
                page.set_viewport_size({'width': width, 'height': 1100})
                for path, series_count in paths:
                    tag = prefix + path + '@' + str(width)
                    response = page.goto(BASE + prefix + path)
                    assert response is not None
                    check('200 ' + tag, response.status == 200)
                    page.evaluate('document.fonts.ready')
                    check('no page overflow ' + tag, page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    check('large type ' + tag, page.locator('body').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 28.04)
                    check('local fonts ' + tag, page.evaluate("document.fonts.check('28.05px Lato') && getComputedStyle(document.querySelector('h1')).fontFamily.includes('Schola')"))
                    sizes = page.locator('.site-header .search').evaluate('e=>{const i=e.querySelector("input").getBoundingClientRect(),b=e.querySelector("button").getBoundingClientRect();return {a:i.height,b:b.height,y:i.y,z:b.y,right:i.right,left:b.left}}')
                    check('joined aligned search ' + tag, abs(sizes['a']-sizes['b']) < .6 and abs(sizes['y']-sizes['z']) < .6 and abs(sizes['right']-sizes['left']) < .6)
                    check('punctuation ' + tag, chr(0x2014) not in page.locator('body').inner_text())
                    if path.startswith('/caderno'):
                        check('noindex ' + tag, response.headers.get('x-robots-tag') == 'noindex, follow')
                    if series_count:
                        page.wait_for_selector('.chart-enhanced canvas')
                        payload = json.loads(page.locator('script.chart-data').inner_text())
                        check('group count ' + tag, len(payload['series']) == series_count)
                        check('complete table ' + tag, page.locator('.notebook-chart .table-details tbody tr').count() == len(payload['x']))
                        check('payload gated CSP ' + tag, "script-src 'self'" in response.headers['content-security-policy'])
                        control = page.locator('.chart-range')
                        for key, point in [('Home', 0), ('ArrowRight', min(1, len(payload['x'])-1)), ('End', len(payload['x'])-1)]:
                            control.focus()
                            control.press(key)
                            expect(page.locator('.chart-readout')).to_have_text(exact(payload, point))
                            check('keyboard exact ' + tag + key, page.locator('.chart-live').inner_text() == exact(payload, point))
                        if width == 1440 and not prefix:
                            REPORT['sizes'].append({'path': path, 'html_bytes': len(response.body()), 'points': len(payload['x']), 'series': len(payload['series'])})
                        for details_class in ('.table-details', '.notebook-definitions', '.provenance-details'):
                            disclosure = page.locator('.notebook-chart ' + details_class)
                            disclosure.locator('summary').first.click()
                            check('open detail no overflow ' + tag + details_class, page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                            disclosure.locator('summary').first.click()
                        if not prefix and width in (1440, 390) and path == address([HICP, UNEMP]):
                            page.locator('.chart-canvas').scroll_into_view_if_needed()
                            page.mouse.move(30, 30)
                            capture(page, 'notebook-chart-' + str(width))
                    else:
                        check('scriptfree ' + tag, page.locator('script[src]').count() == 0 and 'script-src ' not in response.headers['content-security-policy'])
                    if width > 900:
                        for index in (0, 1):
                            summary = page.locator('.site-nav > .nav-disclosure > summary').nth(index)
                            summary.click()
                            check('open panel no overflow ' + tag + str(index), page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                            summary.click()
                    else:
                        menu = page.locator('.nav-menu > summary')
                        menu.focus()
                        menu.press('Enter')
                        check('native menu open ' + tag, page.locator('.nav-menu').get_attribute('open') is not None)
                        check('open menu no overflow ' + tag, page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                        check('visible menu destinations ' + tag, page.locator('.site-nav-compact a:visible').count() == 9)
                        menu.press('Enter')
                    if not prefix and width in (1440, 390) and path == '/':
                        page.evaluate('window.scrollTo(0,0)')
                        capture(page, 'home-' + str(width))
        # Real native chart form: deliberate subset, scale change, explicit empty, and sharing.
        page.set_viewport_size({'width': 1440, 'height': 1100})
        page.goto(BASE + address([HICP, UNEMP, EUR3]))
        page.locator('.notebook-chart-settings > summary').click()
        form = page.locator('#notebook-chart-form')
        form.locator(f'input[name="g"][value="{EUR3}"]').uncheck()
        form.locator('select[name="janela"]').select_option('5a')
        form.locator('button[type="submit"]').click()
        page.wait_for_selector('.chart-enhanced canvas')
        check('form native subset', len(json.loads(page.locator('script.chart-data').inner_text())['series']) == 2)
        clean = page.locator('#ligacao-limpa').get_attribute('href')
        assert clean is not None
        check('share settings retained', 'grafico=on' in clean and 'janela=5a' in clean and clean.count('g=') == 2)
        page.locator('.notebook-chart-settings > summary').click()
        for checkbox in page.locator('#notebook-chart-form input[name="g"]').all():
            checkbox.uncheck()
        page.locator('#notebook-chart-form button[type="submit"]').click()
        check('empty does not select all', page.locator('script.chart-data').count() == 0 and page.locator('.card').count() == 3)
        # Painted pointer coordinates, not guessed thirds of the canvas.
        page.goto(BASE + address([HICP, UNEMP]))
        page.wait_for_selector('.chart-enhanced canvas')
        payload = json.loads(page.locator('script.chart-data').inner_text())
        page.locator('.chart-canvas').scroll_into_view_if_needed()
        bounds = painted_bounds(page)
        check('painted grid found', bounds['valid'])
        for point in (0, len(payload['x'])//2, len(payload['x'])-1):
            x = bounds['left'] + (bounds['right']-bounds['left'])*(payload['x'][point]-payload['x'][0])/(payload['x'][-1]-payload['x'][0])
            x += 1 if point == 0 else -1 if point == len(payload['x'])-1 else 0
            page.mouse.move(x, bounds['y'])
            expect(page.locator('.chart-readout')).to_have_text(exact(payload, point))
            expect(page.locator('.chart-tip-line')).to_have_text([payload['periods'][point]] + [f'{side["title"]}: {payload["display"][point][i]}' for i, side in enumerate(payload['series'])])
            check('pointer exact ' + str(point), True)
        page.emulate_media(media='print')
        check('print SVG', page.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1')
        check('print chart controls hidden', not page.locator('.notebook-chart-settings').is_visible())
        page.emulate_media(media='screen')
        for mode in ('no-js', 'blocked'):
            fallback = browser.new_context(java_script_enabled=mode != 'no-js', viewport={'width': 390, 'height': 1100})
            if mode == 'blocked':
                fallback.route('**/static/js/prumo-charts.min.js*', lambda route: route.abort())
            p = fallback.new_page()
            p.goto(BASE + '/dados' + address([HICP, UNEMP]))
            check('fallback SVG ' + mode, p.locator('svg.chart[role="img"]').count() == 1 and p.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1')
            check('fallback table ' + mode, p.locator('.table-details tbody tr').count() == len(payload['x']))
            p.locator('.nav-menu > summary').click()
            check('fallback menu ' + mode, p.locator('.site-nav-compact a:visible').count() == 9)
            fallback.close()
        mobile = browser.new_context(viewport={'width': 390, 'height': 1100}, has_touch=True, is_mobile=True)
        p = mobile.new_page()
        p.goto(BASE + address([HICP, UNEMP]))
        p.wait_for_selector('.chart-enhanced canvas')
        payload = json.loads(p.locator('script.chart-data').inner_text())
        p.locator('.chart-canvas').scroll_into_view_if_needed()
        bounds = painted_bounds(p)
        check('touch painted grid', bounds['valid'])
        for point in (0, len(payload['x'])//2, len(payload['x'])-1):
            x = bounds['left']+(bounds['right']-bounds['left'])*(payload['x'][point]-payload['x'][0])/(payload['x'][-1]-payload['x'][0])
            p.touchscreen.tap(x, bounds['y'])
            expect(p.locator('.chart-readout')).to_have_text(exact(payload, point))
            check('touch exact ' + str(point), True)
        check('touch scroll preserved', p.locator('.chart-canvas').evaluate('e=>getComputedStyle(e).touchAction') in ('pan-y', 'auto'))
        check('named accessible chart', 'Evolução conjunta' in (p.locator('svg.chart').get_attribute('aria-label') or ''))
        mobile.close()
        check('no page errors', not REPORT['errors'])
        check('no external requests', not REPORT['external'])
        browser.close()
    after = fingerprint()
    check('all tables unchanged', before == after)
    REPORT['before'] = before
    REPORT['after'] = after


try:
    main()
except Exception as error:
    REPORT['failure'] = type(error).__name__ + ': ' + str(error)
    raise
finally:
    (OUT / 'acceptance.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2))
    print(json.dumps({'checks': len(REPORT['checks']), 'passed': sum(c['passed'] for c in REPORT['checks']), 'failure': REPORT.get('failure'), 'output': str(OUT)}, ensure_ascii=False))
