"""Read actual accessibility tree and capture neutral public UI states on localhost."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / 'browser-final'
URL = 'http://127.0.0.1:8107'
report: dict = {'ax': [], 'focus': [], 'screens': []}
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args=['--no-sandbox'])
    for width in (1440, 390):
        context = browser.new_context(viewport={'width': width, 'height': 1100}, reduced_motion='reduce')
        page = context.new_page()
        page.goto(URL + '/')
        page.evaluate('document.fonts.ready')
        page.mouse.move(0, 0)
        name = f'home-neutral-{width}.png'
        page.screenshot(path=str(OUT / name))
        report['screens'].append(name)
        for _ in range(8):
            page.keyboard.press('Tab')
            info = page.evaluate('''() => {const e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,text:e.textContent.trim().slice(0,90),font:s.fontSize,outline:s.outlineColor,width:s.outlineWidth,style:s.outlineStyle}}''')
            assert info['style'] != 'none' and float(info['width'].replace('px', '')) >= 2, info
            report['focus'].append({'viewport': width, **info})
        page.goto(URL + '/dados/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT')
        page.evaluate('document.fonts.ready')
        page.wait_for_selector('.chart-enhanced canvas')
        session = context.new_cdp_session(page)
        tree = session.send('Accessibility.getFullAXTree')['nodes']
        images = [node for node in tree if not node.get('ignored') and node.get('role', {}).get('value') == 'image']
        sliders = [node for node in tree if not node.get('ignored') and node.get('role', {}).get('value') == 'slider']
        assert len(images) == 1 and 'Evolução conjunta' in images[0].get('name', {}).get('value', ''), images
        assert len(sliders) == 1 and sliders[0].get('name', {}).get('value'), sliders
        report['ax'].append({'viewport': width, 'images': [(node.get('name'), node.get('role')) for node in images], 'sliders': [(node.get('name'), node.get('role')) for node in sliders]})
        page.locator('.chart-canvas').scroll_into_view_if_needed()
        box = page.locator('.chart-canvas').bounding_box()
        assert box is not None
        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
        page.mouse.move(0, 0)
        name = f'notebook-neutral-{width}.png'
        page.screenshot(path=str(OUT / name))
        report['screens'].append(name)
        context.close()
    browser.close()
(OUT / 'accessibility-focus.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({'ax_screens': len(report['ax']), 'focused_targets':len(report['focus']), 'screens':report['screens']}, ensure_ascii=False))
