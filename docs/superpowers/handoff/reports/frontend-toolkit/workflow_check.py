"""Native journeys, print evidence and focus checks for the app-style reader shell."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

from tests.app.test_chart_layout import _chromium


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--database', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checks = []
    before = hashlib.sha256(args.database.read_bytes()).hexdigest() if args.database else None

    def check(name, value):
        checks.append({'name': name, 'passed': bool(value)})
        assert value, name

    complete = False
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=_chromium(), headless=True, args=['--no-sandbox'])
            for js in (False, True):
                ctx = browser.new_context(viewport={'width': 390, 'height': 844}, java_script_enabled=js)
                page = ctx.new_page()
                page.goto(args.base + '/pesquisa?q=eletricidade', wait_until='networkidle')
                selected = page.locator('input[type=checkbox][name=s]').all()[:3]
                check('populated native selection', len(selected) == 3)
                ids = [item.input_value() for item in selected]
                for item in selected:
                    item.check()
                page.get_by_role('button', name='Abrir caderno', exact=True).click()
                check('native batch keeps all chosen references', parse_qs(urlparse(page.url).query)['s'] == ids)
                check('three real notebook cards', page.locator('.notebook-selection .card').count() == 3)
                page.get_by_role('link', name='Configurar:', exact=False).click()
                check('native fragment opens settings without script', page.locator('.notebook-chart-settings').get_attribute('open') is not None)
                page.locator('select[name=janela]').select_option('5a')
                page.get_by_role('button', name='Atualizar gráfico', exact=True).click()
                query = parse_qs(urlparse(page.url).query)
                check('native settings preserve chosen references', query['s'] == ids)
                check('native settings preserve selected window', query['janela'] == ['5a'])
                if not js:
                    expect(page.locator('svg.chart[role=img]')).to_be_visible()
                    check('no-JS fallback has no readout gap', not page.locator('.chart-controls').is_visible())
                page.goto(args.base + '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT', wait_until='networkidle')
                if js:
                    page.locator('.brand').focus()
                    page.keyboard.press('Tab')
                    check('keyboard enters first visible task', page.locator('.app-nav-link').first.evaluate('(e) => document.activeElement === e'))
                    style = page.locator('.app-nav-link').first.evaluate('(e) => {const s=getComputedStyle(e);return {width:s.outlineWidth,style:s.outlineStyle,color:s.outlineColor}}')
                    check('immediate visible keyboard focus', style == {'width': '3px', 'style': 'solid', 'color': 'rgb(155, 28, 46)'})
                    page.locator('.app-more > summary').focus()
                    page.keyboard.press('Enter')
                    check('keyboard opens secondary navigation', page.locator('.app-more').get_attribute('open') is not None)
                    page.keyboard.press('Enter')
                    point = page.locator('.chart-range')
                    point.focus()
                    original = point.input_value()
                    page.keyboard.press('Enter')
                    check('point Enter does not submit settings or reset position', point.input_value() == original)
                check('method initially closed', page.locator('.notebook-method').get_attribute('open') is None)
                page.emulate_media(media='print')
                check('print preserves method caveat inside closed details', page.locator('.notebook-caveat').bounding_box() is not None)
                check('print restores server SVG', page.locator('svg.chart[role=img]').is_visible())
                check('print hides app controls', not page.locator('.site-header').is_visible() and not page.locator('.settings-actions').is_visible())
                check('print preserves source metadata', page.locator('.notebook-chart-sources').is_visible())
                ctx.close()
            browser.close()
        if args.database:
            check('entire isolated database unchanged', hashlib.sha256(args.database.read_bytes()).hexdigest() == before)
        complete = True
    finally:
        args.output.write_text(json.dumps({'completed': complete, 'passed': complete and all(c['passed'] for c in checks), 'checks': checks}, indent=2))
        print(json.dumps({'completed': complete, 'checks': len(checks)}))


if __name__ == '__main__':
    main()
