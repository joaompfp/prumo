"""Native batch-selection acceptance on a production copy or the two public mounts."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from playwright.sync_api import expect, sync_playwright

CHROME = '/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'
ENERGY = ['eurostat.electricity_price_household.' + c for c in ('DE', 'ES', 'PT')]
HICP = 'ine.hicp_yoy.PT'
UNEMP = 'ine.unemployment_monthly.PT'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--db', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    before = hashlib.sha256(args.db.read_bytes()).hexdigest() if args.db else None
    checks, errors, warnings = [], [], []
    complete = False

    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
        assert passed, name

    def refs(page):
        return parse_qs(urlsplit(page.url).query).get('s', [])

    def box(page, value):
        return page.locator('input[type=checkbox][name=s][value="' + value + '"]')

    def open_selection(page):
        page.get_by_role('button', name='Abrir caderno', exact=True).first.click()
        page.wait_for_url('**/caderno?*')

    def ready(page):
        page.evaluate('document.fonts.ready')
        page.evaluate('window.scrollTo(0,0)')

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
            for base in args.base:
                origin = urlsplit(base).netloc
                for width in (320, 390, 768, 1440):
                    for mode in ('js', 'no-js', 'blocked'):
                        context = browser.new_context(viewport={'width': width, 'height': 844 if width < 768 else 1000}, java_script_enabled=mode != 'no-js')
                        if mode == 'blocked':
                            context.route('**/static/js/selection.js', lambda route: route.abort())
                        page = context.new_page()
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        def console(message):
                            if message.type == 'error' and mode != 'blocked':
                                errors.append(message.text)
                            if message.type == 'warning':
                                warnings.append(message.text)
                        page.on('console', console)
                        label = f'{base}/{width}/{mode}'
                        response = page.goto(base + '/pesquisa?q=eletricidade')
                        check(label + ' catalogue 200', response is not None and response.status == 200)
                        ready(page)
                        check(label + ' one native form', page.locator('form').count() == 1)
                        check(label + ' no competing one-series action', page.locator('.series-result-action').count() == 0)
                        check(label + ' body preserves approved type', page.locator('body').evaluate('el => parseFloat(getComputedStyle(el).fontSize)') >= 28)
                        check(label + ' no page overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                        if width == 390 and mode == 'js':
                            value = page.locator('.series-result-value').first.bounding_box()
                            check(label + ' first real value in initial view', value is not None and value['y'] + value['height'] <= 844)
                        for sid in ENERGY:
                            box(page, sid).check()
                        if mode == 'js':
                            expect(page.locator('[data-selection-count-number]')).to_have_text('3')
                            check(label + ' all three selected styles', page.locator('.series-result.is-selected').count() == 3)
                            page.locator('.series-result').nth(15).scroll_into_view_if_needed()
                            action = page.locator('.discovery-selection button[name=acao]').bounding_box()
                            check(label + ' batch action stays reachable while scrolling', action is not None and page.viewport_size is not None and action['y'] >= 0 and action['y'] + action['height'] <= page.viewport_size['height'])
                        open_selection(page)
                        check(label + ' ordered three-series handoff', refs(page) == ENERGY)
                        check(label + ' all three cards', page.locator('.notebook-selection .cards > *').count() == 3)

                        # Changes that have not yet been submitted must travel with a new query.
                        page.goto(base + '/caderno?' + urlencode([('s', HICP), ('q', 'desemprego')]))
                        form = page.locator('#notebook-search-form')
                        check(label + ' one native query/selection form', form.count() == 1 and form.locator('[name=q]').count() == 1)
                        available = form.locator('input[type=checkbox][name=s]').evaluate_all('els => els.map(el => el.value)')
                        added = [sid for sid in available if sid != HICP][:2]
                        check(label + ' populated quick batch', len(added) == 2)
                        for sid in added:
                            box(page, sid).check()
                        if mode == 'js':
                            expect(form.locator('[data-selection-count-text]')).to_have_text('3 selecionadas')
                            before_url = page.url
                            page.locator('#notebook-chart-form').evaluate('el => el.requestSubmit()')
                            check(label + ' unrelated submit cannot discard pending selection', page.url == before_url)
                            expect(form.locator('[data-selection-pending]')).to_be_visible()
                        form.locator('[name=q]').fill('PIB')
                        form.get_by_role('button', name='Pesquisar', exact=True).click()
                        page.wait_for_url('**/caderno?*')
                        check(label + ' new search retains unsent batch in order', refs(page) == [HICP, *added])
                        form = page.locator('#notebook-search-form')
                        extra = form.locator('input[type=checkbox][name=s]:not(:checked)').first
                        fourth = extra.get_attribute('value')
                        extra.check()
                        form.get_by_role('button', name='Acrescentar selecionadas', exact=True).click()
                        page.wait_for_url('**/caderno?*')
                        check(label + ' batch applies all new plus existing refs', refs(page) == [HICP, *added, fourth])

                        page.goto(base + '/caderno?' + urlencode([('s', HICP), ('s', UNEMP), ('q', 'IHPC')]))
                        box(page, HICP).uncheck()
                        form = page.locator('#notebook-search-form')
                        form.locator('[name=q]').fill('PIB')
                        form.get_by_role('button', name='Pesquisar', exact=True).click()
                        page.wait_for_url('**/caderno?*')
                        check(label + ' new search does not restore unchecked member', refs(page) == [UNEMP])

                        # A previous explicit plot/window/transform choice survives the handoff.
                        configured = [('s', HICP), ('s', UNEMP), ('grafico', 'on'), ('g', HICP), ('g', UNEMP), ('janela', '5a'), ('frequencia_grafico', 'anual'), ('transformacao', 'pp'), ('base', '2020')]
                        page.goto(base + '/pesquisa?' + urlencode(configured + [('q', 'eletricidade')]))
                        box(page, ENERGY[0]).check()
                        open_selection(page)
                        qs = parse_qs(urlsplit(page.url).query)
                        check(label + ' settings and group preserved', qs.get('g') == [HICP, UNEMP] and qs.get('janela') == ['5a'] and qs.get('frequencia') == ['anual'] and qs.get('transformacao') == ['pp'])

                        page.goto(base + '/pesquisa?q=eletricidade')
                        box(page, ENERGY[0]).check()
                        page.get_by_role('button', name='Página seguinte', exact=True).click()
                        second = page.locator('input[type=checkbox][name=s]').first.get_attribute('value')
                        box(page, second).check()
                        page.get_by_role('button', name='Página anterior', exact=True).click()
                        check(label + ' native pager keeps order', refs(page) == [ENERGY[0], second])
                        box(page, ENERGY[0]).uncheck()
                        open_selection(page)
                        check(label + ' pager uncheck removes just chosen member', refs(page) == [second])

                        if mode == 'js':
                            page.goto(base + '/pesquisa?q=eletricidade')
                            for item in page.locator('input[type=checkbox][name=s]').all()[:12]:
                                item.check()
                            check(label + ' twelve selected not silently truncated', page.locator('input[type=checkbox][name=s]:checked').count() == 12)
                            check(label + ' extra choices disabled at visible bound', page.locator('input[type=checkbox][name=s]:not(:checked):enabled').count() == 0)
                            page.locator('input[type=checkbox][name=s]:checked').first.uncheck()
                            check(label + ' removing restores room', page.locator('input[type=checkbox][name=s]:not(:checked):enabled').count() > 0)
                        else:
                            page.goto(base + '/pesquisa?q=eletricidade')
                            for item in page.locator('input[type=checkbox][name=s]').all()[:13]:
                                item.check()
                            page.get_by_role('button', name='Abrir caderno', exact=True).first.click()
                            check(label + ' no-script overlimit recovers in catalogue', '/pesquisa?' in page.url and len(refs(page)) == 13)
                            expect(page.locator('.selection-warning')).to_be_visible()
                        context.close()

                # Exact loaded local asset and a genuine populated chart remain available.
                context = browser.new_context(viewport={'width': 390, 'height': 844})
                page = context.new_page()
                page.goto(base + '/pesquisa?q=eletricidade')
                ready(page)
                page.screenshot(path=str(args.output / f'{origin}-catalogue-390.png'))
                for asset in ('static/js/selection.js', 'static/css/discovery.css', 'static/css/prumo.css'):
                    r = context.request.get(base + '/' + asset)
                    check(base + ' installed asset ' + asset, r.status == 200 and r.body() == (args.root / asset).read_bytes())
                page.goto(base + '/caderno?' + urlencode([('s', sid) for sid in ENERGY]))
                expect(page.locator('canvas').first).to_be_visible()
                check(base + ' genuine three-series drawable payload', page.locator('.notebook-chart').get_attribute('data-chart-state') == 'ready')
                context.close()
            browser.close()
        complete = True
    finally:
        unchanged = before == hashlib.sha256(args.db.read_bytes()).hexdigest() if args.db else None
        result = {'completed': complete, 'passed': complete and not errors and unchanged is not False, 'checks': checks, 'errors': errors, 'warnings': warnings, 'database_unchanged': unchanged}
        (args.output / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    assert result['passed'], result
    print(json.dumps({'passed': True, 'checks': len(checks), 'warnings': len(warnings), 'database_unchanged': unchanged}))


if __name__ == '__main__':
    main()
