"""Isolated ECharts feasibility probe. Synthetic values, no Prumo runtime modifications."""
import functools
import gzip
import hashlib
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
CSP = "default-src 'none'; script-src 'self'; script-src-attr 'none'; style-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def log_message(self, *args):
        pass


def size(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'gzip_bytes': len(gzip.compress(raw, compresslevel=9, mtime=0)), 'sha256': hashlib.sha256(raw).hexdigest()}


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=ROOT))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f'http://127.0.0.1:{server.server_port}/proof.html'
report = {'scope': 'Synthetic isolated proof; not an installed Prumo feature', 'csp': CSP,
          'engine': size(ROOT / 'engine.min.js'), 'full': size(ROOT / 'node_modules/echarts/dist/echarts.min.js'), 'views': []}
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', headless=True, args=['--no-sandbox'])
        for width, touch in [(1440, False), (390, True)]:
            context = browser.new_context(viewport={'width': width, 'height': 900}, has_touch=touch, is_mobile=touch)
            page = context.new_page()
            errors, requests = [], []
            page.on('console', lambda msg: errors.append(msg.text) if msg.type in ('error', 'warning') else None)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: requests.append(request.url))
            page.goto(url, wait_until='networkidle')
            page.wait_for_function('() => window.proofReady === true')
            pixel = page.evaluate('window.proofChart.convertToPixel({seriesIndex:0}, [1,4.1])' if touch else 'window.proofChart.convertToPixel({seriesIndex:0}, [0,3.9])')
            box = page.locator('#chart').bounding_box()
            if touch:
                page.touchscreen.tap(box['x'] + pixel[0], box['y'] + pixel[1])
            else:
                page.mouse.move(box['x'] + pixel[0], box['y'] + pixel[1])
            print('pointer', width, touch, pixel, box, flush=True)
            try:
                page.wait_for_function('() => !!window.proofTooltip', timeout=3000)
            except Exception:
                print('pointer failed', width, 'errors', errors, 'violations', page.evaluate('window.proofViolations'), 'state', page.evaluate('({ready:window.proofReady,tooltip:window.proofTooltip})'), flush=True)
                page.screenshot(path=str(ROOT / f'failed-{width}.png'), full_page=True)
                raise
            tooltip = page.evaluate('window.proofTooltip')
            assert ('4,10 %' in tooltip and '1 256 789,00 milhões de euros' in tooltip) if touch else ('3,90 %' in tooltip and '1 234 567,80 milhões de euros' in tooltip), tooltip
            violations = page.evaluate('window.proofViolations')
            external = [r for r in requests if not r.startswith(f'http://127.0.0.1:{server.server_port}/')]
            assert not errors, errors
            assert not violations, violations
            assert not external, external
            assert page.locator('#chart canvas').count() > 0
            image = str(ROOT / f'proof-{width}.png')
            page.screenshot(path=image, full_page=True)
            report['views'].append({'width': width, 'touch': touch, 'tooltip': tooltip, 'console_errors_warnings': errors,
                                    'csp_violations': violations, 'external_requests': external,
                                    'horizontal_overflow': page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'screenshot': image})
            context.close()
        browser.close()
    report['passed'] = True
finally:
    server.shutdown()
    server.server_close()
print(json.dumps(report, indent=2, ensure_ascii=False))
(ROOT / 'measurement.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
