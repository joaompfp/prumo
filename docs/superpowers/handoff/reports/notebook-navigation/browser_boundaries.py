"""Boundaries beyond the standard browser matrix: one, six and seven notebook series."""
import json
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import expect, sync_playwright

OUT = Path(__file__).parent / 'browser-final'
GROUP = [f'bportugal.{name}.{geo}' for name, geo in (
    ('euribor_1m', 'EA'), ('euribor_3m', 'EA'), ('euribor_6m', 'EA'),
    ('euribor_12m', 'EA'), ('pt_10y', 'PT'), ('de_10y', 'DE'))]
report: dict = {'checks': [], 'errors': []}


def check(name, condition):
    assert condition, name
    report['checks'].append(name)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
    for width in (320, 390, 1024, 1440):
        context = browser.new_context(viewport={'width': width, 'height': 1100})
        page = context.new_page()
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        for prefix in ('', '/dados'):
            for sides in (GROUP[:1], GROUP):
                address = 'http://127.0.0.1:8107' + prefix + '/caderno?' + urlencode([('s', side) for side in sides] + [('janela', 'max')])
                response = page.goto(address)
                assert response is not None
                check('http ' + address + str(width), response.status == 200)
                page.evaluate('document.fonts.ready')
                page.wait_for_selector('.chart-enhanced canvas')
                data = json.loads(page.locator('script.chart-data').inner_text())
                check('side count ' + str(width) + prefix + str(len(sides)), len(data['series']) == len(sides))
                check('all table rows ' + str(width) + prefix + str(len(sides)), page.locator('.table-details tbody tr').count() == len(data['x']))
                page.locator('.chart-range').focus()
                page.locator('.chart-range').press('Home')
                expected = (data['periods'][0] + ': ' + data['display'][0][0] if len(sides) == 1 else
                            data['periods'][0] + ' - ' + '; '.join(f'{side["title"]}: {data["display"][0][i]}' for i, side in enumerate(data['series'])))
                expect(page.locator('.chart-readout')).to_have_text(expected)
                check('all exact readouts ' + str(width) + prefix + str(len(sides)), True)
                page.locator('.table-details > summary').click()
                check('open max table contained ' + str(width) + prefix + str(len(sides)), page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                scroller = page.locator('.notebook-table-scroll')
                scroller.focus()
                check('table focus ' + str(width) + prefix + str(len(sides)), scroller.evaluate('e=>e===document.activeElement'))
                check('last column exists ' + str(width) + prefix + str(len(sides)), page.locator('.table-details thead th').count() == len(sides)+1)
            response = page.goto('http://127.0.0.1:8107' + prefix + '/caderno?' + urlencode([('s', side) for side in [*GROUP, 'ine.hicp_yoy.PT']]))
            assert response is not None
            check('seven cards kept ' + str(width) + prefix, page.locator('article.card').count() == 7)
            check('seven requires choice ' + str(width) + prefix, page.locator('script.chart-data').count() == 0 and page.locator('#notebook-chart-form input[name="g"]').count() == 7)
            check('seven no implicit first six ' + str(width) + prefix, page.locator('#notebook-chart-form input[name="g"]:checked').count() == 0)
        context.close()
    check('no page errors', not report['errors'])
    browser.close()
(OUT / 'boundaries.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({'checks': len(report['checks']), 'errors': report['errors']}))
