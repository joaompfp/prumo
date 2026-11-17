"""Country comparisons: real-data browser acceptance, localhost and isolated DB only."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[5]
BASE = os.environ.get('PRUMO_QA_URL', 'http://127.0.0.1:8099')
DB = Path(os.environ['PRUMO_QA_DB']).resolve(strict=True)
if urlsplit(BASE).hostname not in ('127.0.0.1', 'localhost'):
    raise ValueError('Local acceptance only')
if not DB.is_relative_to(Path('/home/joao/.hermes/cache/scratch')):
    raise ValueError('Isolated scratch database required')
OUT = Path(os.environ.get('PRUMO_QA_OUT', Path(__file__).parent / 'browser'))
OUT.mkdir(parents=True, exist_ok=True)
SLUGS = ('eletricidade-domestica', 'pib-por-habitante', 'divida-publica')
COUNTS = (37, 31, 31)
LABELS = ['Portugal', 'Espanha', 'França', 'Alemanha', 'Itália']
report: dict = {'checks': [], 'errors': [], 'external': [], 'screens': []}


def check(name, condition):
    report['checks'].append({'name': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)


def fingerprint():
    result = {}
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as conn:
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            safe = name.replace('"', '""')
            body = hashlib.sha256()
            count = 0
            for row in conn.execute(f'SELECT * FROM "{safe}" ORDER BY rowid'):
                body.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode())
                body.update(b'\n')
                count += 1
            result[name] = {'rows': count, 'sha256': body.hexdigest()}
        check('quick_check', conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok')
        check('foreign keys', not conn.execute('PRAGMA foreign_key_check').fetchall())
    return result


def screenshot(page, name):
    page.screenshot(path=str(OUT / (name + '.png')), full_page=False)
    report['screens'].append(name + '.png')


def expected(payload, index):
    return payload['periods'][index] + ' - ' + '; '.join(
        f'{item["title"]}: {payload["display"][index][i]}'
        for i, item in enumerate(payload['series']))


def painted_bounds(page):
    return page.locator('.chart-canvas canvas').evaluate('''c => {
      const ctx=c.getContext('2d', {willReadFrequently:true});
      const d=ctx.getImageData(0,0,c.width,c.height).data;
      const probe=document.createElement('canvas').getContext('2d');
      probe.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--rule').trim();
      probe.fillRect(0,0,1,1);
      const target=probe.getImageData(0,0,1,1).data;
      let left=0,right=0,best=0,red=0;
      for(let y=0;y<c.height;y++) {
        let start=-1;
        for(let x=0;x<=c.width;x++) {
          const i=(y*c.width+x)*4;
          const match=x<c.width && d[i+3]>100 && Math.abs(d[i]-target[0])<5 && Math.abs(d[i+1]-target[1])<5 && Math.abs(d[i+2]-target[2])<5;
          if(match && start<0)start=x;
          if(!match && start>=0){if(x-start>best){best=x-start;left=start;right=x-1}start=-1}
          if(x<c.width && d[i+3]>200 && Math.abs(d[i]-155)<8 && Math.abs(d[i+1]-28)<8 && Math.abs(d[i+2]-46)<8)red++;
        }
      }
      const r=c.getBoundingClientRect();
      return {left:r.x+left*r.width/c.width,right:r.x+right*r.width/c.width,
              y:r.y+r.height/2,valid:best>c.width/2 && red>0};
    }''')


def main():
    before = fingerprint()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.environ.get('PRUMO_CHROMIUM', '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'),
            args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1440, 'height': 1100})
        context.on('request', lambda r: report['external'].append(r.url) if not r.url.startswith(BASE) else None)
        page = context.new_page()
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('console', lambda m: report['errors'].append(m.type + ': ' + m.text) if m.type in ('warning', 'error') else None)
        manifest = json.loads((ROOT / 'static/js/prumo-charts.manifest.json').read_text())
        asset = context.request.get(BASE + '/static/' + manifest['asset'])
        check('actual compiled asset', asset.status == 200 and hashlib.sha256(asset.body()).hexdigest() == manifest['sha256'])
        for prefix in ('', '/dados'):
            response = page.goto(BASE + prefix + '/comparar')
            check('index200 ' + prefix, response.status == 200)
            check('index scriptfree ' + prefix, page.locator('script').count() == 0)
            for slug in SLUGS:
                check('discoverable ' + prefix + slug, page.locator(f'a[href="{prefix}/comparar/paises/{slug}"]').count() == 1)
            for width in (1440, 768, 390, 320):
                page.set_viewport_size({'width': width, 'height': 1100})
                for slug, count in zip(SLUGS, COUNTS):
                    tag = f'{prefix}/{slug}/{width}'
                    response = page.goto(BASE + prefix + '/comparar/paises/' + slug)
                    check('HTTP200 ' + tag, response.status == 200)
                    page.evaluate('document.fonts.ready')
                    page.wait_for_selector('.chart-enhanced canvas')
                    payload = json.loads(page.locator('script.chart-data').inner_text())
                    check('five ordered countries ' + tag, [s['title'] for s in payload['series']] == LABELS)
                    check('same snapshot count ' + tag, len(payload['x']) == count and page.locator('.country-table tbody tr').count() == count)
                    check('one axis ' + tag, len(payload['axes']) == 1 and all(s['axis'] == 0 for s in payload['series']))
                    check('no page overflow ' + tag, page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    check('legend five ' + tag, page.locator('.legend > li').count() == 5)
                    check('provenance five ' + tag, page.locator('.country-provenance .provenance-list').count() == 5)
                    check('local fonts ' + tag, page.evaluate("document.fonts.check('25.5px Lato') && getComputedStyle(document.querySelector('h1')).fontFamily.includes('Schola')"))
                    check('punctuation ' + tag, chr(0x2014) not in page.locator('body').inner_text())
                    bounds = page.locator('svg.chart text').evaluate_all('''es=>es.map(e=>{const r=e.getBBox(),v=e.ownerSVGElement.viewBox.baseVal;return {x:r.x,right:r.x+r.width,width:v.width}})''')
                    check('SVG text contained ' + tag, bool(bounds) and all(r['x'] >= -1 and r['right'] <= r['width'] + 1 for r in bounds))
                    control = page.locator('.chart-range')
                    control.focus()
                    control.press('Home')
                    check('keyboard first exact ' + tag, page.locator('.chart-readout').inner_text() == expected(payload, 0))
                    control.press('ArrowRight')
                    check('keyboard second exact ' + tag, page.locator('.chart-readout').inner_text() == expected(payload, 1))
                    control.press('End')
                    check('keyboard last exact ' + tag, page.locator('.chart-readout').inner_text() == expected(payload, count - 1))
                    check('polite complete announcement ' + tag, page.locator('.chart-live').inner_text() == expected(payload, count - 1))
                    if not prefix and width in (1440, 390):
                        page.locator('h1').scroll_into_view_if_needed()
                        screenshot(page, slug + '-overview-' + str(width))
                        page.locator('.chart-figure').scroll_into_view_if_needed()
                        screenshot(page, slug + '-chart-' + str(width))
                    if slug == 'eletricidade-domestica':
                        page.locator('.chart-canvas').scroll_into_view_if_needed()
                        bounds = painted_bounds(page)
                        check('Carmim painted bounds ' + tag, bounds['valid'])
                        for point in (0, count // 2, count - 1):
                            x = bounds['left'] + (bounds['right'] - bounds['left']) * (payload['x'][point] - payload['x'][0]) / (payload['x'][-1] - payload['x'][0])
                            x += 1 if point == 0 else -1 if point == count - 1 else 0
                            page.mouse.move(x, bounds['y'])
                            report.setdefault('pointer_probes', []).append({'page': tag, 'point': point, 'bounds': bounds, 'x': x, 'actual': page.locator('.chart-range').input_value()})
                            expect(page.locator('.chart-readout')).to_have_text(expected(payload, point))
                            expected_tip = [payload['periods'][point]] + [f'{s["title"]}: {payload["display"][point][i]}' for i, s in enumerate(payload['series'])]
                            expect(page.locator('.chart-tip-line')).to_have_text(expected_tip)
                            check('pointer five exact tooltip ' + tag + str(point), page.locator('.chart-tip-line').all_text_contents() == expected_tip)
                        page.emulate_media(media='print')
                        check('print restores SVG ' + tag, page.locator('svg.chart').evaluate('e => getComputedStyle(e).opacity') == '1')
                        page.emulate_media(media='screen')
            for slug in ('credito-e-taxa', 'inflacao-e-desemprego'):
                response = page.goto(BASE + prefix + '/comparar/' + slug)
                check('old pair ' + prefix + slug, response.status == 200 and page.locator('.legend > li').count() == 2)
            response = context.request.get(BASE + prefix + '/comparar/paises/inexistente')
            check('unknown404 scriptfree ' + prefix, response.status == 404 and '<script src=' not in response.text())
        for mode in ('no-js', 'blocked'):
            ctx = browser.new_context(java_script_enabled=mode != 'no-js', viewport={'width': 390, 'height': 1100})
            if mode == 'blocked':
                ctx.route('**/static/js/prumo-charts.min.js*', lambda route: route.abort())
            p = ctx.new_page()
            p.goto(BASE + '/comparar/paises/eletricidade-domestica')
            check('fallback named SVG ' + mode, p.locator('svg.chart[role="img"]').count() == 1 and p.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity') == '1')
            check('fallback complete table ' + mode, p.locator('.country-table tbody tr').count() == COUNTS[0])
            check('fallback no overflow ' + mode, p.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            ctx.close()
        mobile = browser.new_context(viewport={'width': 390, 'height': 1100}, has_touch=True, is_mobile=True)
        p = mobile.new_page()
        p.goto(BASE + '/comparar/paises/eletricidade-domestica')
        p.wait_for_selector('.chart-enhanced canvas')
        payload = json.loads(p.locator('script.chart-data').inner_text())
        p.locator('.chart-canvas').scroll_into_view_if_needed()
        bounds = painted_bounds(p)
        for point in (0, len(payload['x']) // 2, len(payload['x']) - 1):
            x = bounds['left'] + (bounds['right'] - bounds['left']) * point / (len(payload['x']) - 1)
            p.touchscreen.tap(x, bounds['y'])
            expect(p.locator('.chart-readout')).to_have_text(expected(payload, point))
            check('touch exact ' + str(point), p.locator('.chart-readout').inner_text() == expected(payload, point))
        check('touch remains scrollable', p.evaluate('getComputedStyle(document.querySelector(".chart-canvas")).touchAction') in ('pan-y', 'auto'))
        mobile.close()
        check('no errors or warnings', not report['errors'])
        check('no external requests', not report['external'])
        browser.close()
    after = fingerprint()
    check('all tables unchanged', before == after)
    report['tables_before'] = before
    report['tables_after'] = after


try:
    main()
except Exception as exc:
    report['failure'] = type(exc).__name__ + ': ' + str(exc)
    raise
finally:
    (OUT / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'checks': len(report['checks']), 'passed': sum(c['passed'] for c in report['checks']), 'failure': report.get('failure'), 'report': str(OUT / 'acceptance.json')}, ensure_ascii=False))
