"""Read-only acceptance of the approved notebook workspace on both installed mounts."""
import gzip
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path('/home/joao/projects/prumo-pipeline')
OUT = Path(os.environ['PRUMO_PROD_OUT']).resolve()
OUT.mkdir(parents=True, exist_ok=False)
BASES = ('https://cae.joao.date', 'https://joao.date/dados')
HICP, UNEMP = 'ine.hicp_yoy.PT', 'ine.unemployment_monthly.PT'
EUR12, CREDIT = 'bportugal.euribor_12m.EA', 'bportugal.credit_housing.PT'
SIX = [HICP, UNEMP] + ['bportugal.' + n + '.EA' for n in ('euribor_1m', 'euribor_3m', 'euribor_6m', 'euribor_12m')]
REPORT = {'checks': [], 'measurements': [], 'errors': [], 'warnings': [], 'external': [], 'screens': []}


def check(label, condition):
    REPORT['checks'].append({'check': label, 'passed': bool(condition)})
    assert condition, label


def address(ids, settings=()):
    return '/caderno?' + urlencode([('s', s) for s in ids] + list(settings))


def exact(payload, point):
    return payload['periods'][point] + ' - ' + '; '.join(
        side['title'] + ': ' + payload['display'][point][i]
        for i, side in enumerate(payload['series']))


def measure(page):
    return page.evaluate('''() => {
      const box=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();
        return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height,bottom:r.bottom+scrollY}};
      return {viewport:{width:innerWidth,height:innerHeight},scroll:scrollY,canvas:box('.chart-canvas'),
        caption:box('.notebook-chart-caption'),sources:box('.notebook-chart-sources'),add:box('a[href="#pesquisa"]'),
        body:parseFloat(getComputedStyle(document.body).fontSize),documentWidth:document.documentElement.scrollWidth};
    }''')


def load(page, base, path):
    r = page.goto(base + path)
    check('HTTP200 ' + base + path, r is not None and r.status == 200)
    page.evaluate('document.fonts.ready')
    if page.locator('script.chart-data').count():
        page.locator('.chart-enhanced canvas').wait_for()
    page.mouse.move(0, 0)
    page.evaluate('window.scrollTo(0,0)')
    return r


def observe(context, base):
    context.on('request', lambda r: REPORT['external'].append(r.url)
               if urlsplit(r.url).netloc != urlsplit(base).netloc else None)
    context.on('page', lambda p: events(p))


def events(page):
    page.on('pageerror', lambda e: REPORT['errors'].append(str(e)))
    page.on('console', lambda m: REPORT['errors'].append(m.text) if m.type == 'error'
            else REPORT['warnings'].append(m.text) if m.type == 'warning' else None)


