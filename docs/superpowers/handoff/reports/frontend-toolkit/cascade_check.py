"""Exercise vendor cascade regressions through real rendered pages."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.app.test_chart_layout import _chromium


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checks = []
    def check(name, value):
        checks.append({'name': name, 'passed': bool(value)})
        assert value, name
    complete = False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=_chromium(),headless=True,args=['--no-sandbox'])
            page = browser.new_page(viewport={'width':390,'height':844})
            page.goto(args.base + '/',wait_until='networkidle')
            page.evaluate('() => document.fonts.ready')
            check('native document scrolling, not animated',page.evaluate('getComputedStyle(document.documentElement).scrollBehavior') == 'auto')
            page.locator('.app-more > summary').click()
            group = page.locator('.app-search > .input-group')
            check('populated stacked search',group.locator('.form-control').count() == 1 and group.locator('.btn').count() == 1)
            corners = group.evaluate("e => [...e.querySelectorAll('.form-control,.btn')].map(c=>{const s=getComputedStyle(c);return [s.borderTopLeftRadius,s.borderTopRightRadius,s.borderBottomRightRadius,s.borderBottomLeftRadius,s.marginLeft]})")
            check('stacked search outer corners', corners[0][:4] == ['7px','7px','0px','0px'] and corners[1][:4] == ['0px','0px','7px','7px'])
            check('stacked search no negative step', corners[1][4] == '0px')
            page.locator('.app-more > summary').click()
            check('populated card link',page.locator('.card .card-link').count() > 0)
            check('card footers align left',all(c.evaluate('(e)=>getComputedStyle(e).justifyContent') == 'flex-start' for c in page.locator('.card .card-link').all()))
            page.goto(args.base + '/temas/economy',wait_until='networkidle')
            trigger = page.locator('.app-more > summary')
            check('more has current section',page.locator('.app-more').get_attribute('data-state') is not None)
            check('current section remains visible',trigger.evaluate('(e)=>getComputedStyle(e).color') == 'rgb(155, 28, 46)')
            controls=page.locator('.page-link')
            check('populated pagination',controls.count() > 0)
            check('pagination targets at least44px',all(c.bounding_box()['height'] >= 44 for c in controls.all()))
            page.emulate_media(media='print')
            check('pagination absent from print',all(not c.is_visible() for c in controls.all()))
            page.emulate_media(media='screen')
            page.goto(args.base + '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT',wait_until='networkidle')
            provenance = page.locator('.notebook-workspace details.provenance-details').last
            provenance.locator('summary').click()
            h4 = page.locator('.provenance-details h4')
            check('populated provenance headings',h4.count() > 0)
            check('evidence headings hierarchy',all(h.evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)') <= 22 and h.evaluate('(e)=>getComputedStyle(e).fontWeight') == '700' for h in h4.all()))
            browser.close()
        complete=True
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'completed':complete,'passed':complete and all(c['passed'] for c in checks),'checks':checks},indent=2))
        print(json.dumps({'completed':complete,'checks':len(checks)}))


if __name__ == '__main__':
    main()
