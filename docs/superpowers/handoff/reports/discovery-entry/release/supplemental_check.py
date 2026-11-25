"""Read-only geometry adjudication and installed exports for phase C."""
import argparse
import csv
import io
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checks, geometry, exports = [], [], []
    complete = False

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        assert condition, name

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 390, 'height': 844})
            page = context.new_page()
            response = page.goto('https://joao.date/dados/pesquisa?q=desemprego+Portugal')
            check('mobile search HTTP200', response is not None and response.status == 200)
            page.evaluate('document.fonts.ready')
            for selector in ('main', '.discovery-summary a', '#pesquisa-q', '.discovery-query button'):
                box = page.locator(selector).bounding_box()
                assert box is not None, selector
                geometry.append({'selector': selector, **box})
                if selector == 'main':
                    padding = page.locator(selector).evaluate('e=>({left:parseFloat(getComputedStyle(e).paddingLeft),right:parseFloat(getComputedStyle(e).paddingRight)})')
                    check('main content respects 18px page gutters', box['x'] + padding['left'] >= 17.9 and box['x'] + box['width'] - padding['right'] <= 372.1)
                else:
                    check(selector + ' respects 18px page gutters', box['x'] >= 17.9 and box['x'] + box['width'] <= 372.1)
            query = page.locator('#pesquisa-q')
            check('full query value preserved', query.input_value() == 'desemprego Portugal')
            query.focus()
            query.press('End')
            check('native query input scrolls to its end', query.evaluate('e=>e.scrollLeft + e.clientWidth >= e.scrollWidth - 1'))
            query.press('Home')
            check('native query input scrolls to its start', query.evaluate('e=>e.scrollLeft') == 0)
            boxes = {r['selector']: r for r in geometry}
            check('query and button heights aligned', abs(boxes['#pesquisa-q']['height'] - boxes['.discovery-query button']['height']) < 1)
            for base in ('https://cae.joao.date', 'https://joao.date/dados'):
                for path in ('/series/ine.hicp_yoy.PT.csv', '/calculadas/derived.credit_housing.PT.yoy_change_pct.csv'):
                    result = context.request.get(base + path)
                    check(base + path + ' HTTP200', result.status == 200)
                    check(base + path + ' CSV type', result.headers.get('content-type', '').startswith('text/csv'))
                    rows = list(csv.reader(io.StringIO(result.body().decode('utf-8-sig')), delimiter=';'))
                    check(base + path + ' populated CSV', len(rows) > 1 and len(rows[0]) > 2)
                    exports.append({'url': base + path, 'rows_including_header': len(rows), 'columns': len(rows[0])})
            browser.close()
        complete = True
    finally:
        args.output.write_text(json.dumps({'completed': complete, 'passed': complete and all(r['passed'] for r in checks), 'checks': checks, 'geometry': geometry, 'exports': exports}, ensure_ascii=False, indent=2))
    print(json.dumps({'passed': complete, 'checks': len(checks), 'geometry': geometry, 'exports': exports}))


if __name__ == '__main__':
    main()
