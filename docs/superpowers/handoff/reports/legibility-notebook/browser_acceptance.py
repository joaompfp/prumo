"""Real-data browser acceptance. Run only against qa_server and a scratch SQLite copy."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]
BASE = os.environ.get("PRUMO_QA_URL", "http://127.0.0.1:8124")
DB = Path(os.environ["PRUMO_QA_DB"]).resolve(strict=True)
if not DB.is_relative_to(Path('/home/joao/.hermes/cache/scratch')):
    raise ValueError('Acceptance requires an isolated scratch database')
OUT = Path(os.environ.get('PRUMO_QA_OUT', Path(__file__).parent / 'browser'))
OUT.mkdir(parents=True, exist_ok=True)
AUDIT = Path(__file__).resolve().parent / 'baseline'
PUBLIC_BASELINE = json.loads((AUDIT / 'public_measure.json').read_text())
ADMIN_BASELINE = json.loads((AUDIT / 'bo_measure.json').read_text())
PUB = {
    'body':'body', 'h1':'h1', 'h2':'h2', 'h3':'h3', 'nav':'.site-nav a',
    'lede':'.lede', 'eyebrow':'.eyebrow', 'card_label':'.card-label',
    'card_value':'.card-value', 'card_unit':'.card-unit', 'card_period':'.card-period',
    'card_source':'.card-source', 'card_link':'.card-link', 'badge':'.badge',
    'theme_title':'.theme-title', 'theme_blurb':'.theme-blurb', 'footer':'.site-footer p',
    'table':'.data-table', 'th':'.data-table th', 'td':'.data-table td',
    'figure_meta':'.figure-meta', 'figure_value':'.figure-value', 'button':'.button',
    'compare_link':'.compare-link', 'search':'.search input', 'chart_tick':'.chart-tick',
    'chart_readout':'.chart-readout', 'figcaption':'.chart-figure figcaption',
}
BO = {
    'body':'body', 'h1':'h1', 'h2':'h2', 'h3':'h3', 'lede':'.page-sub, .lede, .section-note',
    'nav':'.nav-link', 'nav_label':'.nav-label', 'meta':'.crumbs, .page-sub',
    'card_title':'.card-title', 'metric_label':'.metric-label', 'metric_value':'.metric-value',
    'table':'.table', 'th':'.table > thead > tr > th', 'td':'.table > tbody > tr > td',
    'form_label':'.field > .form-label, .field-label', 'hint':'.form-hint, .field .hint',
    'badge':'.badge', 'button':'.btn', 'editor_title':'.editor-title',
    'editor_status':'.editor-status', 'summary':'details.block-card > summary',
    'block_kind':'.block-kind', 'caveat':'.caveat',
}
MEASURE = """sels => Object.fromEntries(Object.entries(sels).map(([k,s])=> {
  const all=Array.from(document.querySelectorAll(s));
  const e=all.find(e=>e.getClientRects().length) || all[0];
  return [k,e?{size:getComputedStyle(e).fontSize,family:getComputedStyle(e).fontFamily}:null];
}))"""
report: dict = {'checks':[], 'ratios':[], 'errors':[], 'warnings':[], 'external':[], 'screens':[]}


def check(name, condition):
    report['checks'].append({'name':name, 'passed':bool(condition)})
    if not condition:
        raise AssertionError(name)


def fingerprints(include_cms=False):
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as conn:
        result = {}
        names = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        for (name,) in names:
            if not include_cms and name.startswith('cms_'):
                continue
            digest = hashlib.sha256()
            count = 0
            for row in conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid'):
                digest.update(json.dumps(row, ensure_ascii=False, separators=(',',':')).encode())
                digest.update(b'\n')
                count += 1
            result[name] = {'rows':count, 'sha256':digest.hexdigest()}
        return result


def screen(page, name):
    path = OUT / (name + '.png')
    page.screenshot(path=str(path))
    report['screens'].append(str(path.relative_to(ROOT)))


def type_ratios(page, name, width, selectors, baseline):
    measured = page.evaluate(MEASURE, selectors)
    key = f'{name}@{width}'
    if key not in baseline:
        return
    previous = baseline[key]['fonts']
    for role, current in measured.items():
        old = previous.get(role)
        if not old or not current:
            continue
        old_size = float(old['size'].removesuffix('px'))
        size = float(current['size'].removesuffix('px'))
        ratio = size / old_size
        report['ratios'].append({'page':name,'width':width,'role':role,'before':old_size,'after':size,'ratio':ratio})
        check(f'{key} {role} at least 50 percent larger', ratio >= 1.5 - 0.0001)


report['protected_before'] = fingerprints()
report['notebook_before'] = fingerprints(True)
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
        context = browser.new_context(viewport={'width':1440,'height':1100}, color_scheme='light')
        context.on('request', lambda r: report['external'].append(r.url) if not r.url.startswith(BASE) else None)
        page = context.new_page()
        page.on('pageerror', lambda e: report['errors'].append(str(e)))
        page.on('console', lambda m: report['errors'].append(m.text) if m.type == 'error' else report['warnings'].append(m.text) if m.type == 'warning' else None)
        page.on('dialog', lambda d: d.accept())
        page.goto(BASE + '/')
        labels = page.locator('.card-label').all_text_contents()
        values = page.locator('.card-value').all_text_contents()
        check('real populated homepage has twelve cards', len(values) == 12)
        pages = [('home','/'),('series','/series/ine.hicp_yoy.PT'),
                 ('comparison','/comparar/credito-e-taxa'),('themes','/temas/economy'),
                 ('overview','/dados/admin/'),('cms_list','/dados/admin/cms'),
                 ('cms_editor','/dados/admin/cms/page/inicio'),('series_list','/dados/admin/series'),
                 ('notebook','/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT')]
        for width in (1440,1024,768,390,320):
            page.set_viewport_size({'width':width,'height':1100})
            for name, route in pages:
                response = page.goto(BASE + route)
                check(f'{name} {width} HTTP200', response is not None and response.status == 200)
                page.evaluate('document.fonts.ready')
                check(f'{name} {width} no page overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                check(f'{name} {width} no authored forbidden punctuation', chr(0x2014) not in page.locator('body').inner_text())
                is_admin = route.startswith('/dados/admin')
                type_ratios(page, name, width, BO if is_admin else PUB, ADMIN_BASELINE if is_admin else PUBLIC_BASELINE)
                check(f'{name} {width} Lato loaded', page.evaluate("document.fonts.check('21px Lato')"))
                if name in ('series','comparison'):
                    bounds = page.locator('svg.chart text').evaluate_all("es=>es.map(e=>{const b=e.getBBox();const v=e.ownerSVGElement.viewBox.baseVal;return {text:e.textContent,left:b.x,right:b.x+b.width,width:v.width};})")
                    check(f'{name} {width} actual SVG labels inside viewBox', bool(bounds) and all(b['left']>=-1 and b['right']<=b['width']+1 for b in bounds))
                if name in ('home','notebook'):
                    check(f'{name} {width} scriptfree', page.locator('script').count() == 0)
                if name == 'home':
                    check(f'home {width} exact values', page.locator('.card-value').all_text_contents() == values)
                    check(f'home {width} Schola display', 'Schola' in page.locator('h1').evaluate('e=>getComputedStyle(e).fontFamily'))
                if is_admin and width <= 1024:
                    check(f'{name} {width} compact native menu', page.locator('.bo-menu summary').is_visible())
                    page.locator('.bo-menu summary').click()
                    check(f'{name} {width} accessible current mobile location', page.locator('.nav-mobile a[aria-current="page"]').count() == 1)
                    page.locator('.bo-menu summary').click()
                if not is_admin and width <= 760:
                    page.locator('.nav-disclosure summary').click()
                    check(f'{name} {width} notebook discoverable in mobile menu', page.locator('.nav-disclosure').get_by_role('link',name='Caderno',exact=True).is_visible())
                    page.locator('.nav-disclosure summary').click()
                if width in (1440,390) and name in ('home','cms_editor','comparison','notebook'):
                    screen(page, f'{name}-{width}')
        page.set_viewport_size({'width':1440,'height':1100})
        for name in ('lato-regular.woff2','lato-semibold.woff2','lato-bold.woff2','schola-regular.woff2','schola-bold.woff2'):
            response = context.request.get(BASE + '/static/fonts/prumo/' + name)
            check('advertised font bytes ' + name, response.status == 200 and response.body() == (ROOT/'static/fonts/prumo'/name).read_bytes())
        for prefix in ('','/dados'):
            page.goto(BASE + prefix + '/series/ine.hicp_yoy.PT')
            page.get_by_role('link',name='Criar caderno com esta série',exact=True).click()
            check('series start action ' + prefix, page.locator('.card').count() == 1 and '/caderno?' in page.url)
            form = page.locator('.notebook-search form')
            form.locator('input[name=q]').fill('desemprego')
            form.get_by_role('button',name='Pesquisar',exact=True).click()
            check('search preserves selected card ' + prefix, page.locator('.cards .card').count() == 1)
            page.get_by_role('link',name='Acrescentar ao caderno',exact=True).first.click()
            check('add a second card ' + prefix, page.locator('.cards .card').count() == 2)
            canonical = page.locator('#ligacao-limpa').get_attribute('href')
            assert canonical is not None
            check('canonical strips only transient search ' + prefix, canonical.startswith(prefix+'/caderno?s=') and 'q=' not in canonical)
            page.goto(BASE + canonical)
            selected_labels = page.locator('.card-label').all_text_contents()
            other = context.new_page()
            other.goto(BASE + canonical)
            check('shared address reopens same cards ' + prefix, other.locator('.card-label').all_text_contents() == selected_labels)
            other.close()
            page.locator('.card-remove').first.click()
            check('remove one card ' + prefix, page.locator('.cards .card').count() == 1)
            page.get_by_role('link',name='Limpar seleção',exact=True).click()
            check('clear notebook ' + prefix, page.locator('.cards .card').count() == 0)
            page.goto(BASE + prefix + '/comparar/credito-e-taxa')
            page.get_by_role('link',name='Criar caderno com estas duas séries',exact=True).click()
            check('comparison start action ' + prefix, page.locator('.cards .card').count() == 2)
            check('notebook noindex meta ' + prefix, page.locator('meta[name=robots]').get_attribute('content') == 'noindex, follow')
            response = context.request.get(BASE + prefix + '/caderno?s=ren.electricity_price.PT')
            check('withheld notebook stays safe ' + prefix, response.status == 200 and 'class="card-value' not in response.text())
        check('entire database unchanged by notebook', fingerprints(True) == report['notebook_before'])
        for scheme in ('light','dark'):
            page.emulate_media(color_scheme=scheme)
            page.goto(BASE+'/dados/admin/cms/page/inicio')
            page.locator('input[name=note]').first.focus()
            page.keyboard.press('Tab')
            focus = page.evaluate("({style:getComputedStyle(document.activeElement).outlineStyle,width:parseFloat(getComputedStyle(document.activeElement).outlineWidth),color:getComputedStyle(document.activeElement).outlineColor})")
            check('visible real keyboard outline ' + scheme, focus['style']=='solid' and focus['width']>=3)
            if scheme == 'dark':
                screen(page, 'editor-dark-1440')
        page.emulate_media(color_scheme='light')
        # Exercise unchanged editorial protections on the isolated copy, never on production.
        admin = BASE + '/dados/admin/cms/page/inicio'
        with sqlite3.connect(f'file:{DB}?mode=ro',uri=True) as conn:
            original_revision = conn.execute("SELECT published_revision_id FROM cms_document WHERE kind='page' AND slug='inicio'").fetchone()[0]
        page.goto(admin)
        save = page.locator('form[action$="/save"]')
        save.locator('input[name=block_title_0]').fill('Prova privada de legibilidade')
        page.locator('form[action$="/publish"]').get_by_role('button').click()
        check('dirty publication still blocked', page.locator('.dirty-note').is_visible())
        save.locator('input[name=note]').fill('Prova local de legibilidade')
        save.get_by_role('button',name='Guardar rascunho',exact=True).click()
        check('draft stays private', 'Prova privada de legibilidade' not in context.request.get(BASE+'/').text())
        response = context.request.get(admin+'/preview')
        check('static preview has local fonts but no executable scripts', response.status==200 and 'fonts.css' in response.text() and '<script src=' not in response.text() and "font-src 'self'" in response.headers['content-security-policy'])
        page.goto(admin)
        publish = page.locator('form[action$="/publish"]')
        publish.locator('input[name=note]').fill('Publicar apenas no ensaio isolado')
        publish.get_by_role('button').click()
        check('isolated publication actually served', 'Prova privada de legibilidade' in context.request.get(BASE+'/').text())
        unpublish = page.locator('form[action$="/unpublish"]')
        unpublish.locator('input[name=note]').fill('Retirar publicação de ensaio')
        unpublish.get_by_role('button').click()
        check('isolated unpublication actually removed', 'Prova privada de legibilidade' not in context.request.get(BASE+'/').text())
        restore = page.locator('form[action$="/restore"]').filter(has=page.locator(f'input[name=revision_id][value="{original_revision}"]'))
        restore.locator('input[name=note]').fill('Recuperar rascunho original do ensaio')
        restore.get_by_role('button').click()
        publish = page.locator('form[action$="/publish"]')
        publish.locator('input[name=note]').fill('Repor publicação original no ensaio')
        publish.get_by_role('button').click()
        page.goto(BASE+'/')
        check('original cards after history restore', page.locator('.card-label').all_text_contents()==labels and page.locator('.card-value').all_text_contents()==values)
        # Compiled chart exact selection and print fallback.
        page.goto(BASE+'/comparar/credito-e-taxa')
        page.locator('.chart-enhanced').wait_for()
        payload=json.loads(page.locator('script[type="application/json"]').inner_text())
        control=page.locator('input[type=range]')
        control.focus()
        for key,index in (('Home',0),('End',-1)):
            control.press(key)
            check('exact dual-axis keyboard '+key, all(value in page.locator('.chart-readout').inner_text() for value in payload['display'][index]))
        page.emulate_media(media='print')
        check('print restores named SVG', page.locator('svg.chart').evaluate('e=>getComputedStyle(e).opacity==="1"'))
        page.emulate_media(media='screen',reduced_motion='reduce')
        page.goto(BASE+'/dados/admin/cms')
        check('reduced motion retains static controls', page.locator('.btn').first.evaluate("e=>getComputedStyle(e).transitionDuration.split(',').every(v=>parseFloat(v)===0)"))
        degraded=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1100})
        p=degraded.new_page()
        p.goto(BASE+'/caderno?s=ine.hicp_yoy.PT')
        check('notebook usable without JavaScript',p.locator('.card').count()==1 and p.locator('script').count()==0)
        p.goto(BASE+'/comparar/credito-e-taxa')
        check('no-JS readable scrollable SVG',p.locator('svg.chart').evaluate('e=>e.getBoundingClientRect().width>=600'))
        degraded.route('**/*.woff2',lambda route:route.abort())
        p.goto(BASE+'/dados/admin/cms/page/inicio')
        check('missing-font no-JS editor actions remain named',p.get_by_role('button',name='Guardar rascunho',exact=True).is_visible())
        degraded.close()
        check('no page or CSP errors',not report['errors'])
        check('no external requests',not report['external'])
        browser.close()
    report['protected_after']=fingerprints()
    check('all protected data fingerprints unchanged',report['protected_after']==report['protected_before'])
    with sqlite3.connect(f'file:{DB}?mode=ro',uri=True) as conn:
        report['integrity']=conn.execute('PRAGMA quick_check').fetchone()[0]
        report['foreign_keys']=conn.execute('PRAGMA foreign_key_check').fetchall()
    check('integrity and foreign keys',report['integrity']=='ok' and not report['foreign_keys'])
    report['complete']=True
finally:
    (OUT/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'complete':report.get('complete',False),'checks':len(report['checks']),'type_samples':len(report['ratios']),'minimum_ratio':min(r['ratio'] for r in report['ratios']),'errors':report['errors'],'warnings':report['warnings'],'protected_tables':len(report.get('protected_after',{}))}))
