"""Capture neutral installed UI after clearing transient focus/tooltip states."""
import json
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

OUT = Path(__file__).parent / 'production'
report = {'screens': [], 'transient_tooltip_checks': []}
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
    for base, suffix in (('https://cae.joao.date', 'direct'), ('https://joao.date/dados', 'mounted')):
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1100}, reduced_motion='reduce')
            page = context.new_page()
            page.goto(base + '/')
            page.evaluate('document.fonts.ready')
            page.locator('h1').click()
            page.mouse.move(0, 0)
            page.evaluate('window.scrollTo(0,0)')
            name = f'home-neutral-{suffix}-{width}.png'
            page.screenshot(path=str(OUT / name))
            report['screens'].append(name)
            page.goto(base + '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT')
            page.locator('.chart-enhanced canvas').wait_for()
            page.evaluate('document.fonts.ready')
            page.locator('.chart-canvas').scroll_into_view_if_needed()
            box = page.locator('.chart-canvas').bounding_box()
            assert box is not None
            page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
            expect(page.locator('.chart-tip-line').first).to_be_visible()
            page.mouse.move(0, 0)
            expect(page.locator('.chart-tip-line').first).not_to_be_visible()
            report['transient_tooltip_checks'].append({'base': base, 'width': width, 'hides_on_pointerleave': True})
            name = f'notebook-neutral-{suffix}-{width}.png'
            page.screenshot(path=str(OUT / name))
            report['screens'].append(name)
            context.close()
    browser.close()
(OUT / 'neutral-screens.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'screens': len(report['screens']), 'tooltip_checks': len(report['transient_tooltip_checks'])}))
