"""Real CMS authoring and published-reader browser acceptance on an isolated production copy."""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
sys.path.insert(0, str(REPO))
from backoffice.cms import Cms  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', default='http://127.0.0.1:8791')
    parser.add_argument('--db', type=Path, required=True)
    args = parser.parse_args()
    output = ROOT / 'browser'
    output.mkdir(exist_ok=True)
    checks = []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        assert condition, name
    cms = Cms(args.db, args.db)
    slug = 'taxas-juro-credito-depositos'
    original = cms.get('chart', slug)
    original_revision = original['meta']['draft_revision_id']
    public_path = f'/comparar/{slug}'
    admin_path = f'/dados/admin/cms/chart/{slug}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
            errors = []
            requests = []
            context = browser.new_context(viewport={'width': 1440, 'height': 1080})
            page = context.new_page()
            page.on('dialog', lambda dialog: dialog.accept())
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: requests.append(request.url))
            for prefix in ('', '/dados'):
                for width in (390, 768, 1440, 1920):
                    page.set_viewport_size({'width': width, 'height': 1080 if width > 768 else 844})
                    response = page.goto(args.origin + prefix + public_path)
                    page.evaluate('document.fonts.ready')
                    page.wait_for_selector('.chart-shell.chart-enhanced canvas')
                    check(f'public-{prefix}-{width}-200', response.status == 200)
                    check(f'public-{prefix}-{width}-no-overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    check(f'public-{prefix}-{width}-no-composition-controls', page.locator('select[name=scale], select[name=escala], input[name=g], .notebook-chart-form').count() == 0)
                    check(f'public-{prefix}-{width}-four-series', len(json.loads(page.locator('.chart-data').inner_text())['series']) == 4)
                    check(f'public-{prefix}-{width}-all-table-cells', page.locator('.notebook-table-scroll tbody tr').first.locator('td').count() == 5)
                    slider = page.locator('.chart-range')
                    slider.focus()
                    slider.press('Home')
                    first = slider.get_attribute('aria-valuetext')
                    slider.press('End')
                    check(f'public-{prefix}-{width}-keyboard', bool(first) and slider.get_attribute('aria-valuetext') != first)
                    page.locator('h1').click()
                    canvas = page.locator('.chart-canvas').bounding_box()
                    page.mouse.move(canvas['x'] + canvas['width'] / 2, canvas['y'] + canvas['height'] / 2)
                    page.mouse.move(0, 0)
                    page.wait_for_timeout(100)
                    page.evaluate('window.scrollTo(0,0)')
                    check(f'public-{prefix}-{width}-capture-at-top', page.evaluate('scrollY') == 0)
                    if prefix == '/dados' and width in (390, 1440):
                        page.screenshot(path=str(output / f'public-{width}.png'), full_page=False)
            page.set_viewport_size({'width': 1440, 'height': 1080})
            response = page.goto(args.origin + admin_path)
            page.evaluate('document.fonts.ready')
            check('admin-editor-200', response.status == 200)
            check('admin-six-series-slots', page.locator('select[name^=series_]').count() == 6)
            check('admin-six-axis-assignments', page.locator('select[name^=axis_]').count() == 6)
            page.screenshot(path=str(output / 'editor-1440.png'), full_page=False)
            page.locator('input[name=title]').fill('Juros, crédito e depósitos: composição revista')
            page.locator('select[name=series_extra_2]').select_option('bportugal.euribor_3m.EA')
            page.locator('select[name=axis_4]').select_option('0')
            page.locator('#draft-note').fill('Provar edição de um comparativo real no backoffice')
            page.get_by_role('button', name='Guardar rascunho', exact=False).click()
            page.wait_for_url('**/cms/chart/' + slug)
            check('saved-draft-has-five-series', len(cms.get('chart', slug)['draft'].series_ids) == 5)
            public = context.new_page()
            public.goto(args.origin + public_path)
            check('draft-is-private', len(json.loads(public.locator('.chart-data').inner_text())['series']) == 4)
            preview = context.new_page()
            preview_response = preview.goto(args.origin + admin_path + '/preview')
            check('private-preview-200', preview_response.status == 200)
            check('private-preview-static', preview.locator('script[src]').count() == 0 and preview.locator('svg.chart').count() >= 1)
            check('preview-title', 'composição revista' in preview.locator('h1').inner_text())
            page.locator('#publish-note').fill('Publicar composição revista a partir do editor')
            with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/publish')) as published_response:
                page.get_by_role('button', name='Publicar este rascunho', exact=False).click()
            check('publish-post-303', published_response.value.status == 303)
            page.wait_for_url('**/cms/chart/' + slug)
            public.reload()
            check('published-five-series', len(json.loads(public.locator('.chart-data').inner_text())['series']) == 5)
            check('published-editorial-title', 'composição revista' in public.locator('h1').inner_text())
            check('public-remains-read-only', public.locator('select[name^=series_], select[name^=axis_]').count() == 0)
            for width in (390, 768):
                page.set_viewport_size({'width': width, 'height': 844})
                page.goto(args.origin + admin_path)
                page.evaluate('document.fonts.ready')
                check(f'admin-{width}-no-overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            check('no-application-errors', not errors)
            check('no-external-requests', all(url.startswith(args.origin) or url.startswith('data:') for url in requests))
            nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
            plain = nojs.new_page()
            plain.goto(args.origin + '/dados' + public_path)
            check('nojs-complete-svg', plain.locator('svg.chart').count() >= 1)
            plain.goto(args.origin + admin_path)
            check('nojs-six-series', plain.locator('select[name^=series_]').count() == 6)
            touch_context = browser.new_context(has_touch=True, is_mobile=True, viewport={'width': 390, 'height': 844})
            touch = touch_context.new_page()
            touch.goto(args.origin + '/dados' + public_path)
            touch.wait_for_selector('.chart-shell.chart-enhanced canvas')
            drawing = touch.locator('.chart-canvas').bounding_box()
            assert drawing is not None
            touch.touchscreen.tap(drawing['x'] + drawing['width'] / 2, drawing['y'] + drawing['height'] / 2)
            data = json.loads(touch.locator('.chart-data').inner_text())
            selected = int(touch.locator('.chart-range').input_value())
            readout = touch.locator('.chart-readout').inner_text()
            check('touch-exact-period', data['periods'][selected] in readout)
            check('touch-exact-each-value', all(token in readout for token in data['display'][selected]))
            touch.emulate_media(media='print')
            check('print-restores-svg', touch.locator('svg.chart').first.evaluate('(el)=>getComputedStyle(el).opacity') == '1')
            check('print-hides-canvas', touch.locator('.chart-canvas').evaluate('(el)=>getComputedStyle(el).display') == 'none')
            blocked_context = browser.new_context(viewport={'width': 390, 'height': 844})
            blocked_context.route('**/static/js/prumo-charts*', lambda route: route.abort())
            blocked = blocked_context.new_page()
            blocked.goto(args.origin + '/dados' + public_path)
            check('blocked-bundle-keeps-svg', blocked.locator('svg.chart').first.evaluate('(el)=>getComputedStyle(el).opacity') == '1')
            browser.close()
    finally:
        current = cms.get('chart', slug)
        if current['draft'].title != original['draft'].title:
            restored = cms.restore('chart', slug, current['meta']['version'], original_revision,
                                   actor='browser-acceptance', note='Restaurar composição real após ensaio isolado')
            cms.publish('chart', slug, restored['version'], actor='browser-acceptance', note='Repor publicação original na cópia')
        (output / 'result.json').write_text(json.dumps({'checks': checks}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': len(checks), 'receipt': str(output / 'result.json')}))


if __name__ == '__main__':
    main()