def grid(page):
    return page.locator('.chart-canvas canvas').evaluate('''c => {
      const ctx=c.getContext('2d',{willReadFrequently:true});const d=ctx.getImageData(0,0,c.width,c.height).data;
      const probe=document.createElement('canvas').getContext('2d',{willReadFrequently:true});
      probe.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--rule').trim();probe.fillRect(0,0,1,1);
      const t=probe.getImageData(0,0,1,1).data;let left=0,right=0,best=0;
      for(let y=0;y<c.height;y++){let start=-1;for(let x=0;x<=c.width;x++){
        const i=(y*c.width+x)*4;const yes=x<c.width&&d[i+3]>100&&Math.abs(d[i]-t[0])<5&&Math.abs(d[i+1]-t[1])<5&&Math.abs(d[i+2]-t[2])<5;
        if(yes&&start<0)start=x;if(!yes&&start>=0){if(x-start>best){best=x-start;left=start;right=x-1}start=-1}
      }}const r=c.getBoundingClientRect();return {left:r.x+left*r.width/c.width,right:r.x+right*r.width/c.width,y:r.y+r.height/2,valid:best>c.width/3};
    }''')


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
        for base in BASES:
            suffix = 'mounted' if '/dados' in base else 'direct'
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            observe(context, base)
            page = context.new_page()
            for width, height in ((320,844),(390,844),(768,1024),(899,1000),(900,1000),(901,1000),(1024,1000),(1440,1000),(1920,1080),(2560,1440),(3774,1870)):
                page.set_viewport_size({'width': width, 'height': height})
                response = load(page, base, address([HICP, UNEMP]))
                m = measure(page)
                m['base'] = base
                REPORT['measurements'].append(m)
                label = suffix + '@' + str(width)
                check('no overflow ' + label, m['documentWidth'] <= width)
                check('large local fonts ' + label, m['body'] >= 28.04 and page.evaluate("document.fonts.check('28.05px Lato') && document.fonts.check('44px Schola')"))
                check('common caption above plot ' + label, m['caption']['bottom'] <= m['canvas']['y'] + 1)
                check('sources beside result ' + label, m['sources']['y'] - m['canvas']['bottom'] < 45)
                if width in (390,1440,1920):
                    check('complete chart in first view ' + label, m['canvas']['bottom'] <= height)
                    check('composition in first view ' + label, m['add']['bottom'] <= height)
                if width in (320,390):
                    check('mobile plot preserved ' + label, m['canvas']['height'] >= 263)
                if width == 3774:
                    check('wide plot grows ' + label, m['canvas']['width'] > 1700 and m['canvas']['height'] > 650)
                if width in (390,1440,1920,3774):
                    check('neutral capture ' + label, page.evaluate('scrollY') == 0)
                    name = 'notebook-' + suffix + '-' + str(width) + '.png'
                    page.screenshot(path=str(OUT / name))
                    REPORT['screens'].append(name)
                before = m['canvas']['y']
                page.locator('.notebook-chart-settings > summary').click()
                check('configuration does not displace plot ' + label, abs(measure(page)['canvas']['y'] - before) < 1)
                payload = json.loads(page.locator('script.chart-data').inner_text())
                for key, point in (('Home',0),('ArrowRight',1),('End',len(payload['x'])-1)):
                    page.locator('.chart-range').focus()
                    page.locator('.chart-range').press(key)
                    expect(page.locator('.chart-readout')).to_have_text(exact(payload, point))
                    check('exact keyboard ' + label + '/' + key, page.locator('.chart-live').inner_text() == exact(payload, point))
                check('complete table ' + label, page.locator('.table-details tbody tr').count() == len(payload['x']))
                check('range not in settings form ' + label, page.locator('.chart-range').evaluate('e=>e.form===null'))
                current = page.url
                page.locator('.chart-range').press('Enter')
                check('range Enter no navigation ' + label, page.url == current)
                check('strict script policy ' + label, "script-src 'self'" in response.headers['content-security-policy'] and 'unsafe-eval' not in response.headers['content-security-policy'])
                check('authored typography ' + label, chr(0x2014) not in page.locator('body').inner_text())
            page.set_viewport_size({'width':1440,'height':1000})
            load(page, base, address([HICP,UNEMP]))
            page.get_by_role('link', name='Configurar', exact=False).click()
            check(base + ' native configuration opens', page.locator('#definicoes select[name="janela"]').is_visible())
            page.locator('#notebook-chart-form select[name="janela"]').select_option('5a')
            page.locator('#notebook-chart-form button').click()
            check(base + ' native window and return', parse_qs(urlsplit(page.url).query)['janela'] == ['5a'] and urlsplit(page.url).fragment == 'grafico')
            page.locator('a[href="#pesquisa"]').click()
            page.locator('#notebook-search-form input[name="q"]').fill('euribor')
            page.locator('#notebook-search-form button').click()
            page.locator('.notebook-results a').filter(has_text='Acrescentar ao caderno').first.click()
            query = parse_qs(urlsplit(page.url).query)
            check(base + ' add preserves group/window', len(query['s']) == 3 and query['g'] == [HICP,UNEMP] and query['janela'] == ['5a'])
            for ids, options, state, sides in (
                ([HICP,UNEMP],[('grafico','off')],'off',0), ([HICP,UNEMP],[('grafico','on')],'empty',0),
                ([HICP,CREDIT],[],'unavailable',0), (SIX,[],'ready',6),
                ([EUR12,CREDIT],[('escala','dupla')],'ready',2),
            ):
                load(page,base,address(ids, options))
                check(base + ' honest state ' + state, page.locator('#grafico').get_attribute('data-chart-state') == state)
                if sides:
                    p = json.loads(page.locator('script.chart-data').inner_text())
                    check(base + ' population ' + str(sides), len(p['series']) == sides and page.locator('.notebook-chart-sources li').count() == sides)
                    check(base + ' full table ' + str(sides), page.locator('.table-details tbody tr').count() == len(p['x']))
                    if options:
                        check(base + ' deliberate dual axes', len(p['axes']) == 2)
                else:
                    check(base + ' scriptfree undrawable', page.locator('script[src]').count() == 0)
                    check(base + ' no blank evidence', page.locator('.provenance-details,.table-details,.notebook-definitions').count() == 0)
            load(page,base,address([HICP,UNEMP]))
            payload = json.loads(page.locator('script.chart-data').inner_text())
            page.locator('.chart-canvas').scroll_into_view_if_needed()
            bounds = grid(page)
            check(base + ' painted plot', bounds['valid'])
            for point in (0,len(payload['x'])//2,len(payload['x'])-1):
                x = bounds['left'] + (bounds['right']-bounds['left'])*(payload['x'][point]-payload['x'][0])/(payload['x'][-1]-payload['x'][0])
                x += 1 if point == 0 else -1 if point == len(payload['x'])-1 else 0
                page.mouse.move(x,bounds['y'])
                expect(page.locator('.chart-readout')).to_have_text(exact(payload,point))
                check(base + ' exact painted point ' + str(point),True)
            page.emulate_media(media='print')
            check(base + ' print SVG and caveats', page.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1' and page.locator('.notebook-caveat').is_visible() and page.locator('.notebook-chart-sources').is_visible())
            check(base + ' no print configuration', not page.locator('#definicoes').is_visible())
            page.emulate_media(media='screen')
            for path in ('/','/healthz','/comparar','/comparar/credito-e-taxa','/comparar/paises/eletricidade-domestica','/fontes','/metodologia','/paginas','/pesquisa?q=inflacao','/series/ine.hicp_yoy.PT','/series/ine.hicp_yoy.PT.csv'):
                check('public route ' + base + path, context.request.get(base + path).status == 200)
            for asset in ('static/css/prumo.css','static/css/fonts.css','static/images/prumo/favicon.svg','static/js/prumo-charts.min.js'):
                r = context.request.get(base + '/' + asset)
                check('exact installed asset ' + base + '/' + asset,r.status == 200 and r.body() == (ROOT / asset).read_bytes())
            check(base + ' unknown scale404',context.request.get(base + address([HICP],[('escala','invalid')])).status == 404)
            context.close()
            for mode in ('no-js','blocked'):
                c = browser.new_context(java_script_enabled=mode!='no-js', viewport={'width':390,'height':844})
                if mode == 'blocked':
                    c.route('**/static/js/prumo-charts.min.js*',lambda r:r.abort())
                p = c.new_page()
                p.goto(base + address([HICP,UNEMP]))
                check(base + ' SVG fallback ' + mode,p.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1')
                check(base + ' fallback table ' + mode,p.locator('.table-details tbody tr').count() == len(payload['x']))
                p.get_by_role('link',name='Configurar',exact=False).click()
                check(base + ' native fallback settings ' + mode,p.locator('#definicoes select[name="janela"]').is_visible())
                c.close()
            touch = browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
            observe(touch,base)
            p = touch.new_page()
            load(p,base,address([HICP,UNEMP]))
            payload = json.loads(p.locator('script.chart-data').inner_text())
            p.locator('.chart-canvas').scroll_into_view_if_needed()
            bounds = grid(p)
            check(base + ' touch painted plot',bounds['valid'])
            for point in (0,len(payload['x'])//2,len(payload['x'])-1):
                x = bounds['left'] + (bounds['right']-bounds['left'])*(payload['x'][point]-payload['x'][0])/(payload['x'][-1]-payload['x'][0])
                p.touchscreen.tap(x,bounds['y'])
                expect(p.locator('.chart-readout')).to_have_text(exact(payload,point))
                check(base + ' exact touch ' + str(point),True)
            nodes = touch.new_cdp_session(p).send('Accessibility.getFullAXTree')['nodes']
            sliders = [n for n in nodes if not n.get('ignored') and n.get('role',{}).get('value') == 'slider']
            check(base + ' named range in accessibility tree',len(sliders) == 1 and bool(sliders[0].get('name',{}).get('value')))
            touch.close()
        c = browser.new_context()
        r = c.request.get('https://joao.date/dados/admin/cms/page/inicio',max_redirects=0)
        check('Admin still challenges through Authelia',r.status in (302,303,307) and r.headers.get('location','').startswith('https://authelia.joao.date/'))
        c.close()
        browser.close()
    check('no page/CSP errors',not REPORT['errors'])
    check('no off-origin requests',not REPORT['external'])
    known = [w for w in REPORT['warnings'] if 'Permissions-Policy' in w and 'vr' in w]
    check('only recorded shared-edge warnings',len(known) == len(REPORT['warnings']))
    REPORT['known_edge_warnings'] = len(known)
    with urlopen(Request(BASES[1] + '/static/js/prumo-charts.min.js',headers={'Accept-Encoding':'gzip'}),timeout=40) as r:
        wire = r.read()
        encoding = r.headers.get('Content-Encoding','')
        decoded = gzip.decompress(wire) if encoding == 'gzip' else wire
        check('actual edge bundle bytes',decoded == (ROOT / 'static/js/prumo-charts.min.js').read_bytes())
        REPORT['transfer'] = {'encoding':encoding,'wire_bytes':len(wire),'decoded_bytes':len(decoded),'sha256':hashlib.sha256(decoded).hexdigest()}
    REPORT['complete'] = True


try:
    main()
except Exception as exc:
    REPORT['failure'] = type(exc).__name__ + ': ' + str(exc)
    raise
finally:
    (OUT / 'acceptance.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
    print(json.dumps({'checks':len(REPORT['checks']),'passed':sum(c['passed'] for c in REPORT['checks']),'complete':REPORT.get('complete',False),'failure':REPORT.get('failure'),'errors':REPORT['errors'],'known_edge_warnings':REPORT.get('known_edge_warnings')},ensure_ascii=False))
