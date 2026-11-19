"""Local real-data acceptance of the notebook workspace. No source or CMS writes."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[5]
BASE = os.environ.get('PRUMO_QA_URL', 'http://127.0.0.1:8129')
OLD = os.environ.get('PRUMO_QA_BASELINE', 'http://127.0.0.1:8128')
OUT = Path(os.environ['PRUMO_QA_OUT'])
DB = Path(os.environ['PRUMO_QA_DB']).resolve(strict=True)
assert urlsplit(BASE).hostname in ('localhost', '127.0.0.1')
assert DB.is_relative_to('/home/joao/.hermes/cache/scratch')
OUT.mkdir(parents=True, exist_ok=True)
HICP, UNEMP = 'ine.hicp_yoy.PT', 'ine.unemployment_monthly.PT'
EUR3, EUR12, CREDIT = 'bportugal.euribor_3m.EA', 'bportugal.euribor_12m.EA', 'bportugal.credit_housing.PT'
REPORT: dict = {'checks': [], 'measurements': [], 'errors': [], 'external': [], 'screens': []}


def check(name, value):
    REPORT['checks'].append({'name': name, 'passed': bool(value)})
    if not value:
        raise AssertionError(name)


def address(ids, settings=()):
    return '/caderno?' + urlencode([('s', s) for s in ids] + list(settings))


PAIR = address([HICP, UNEMP])


def fingerprint():
    result = {}
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as db:
        check('copy quick check', db.execute('PRAGMA quick_check').fetchone()[0] == 'ok')
        check('copy foreign keys', not db.execute('PRAGMA foreign_key_check').fetchall())
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        for (name,) in tables:
            digest, count = hashlib.sha256(), 0
            safe = name.replace('"', '""')
            for row in db.execute(f'SELECT * FROM "{safe}" ORDER BY rowid'):
                digest.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode())
                digest.update(b'\n')
                count += 1
            result[name] = {'count': count, 'sha256': digest.hexdigest()}
    return result


def expected(payload, point):
    return payload['periods'][point] + ' - ' + '; '.join(
        f'{s["title"]}: {payload["display"][point][i]}' for i, s in enumerate(payload['series']))


def measure(page):
    return page.evaluate('''() => {
      const box = s => {const e=document.querySelector(s); if(!e)return null;
        const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height,bottom:r.bottom+scrollY}};
      return {viewport:{width:innerWidth,height:innerHeight},scroll:scrollY,
        canvas:box('.chart-canvas'),header:box('.site-header'),title:box('h1'),
        settings:box('.notebook-chart-settings'),sources:box('.notebook-chart-sources'),
        caption:box('.notebook-chart-caption'),add:box('a[href="#pesquisa"]'),
        body:parseFloat(getComputedStyle(document.body).fontSize),
        documentWidth:document.documentElement.scrollWidth};
    }''')


def load(page, path):
    response = page.goto(BASE + path)
    assert response is not None
    check('HTTP 200 ' + path, response.status == 200)
    page.evaluate('document.fonts.ready')
    if page.locator('script.chart-data').count():
        page.locator('.chart-enhanced canvas').wait_for()
    page.evaluate('window.scrollTo(0, 0)')
    return response


def capture(page, name):
    page.mouse.move(0, 0)
    page.evaluate('window.scrollTo(0, 0)')
    assert page.evaluate('scrollY') == 0
    page.screenshot(path=str(OUT / (name + '.png')))
    REPORT['screens'].append(name + '.png')


def run():
    REPORT['before'] = fingerprint()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
        ctx.on('request', lambda r: REPORT['external'].append(r.url) if not r.url.startswith(BASE) else None)
        page = ctx.new_page()
        page.on('pageerror', lambda e: REPORT['errors'].append(str(e)))
        page.on('console', lambda m: REPORT['errors'].append(m.text) if m.type in ('warning', 'error') else None)
        manifest = json.loads((ROOT / 'static/js/prumo-charts.manifest.json').read_text())
        asset = ctx.request.get(BASE + '/static/' + manifest['asset'])
        check('actual compiled chart asset', asset.status == 200 and hashlib.sha256(asset.body()).hexdigest() == manifest['sha256'])
        for prefix in ('', '/dados'):
            for width, height in ((320,844),(390,844),(768,1024),(899,1000),(900,1000),(901,1000),(1024,1000),(1440,1000),(1920,1080),(2560,1440),(3774,1870)):
                page.set_viewport_size({'width': width, 'height': height})
                response = load(page, prefix + PAIR)
                m = measure(page)
                m['prefix'] = prefix
                REPORT['measurements'].append(m)
                tag = f'{prefix}@{width}'
                check('no page overflow ' + tag, m['documentWidth'] <= width)
                check('body size preserved ' + tag, m['body'] >= 28.04)
                check('fonts loaded ' + tag, page.evaluate("document.fonts.check('28.05px Lato') && document.fonts.check('44px Schola')"))
                check('source next to plot ' + tag, m['sources']['y'] - m['canvas']['bottom'] < 45)
                if width in (1440,1920):
                    check('whole plot initially visible ' + tag, m['canvas']['bottom'] <= height)
                    check('add initially visible ' + tag, m['add']['bottom'] <= height)
                if width in (320,390):
                    check('usable mobile plot floor ' + tag, m['canvas']['height'] >= 263)
                    page.locator('.notebook-chart-settings > summary').click()
                    sizes = page.locator('.notebook-chart-pair select').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().width)')
                    check('full mobile select labels ' + tag, len(sizes) == 2 and min(sizes) >= 240)
                    page.locator('.notebook-chart-settings > summary').click()
                    check('mobile data starts in first view ' + tag, m['canvas']['y'] + 80 < height)
                    check('mobile common period before plot ' + tag, m['caption']['bottom'] <= m['canvas']['y'] + 1)
                if width == 3774:
                    check('wide chart grows both dimensions ' + tag, m['canvas']['width'] > 1700 and m['canvas']['height'] > 650)
                if not prefix and width in (390,1440,1920,3774):
                    capture(page, 'notebook-' + str(width))
                # Opening configuration is a native click; document position cannot change.
                before = m['canvas']['y']
                page.locator('.notebook-chart-settings > summary').click()
                check('settings do not displace plot ' + tag, abs(measure(page)['canvas']['y']-before) < 1)
                payload = json.loads(page.locator('script.chart-data').inner_text())
                for key, point in (('Home',0),('ArrowRight',1),('End',len(payload['x'])-1)):
                    page.locator('.chart-range').focus()
                    page.locator('.chart-range').press(key)
                    expect(page.locator('.chart-readout')).to_have_text(expected(payload, point))
                check('all plotted rows in table ' + tag, page.locator('.table-details tbody tr').count() == len(payload['x']))
                check('range outside forms ' + tag, page.locator('.chart-range').evaluate('e => e.form === null'))
                url = page.url
                page.locator('.chart-range').press('Enter')
                check('range Enter no navigation ' + tag, page.url == url)
                check('strict CSP ' + tag, "script-src 'self'" in response.headers['content-security-policy'] and 'unsafe-eval' not in response.headers['content-security-policy'])
        page.set_viewport_size({'width':1440,'height':1000})
        # Native link opens the configuration target without a script requirement.
        load(page, PAIR)
        page.locator('a[href="#definicoes"]').click()
        REPORT['settings_shortcut_opens'] = page.locator('#definicoes select[name="janela"]').is_visible()
        check('native settings shortcut opens panel', REPORT['settings_shortcut_opens'])
        check('configuration accessible label matches visible text', page.get_by_role('link', name='Configurar', exact=False).count() == 1)
        page.locator('#notebook-chart-form select[name="janela"]').select_option('5a')
        page.locator('#notebook-chart-form button').click()
        check('window retained in address', parse_qs(urlsplit(page.url).query)['janela'] == ['5a'])
        check('update returns to plot', urlsplit(page.url).fragment == 'grafico')
        page.locator('a[href="#pesquisa"]').click()
        page.locator('#notebook-search-form input[name="q"]').fill('euribor')
        page.locator('#notebook-search-form button').click()
        first = page.locator('.notebook-results a').filter(has_text='Acrescentar ao caderno').first
        first.click()
        query = parse_qs(urlsplit(page.url).query)
        check('add preserves existing group and window', len(query['s']) == 3 and query['g'] == [HICP,UNEMP] and query['janela'] == ['5a'])
        check('add returns to plot', urlsplit(page.url).fragment == 'grafico')
        # Off, deliberate empty and incompatible remain script-free, without blank evidence.
        for options, state in (([('grafico','off')],'off'),([('grafico','on')],'empty')):
            load(page, address([HICP,UNEMP], options))
            page.locator('#notebook-chart-form select[name="janela"]').select_option('5a')
            page.locator('#notebook-chart-form button').click()
            check('intent preserved ' + state, page.locator('#grafico').get_attribute('data-chart-state') == state)
            check('no blank evidence ' + state, page.locator('.provenance-details, .table-details, .notebook-definitions').count() == 0)
        load(page, address([HICP,CREDIT]))
        check('incompatible explanatory/scriptfree', page.locator('#grafico').get_attribute('data-chart-state') == 'unavailable' and page.locator('script[src]').count() == 0)
        for path, sides in ((address([EUR12,CREDIT],[('escala','dupla')]),2),(address([HICP,UNEMP,EUR3,EUR12]),4)):
            load(page,path)
            check('multi/dual payload population ' + path, len(json.loads(page.locator('script.chart-data').inner_text())['series']) == sides)
        load(page,PAIR)
        page.emulate_media(media='print')
        check('print SVG', page.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1')
        check('print sources and caveats', page.locator('.notebook-chart-sources').is_visible() and page.locator('.notebook-caveat').is_visible())
        check('print controls absent', not page.locator('#definicoes').is_visible())
        page.pdf(path=str(OUT/'notebook.pdf'), format='A4')
        page.emulate_media(media='screen')
        for mode in ('no-js','blocked'):
            fallback = browser.new_context(java_script_enabled=mode!='no-js',viewport={'width':390,'height':844})
            if mode == 'blocked': fallback.route('**/static/js/prumo-charts.min.js*',lambda r:r.abort())
            p = fallback.new_page()
            p.goto(BASE+'/dados'+PAIR)
            check('SVG fallback ' + mode,p.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity')=='1')
            fallback_box = p.locator('.chart-wrap').bounding_box()
            assert fallback_box is not None
            check('local SVG scroller ' + mode, fallback_box['width']>=660)
            check('fallback exact full table ' + mode,p.locator('.table-details tbody tr').count()==len(payload['x']))
            p.locator('.notebook-chart-settings > summary').click()
            p.locator('select[name="janela"]').select_option('5a')
            p.locator('#notebook-chart-form button').click()
            check('fallback native update ' + mode,parse_qs(urlsplit(p.url).query)['janela']==['5a'])
            fallback.close()
        check('no page/CSP errors',not REPORT['errors'])
        check('no external requests',not REPORT['external'])
        browser.close()
    REPORT['after'] = fingerprint()
    check('every table unchanged',REPORT['before']==REPORT['after'])


try:
    run()
except Exception as exc:
    REPORT['failure'] = type(exc).__name__ + ': ' + str(exc)
    raise
finally:
    (OUT/'acceptance.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
    print(json.dumps({'checks':len(REPORT['checks']),'passed':sum(c['passed'] for c in REPORT['checks']),'failure':REPORT.get('failure'),'settings_shortcut_opens':REPORT.get('settings_shortcut_opens'),'output':str(OUT)},ensure_ascii=False))
