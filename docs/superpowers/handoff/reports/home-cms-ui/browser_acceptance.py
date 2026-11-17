"""Real browser acceptance against a writable isolated production copy only."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path('/home/joao/projects/prumo-pipeline')
OUT = ROOT / 'docs/superpowers/handoff/reports/home-cms-ui/browser'
OUT.mkdir(parents=True, exist_ok=True)
DB = Path('/home/joao/.hermes/cache/scratch/prumo-home-qa/acceptance3.sqlite3')
BASE = 'http://127.0.0.1:8107'
ADMIN = BASE + '/dados/admin'


def fingerprint():
    result = {}
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'cms_%' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for table in tables:
            h, count = hashlib.sha256(), 0
            for row in db.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                h.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode())
                h.update(b'\n')
                count += 1
            result[table] = {'rows': count, 'sha256': h.hexdigest()}
    return result


report = {'protected_before': fingerprint(), 'checks': [], 'errors': [], 'external': []}


def check(name, condition):
    report['checks'].append({'check': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, color_scheme='light')
    context.on('request', lambda r: report['external'].append(r.url) if not r.url.startswith(BASE) else None)
    page = context.new_page()
    page.on('pageerror', lambda e: report['errors'].append(str(e)))
    page.on('console', lambda m: report['errors'].append(m.text) if m.type == 'error' else None)
    page.on('dialog', lambda d: d.accept())
    initial = page.goto(BASE + '/')
    initial_html = initial.text()
    initial_labels = page.locator('.card-label').all_text_contents()
    initial_values = page.locator('.card-value').all_text_contents()
    check('baseline public home', initial.status == 200 and len(initial_labels) == 12)
    page.goto(ADMIN + '/cms')
    page.screenshot(path=str(OUT / 'dashboard-1440.png'))
    page.goto(ADMIN + '/cms/home')
    page.get_by_role('button', name='Preparar rascunho da página inicial').click()
    page.wait_for_url('**/cms/page/inicio')
    check('complete home content created by real form', page.locator('input[name="block_count"]').input_value() == '17')
    check('live source facts not stored in prose', page.locator('input[name="block_counts_0"]').is_checked())
    check('local icon font loaded', page.evaluate("document.fonts.ready.then(() => document.fonts.check('16px PrumoIcons'))"))
    check('irrelevant fields disclosed by type', not page.locator('#block-text-0').is_visible() and page.locator('#block-title-0').is_visible())
    page.screenshot(path=str(OUT / 'home-editor-1440.png'))
    response = context.request.get(BASE + '/')
    check('private preparation did not change public bytes', response.text() == initial_html)
    page.goto(ADMIN + '/cms/page/inicio/preview')
    check('static full-home preview', page.get_by_text('A cadeia de verificação', exact=True).count() == 1 and page.locator('.card').count() == 12 and page.locator('script[src]').count() == 0)
    page.screenshot(path=str(OUT / 'home-preview-1440.png'))
    page.goto(ADMIN + '/cms/page/inicio')
    publish = page.locator('form[action$="/publish"]')
    publish.locator('input[name="note"]').fill('Aceitação local: publicar a homepage completa existente')
    publish.get_by_role('button').click()
    page.wait_for_load_state('load')
    page.goto(BASE + '/')
    check('published CMS home preserves current figures', page.locator('.card-label').all_text_contents() == initial_labels and page.locator('.card-value').all_text_contents() == initial_values)
    for text in ['Todo o catálogo, por assunto.', 'A cadeia de verificação', 'Instituições publicadas', 'Explorar os dados', 'Como verificamos']:
        check('preserved home section ' + text, page.get_by_text(text, exact=True).count() == 1)
    check('grouped current cards', page.locator('.cards').count() == 1)
    check('summary script-free', page.locator('script').count() == 0)
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 1000})
        for route, name in [('/', 'home'), ('/dados/', 'home-mounted'), ('/dados/admin/cms', 'dashboard'), ('/dados/admin/cms/page/inicio', 'editor')]:
            response = page.goto(BASE + route)
            check(f'{name} {width} HTTP200', response.status == 200)
            check(f'{name} {width} no page overflow', page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
            if name == 'dashboard' and width < 600:
                check(f'mobile table {width} cells stay within viewport', page.locator('.cms-table td').evaluate_all('(cells) => cells.every(cell => cell.getBoundingClientRect().right <= innerWidth)'))
                check(f'mobile nav {width} fully visible', page.locator('.nav-link').evaluate_all('(links) => links.every(link => link.getBoundingClientRect().right <= innerWidth)'))
            if name.startswith('home'):
                check(f'{name} {width} single main heading', page.locator('h1').count() == 1)
            page.screenshot(path=str(OUT / f'{name}-{width}.png'))
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto(ADMIN + '/cms/page/inicio')
    form = page.locator('form[action$="/save"]')
    form.locator('input[name="block_title_0"]').fill('Abertura de teste privado')
    stored = context.request.get(BASE + '/').text()
    submissions = []
    page.on('request', lambda request: submissions.append(request.url) if request.method == 'POST' else None)
    page.locator('form[action$="/publish"]').get_by_role('button').click()
    check('dirty publication refused before POST', not submissions and page.locator('.dirty-note').inner_text().startswith('Alterações por guardar:'))
    check('dirty publication kept text and stored content', page.locator('input[name="block_title_0"]').input_value() == 'Abertura de teste privado' and context.request.get(BASE + '/').text() == stored)
    form.locator('input[name="note"]').fill('Guardar um título de teste sem publicar')
    form.get_by_role('button', name='Guardar rascunho', exact=True).click()
    page.wait_for_load_state('load')
    check('draft edit preserved', page.locator('input[name="block_title_0"]').input_value() == 'Abertura de teste privado')
    public_html = context.request.get(BASE + '/').text()
    check('draft edit remains private', 'Abertura de teste privado' not in public_html)
    check('legacy editor locked', context.request.post(ADMIN + '/editorial/inicio/publish', form={'version': '0', 'note': 'teste'}, headers={'Origin': BASE}).status == 409)
    page.emulate_media(reduced_motion='reduce')
    check('reduced motion enabled', page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
    page.goto(ADMIN + '/cms')
    page.locator('body').press('Tab')
    check('keyboard focus visible', page.evaluate("getComputedStyle(document.activeElement).outlineStyle !== 'none'"))
    check('no external requests', not report['external'])
    check('no page or CSP errors', not report['errors'])
    # No-JavaScript save exercises the same server forms, including hidden irrelevant fields.
    nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 1000})
    p = nojs.new_page()
    p.goto(ADMIN + '/cms/page/inicio')
    check('without JS all type fields available', p.locator('#block-text-0').is_visible())
    form = p.locator('form[action$="/save"]')
    form.locator('input[name="block_title_0"]').fill('Estatísticas oficiais, com a proveniência à vista.')
    form.locator('input[name="note"]').fill('Reposição pelo formulário sem JavaScript')
    form.get_by_role('button', name='Guardar rascunho', exact=True).click()
    p.wait_for_load_state('load')
    check('no-JS save accepted', p.locator('input[name="block_title_0"]').input_value() == 'Estatísticas oficiais, com a proveniência à vista.')
    p.screenshot(path=str(OUT / 'editor-nojs-390.png'))
    browser.close()

report['protected_after'] = fingerprint()
check('all non-CMS table fingerprints unchanged', report['protected_before'] == report['protected_after'])
with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as db:
    report['integrity'] = db.execute('PRAGMA integrity_check').fetchone()[0]
    report['foreign_keys'] = db.execute('PRAGMA foreign_key_check').fetchall()
    report['home'] = db.execute("SELECT version,draft_revision_id,published_revision_id FROM cms_document WHERE kind='page' AND slug='inicio'").fetchone()
    report['audit'] = db.execute("SELECT action,version,actor,note FROM cms_event WHERE slug='inicio' ORDER BY id").fetchall()
check('integrity and foreign keys', report['integrity'] == 'ok' and not report['foreign_keys'])
(OUT / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({'checks': len(report['checks']), 'passed': all(c['passed'] for c in report['checks']), 'errors': report['errors'], 'home': report['home'], 'tables': len(report['protected_before'])}, ensure_ascii=False))
