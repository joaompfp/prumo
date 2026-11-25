"""Read-only phase C acceptance against a disposable, populated production copy.

Run with system Python (Playwright installed), --origin for the candidate QA server
and --baseline for the installed code serving the SAME isolated database. Never
publish content or open a live source database through this helper.
"""
import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from ingest.db import read_db_readonly  # noqa: E402

CHROME = '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'


def fingerprint(path):
    def read(db):
        conn = db.conn
        tables = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + name.replace('"', '""') + '"'
            columns = len(conn.execute(f'PRAGMA table_info({quoted})').fetchall())
            order = ','.join(str(index + 1) for index in range(columns))
            digest, count = hashlib.sha256(), 0
            for row in conn.execute(f'SELECT * FROM {quoted} ORDER BY {order}'):
                digest.update(json.dumps(list(row), ensure_ascii=False, default=repr).encode())
                digest.update(b'\n')
                count += 1
            tables[name] = {'rows': count, 'sha256': digest.hexdigest()}
        schema = [list(row) for row in conn.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')]
        return {'tables': tables, 'schema': hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
                'integrity': conn.execute('PRAGMA quick_check').fetchone()[0],
                'foreign_keys': conn.execute('PRAGMA foreign_key_check').fetchall()}
    return read_db_readonly(path, read)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.db = args.db.resolve(strict=True)
    if not args.db.is_relative_to(Path('/home/joao/.hermes/cache/scratch')):
        raise ValueError('Only an isolated scratch database is allowed')
    args.output.mkdir(parents=True, exist_ok=False)
    checks, measures, errors, requests, journeys = [], [], [], [], []
    benchmarks, completed = [], False
    before = fingerprint(args.db)

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
            context = browser.new_context()
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.on('request', lambda request: requests.append(request.url))
            # Matched before/after screenshots and measured functional reading sizes.
            for label, origin in (('before', args.baseline), ('after', args.origin)):
                for width, height in ((390,844),(1440,1000)):
                    page.set_viewport_size({'width': width, 'height': height})
                    for name, path in (('search','/pesquisa?q=desemprego+Portugal'),
                                       ('theme','/temas/energy'), ('home','/')):
                        response = page.goto(origin + '/dados' + path)
                        check(f'{label}-{width}-{name}-200', response.status == 200)
                        page.evaluate('document.fonts.ready')
                        page.locator('h1').click()
                        page.evaluate('scrollTo(0,0)')
                        check(f'{label}-{width}-{name}-top', page.evaluate('scrollY') == 0)
                        page.screenshot(path=str(args.output / f'{label}-{name}-{width}.png'))
                        selector = '.series-result-value' if label == 'after' else '.data-table td'
                        measures.append({'phase': label, 'name': name, 'width': width,
                            'body': page.locator('body').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)'),
                            'nav': page.locator('.site-nav > a').first.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)'),
                            'value': page.locator(selector).first.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') if page.locator(selector).count() else None,
                            'first_result': page.locator('.series-result').first.bounding_box() if page.locator('.series-result').count() else None})
            for prefix in ('', '/dados'):
                for width in (320,390,600,601,768,820,821,900,901,1024,1100,1101,1440,1920):
                    page.set_viewport_size({'width': width, 'height': 844 if width < 700 else 1000})
                    for name, path in (('catalogue','/pesquisa'), ('search','/pesquisa?q=desemprego+Portugal'),
                                       ('theme','/temas/energy'), ('home','/')):
                        response = page.goto(args.origin + prefix + path)
                        tag = f'{prefix}-{width}-{name}'
                        check(tag+'-200', response.status == 200)
                        page.evaluate('document.fonts.ready')
                        check(tag+'-overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                        check(tag+'-body', page.locator('body').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 28.05)
                        check(tag+'-one-search', page.locator('input[type=search]').count() == 1)
                        check(tag+'-script-free', page.locator('script').count() == 0)
                        check(tag+'-strict-csp', "default-src 'none'" in response.headers['content-security-policy'])
                        check(tag+'-local-assets', page.locator('link[rel=stylesheet][href$="/discovery.css"]').count() == 1)
                        if name != 'home':
                            check(tag+'-populated', page.locator('.series-result').count() > 0)
                            first = page.locator('.series-result').first
                            check(tag+'-value-intact', first.locator('.series-result-number').evaluate('e=>e.scrollWidth <= e.clientWidth+1')
                                  if first.locator('.series-result-number').evaluate('e=>e.clientWidth') else True)
                            check(tag+'-value-size', first.locator('.series-result-value').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 28.05)
                            if name in ('search','theme') and width in (390,1440):
                                box = first.locator('.series-result-value').bounding_box()
                                check(tag+'-data-in-first-view', box['y'] + box['height'] < page.viewport_size['height'])
                        menu = page.locator('.nav-menu')
                        if menu.is_visible():
                            menu.locator('summary').click()
                            check(tag+'-menu-overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                            check(tag+'-menu-catalogue', menu.get_by_role('link', name='Catálogo', exact=True).is_visible())
                            menu.locator('summary').click()
                        else:
                            for disclosure in page.locator('.site-nav > details').all():
                                disclosure.locator('summary').click()
                                box = disclosure.locator('ul').bounding_box()
                                check(tag+'-panel-edge', box['x'] >= 0 and box['x']+box['width'] <= width+1)
                                disclosure.locator('summary').click()
                # Task journeys are repeated on mobile/desktop, with and without JS below.
                for js in (True, False):
                    task_context = browser.new_context(java_script_enabled=js, viewport={'width':390 if not js else 1440,'height':1000})
                    task = task_context.new_page()
                    task.goto(args.origin + prefix + '/pesquisa')
                    task.get_by_label('Pesquisar indicadores', exact=True).fill('desemprego Portugal')
                    task.get_by_role('button', name='Procurar', exact=True).click()
                    task.locator(f'main a[href="{prefix}/series/ine.unemployment_monthly.PT"]').click()
                    notebook_link = task.locator(f'a[href="{prefix}/caderno?s=ine.unemployment_monthly.PT"]')
                    disclosure = task.locator('details').filter(has=notebook_link)
                    if not notebook_link.is_visible():
                        disclosure.locator('summary').first.click()
                    notebook_link.click()
                    search = task.locator('#notebook-search-form')
                    search.locator('input[name=q]').fill('IHPC')
                    search.get_by_role('button').click()
                    result = task.locator('.notebook-results tr').filter(has=task.locator('a[href*="s=ine.hicp_yoy.PT"]')).first
                    result.get_by_role('link', name='Acrescentar ao caderno', exact=True).click()
                    clean = task.locator('#ligacao-limpa').get_attribute('href')
                    params = parse_qs(urlparse(clean).query)
                    check(f'{prefix}-{js}-ordered-selection', params['s'] == ['ine.unemployment_monthly.PT','ine.hicp_yoy.PT'])
                    check(f'{prefix}-{js}-clean-address', 'q' not in params)
                    reopen = task_context.new_page()
                    check(f'{prefix}-{js}-shared-200', reopen.goto(args.origin + clean).status == 200)
                    check(f'{prefix}-{js}-shared-cards', reopen.locator('.notebook-selection .card').count() == 2)
                    journeys.append({'prefix':prefix, 'javascript':js, 'shared_path':clean, 'passed':True})
                    # Unsubmitted query edits and filters are submitted together by the same native form.
                    task.goto(args.origin + prefix + '/pesquisa?q=desemprego')
                    task.get_by_label('Pesquisar indicadores',exact=True).fill('industrial')
                    task.locator('.discovery-filters > summary').click()
                    task.locator('select[name=grupo]').select_option('pt')
                    task.get_by_role('button', name='Aplicar filtros',exact=True).click()
                    params = parse_qs(urlparse(task.url).query)
                    check(f'{prefix}-{js}-query-filter-state',params.get('q') == ['industrial'] and params.get('grupo') == ['pt'])
                    task.goto(args.origin + prefix + '/pesquisa?tema=inexistente')
                    check(f'{prefix}-{js}-invalid-selection-honest',task.locator('select[name=tema]').input_value() == 'inexistente')
                    task_context.close()
                page.goto(args.origin + prefix + '/pesquisa?q=emprego')
                first_names = page.locator('.series-result-title').all_text_contents()
                check(prefix+'-real-pagination',page.locator('a[rel=next]').count() == 1)
                page.locator('a[rel=next]').click()
                check(prefix+'-page-changes',page.locator('.series-result-title').all_text_contents() != first_names)
                page.goto(args.origin + prefix + '/')
                check(prefix+'-home-cards',page.locator('a.card-create').count() > 0)
                page.locator('a.card-create').first.click()
                check(prefix+'-home-to-notebook',page.locator('.notebook-selection .card').count() == 1)
                page.goto(args.origin + prefix + '/comparar')
                hrefs = sorted(set(page.locator('main a[href*="/comparar/"]').evaluate_all('es=>es.map(e=>e.getAttribute("href"))')))
                check(prefix+'-nine-cms-comparisons',len(hrefs) == 9)
                for href in hrefs:
                    check(href+'-200',page.goto(args.origin+href).status == 200)
                    page.wait_for_selector('.chart-enhanced canvas')
                    check(href+'-no-editor',page.locator('main select[name=scale],main select[name=escala],main select[name^=series_]').count() == 0)
                    slider = page.locator('.chart-range').first
                    slider.focus()
                    slider.press('End')
                    data = json.loads(page.locator('.chart-data').first.text_content())
                    expected = [v if v is not None else data['missing'] for v in data['display'][-1]]
                    expect(page.locator('.chart-readout-value')).to_have_text(expected)
                    check(href+'-exact-reading',True)
            page.goto(args.origin+'/dados/admin/cms/page/inicio/preview')
            check('static-preview-cards',page.locator('a.card-create').count() > 0)
            check('static-preview-no-executable-scripts',page.locator('script[src],script:not([type="application/json"])').count() == 0)
            css = context.request.get(args.origin+'/dados/static/css/discovery.css')
            check('served-stylesheet-200',css.status == 200)
            check('served-stylesheet-bytes',css.body() == (ROOT/'static/css/discovery.css').read_bytes())
            # Measure actual local HTTP responses, separately from installed-edge performance.
            for origin, phase in ((args.baseline,'before'),(args.origin,'after')):
                for route in ('/pesquisa?q=desemprego+Portugal','/pesquisa','/temas/energy'):
                    timings = []
                    for index in range(22):
                        started = time.perf_counter()
                        response = context.request.get(origin+route)
                        body = response.body()
                        if response.status != 200:
                            raise AssertionError('Benchmark response is not usable')
                        if index >= 2:
                            timings.append((time.perf_counter()-started)*1000)
                    benchmarks.append({'phase':phase,'route':route,'samples':len(timings),
                        'median_ms':statistics.median(timings),'p95_ms':sorted(timings)[18],
                        'html_bytes':len(body),'concurrency':1})
            page.goto(args.origin+'/dados/pesquisa')
            page.get_by_label('Pesquisar indicadores',exact=True).focus()
            page.keyboard.press('Tab')
            check('keyboard-query-submit',page.locator(':focus').inner_text() == 'Procurar')
            focus = page.locator(':focus').evaluate('e=>({width:parseFloat(getComputedStyle(e).outlineWidth),style:getComputedStyle(e).outlineStyle})')
            check('visible-keyboard-focus',focus['width'] >= 2 and focus['style'] != 'none')
            page.emulate_media(media='print')
            check('print-hides-query',not page.locator('.discovery-query').is_visible())
            check('print-retains-data',page.locator('.series-result').first.is_visible())
            page.emulate_media(media='screen')
            check('no-browser-errors',not errors)
            allowed = {urlparse(args.origin).netloc,urlparse(args.baseline).netloc}
            check('no-external-requests',all(urlparse(url).netloc in allowed for url in requests))
            browser.close()
        after = fingerprint(args.db)
        check('all-tables-schema-unchanged',before == after)
        completed = True
    finally:
        after = fingerprint(args.db)
        result = {'checks':checks,'passed':completed and all(row['passed'] for row in checks), 'measurements':measures,
                  'benchmarks':benchmarks,'journeys':journeys,'errors':errors,'before':before,'after':after}
        (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':len(checks),'journeys':len(journeys),'tables':len(before['tables'])}))


if __name__ == '__main__':
    main()
