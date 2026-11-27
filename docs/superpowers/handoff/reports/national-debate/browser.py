"""Browser acceptance for CMS documents, on an isolated server or actual public mounts."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', action='append', required=True)
    parser.add_argument('--chromium', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--screenshots', type=Path, required=True)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text())
    checks = []
    errors = []
    warnings = []
    completed = False
    args.screenshots.mkdir(parents=True, exist_ok=True)

    def check(name, result):
        checks.append({'name':name,'passed':bool(result)})
        assert result, name

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=str(args.chromium))
            for width, height in ((390,844),(1440,1000)):
                context = browser.new_context(viewport={'width':width,'height':height},
                                              is_mobile=width<600, has_touch=width<600)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: warnings.append(message.text)
                        if message.type in ('error','warning') else None)
                for origin in args.origin:
                    for entry in bundle['documents']:
                        kind, slug = entry['kind'], entry['slug']
                        route = ('/comparar/' if kind=='chart' else '/paginas/') + slug
                        response = page.goto(origin.rstrip('/') + route, wait_until='domcontentloaded')
                        page.evaluate('document.fonts.ready')
                        check(f'{width} {origin}{route}: 200', response.status==200)
                        check(f'{width} {slug}: heading', page.locator('h1').count()==1
                              and page.locator('h1').inner_text()==entry['body']['title'])
                        check(f'{width} {slug}: no page overflow', page.evaluate(
                            'document.documentElement.scrollWidth <= innerWidth + 1'))
                        check(f'{width} {slug}: no forbidden punctuation', chr(0x2014) not in page.locator('body').inner_text())
                        expected_charts = 1 if kind=='chart' else sum(block['type']=='chart' for block in entry['body']['blocks'])
                        if expected_charts:
                            page.wait_for_selector('.chart-shell.chart-enhanced', timeout=15000)
                            check(f'{width} {slug}: all charts enhanced', page.locator('.chart-shell.chart-enhanced').count()==expected_charts)
                            for index, shell in enumerate(page.locator('.chart-shell').all()):
                                payload = json.loads(shell.locator('script.chart-data').text_content())
                                control = shell.locator('.chart-range')
                                control.press('End')
                                readout = shell.locator('.chart-readout').inner_text()
                                check(f'{width} {slug}/{index}: exact last period inspection', payload['periods'][-1] in readout)
                                check(f'{width} {slug}/{index}: exact displayed values', all(value in readout for value in payload['display'][-1]))
                                check(f'{width} {slug}/{index}: usable canvas', shell.locator('canvas').first.evaluate('(e)=>e.getBoundingClientRect().width')>250)
                        if origin == args.origin[0] and slug in ('debate-nacional','produtividade-hora-portugal-europa','energia-e-precos','industria-portugal-setores'):
                            page.evaluate('scrollTo(0,0)')
                            page.screenshot(path=str(args.screenshots/f'{slug}-{width}.png'),full_page=False)
                context.close()
            browser.close()
        check('no uncaught application errors', not errors)
        check('no application console errors', all("Permissions-Policy" in warning and 'vr' in warning for warning in warnings))
        completed = True
    finally:
        result = {'completed':completed,'passed':completed and all(c['passed'] for c in checks),
                  'checks':checks,'errors':errors,'warnings':warnings,'origins':args.origin}
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'receipt':str(args.receipt),'completed':completed,'passed':result['passed'],
                          'checks':len(checks),'warnings':len(warnings),'errors':errors}))


if __name__=='__main__':
    main()
