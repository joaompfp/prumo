"""Painted mobile utility controls must never cover primary navigation targets."""
import pytest

from tests.app.test_chart_interaction import browser as browser
from tests.app.test_chart_interaction import site_url as site_url


@pytest.mark.parametrize('width', (320, 360, 390, 600, 768, 900, 901, 1120, 1440))
def test_mobile_utility_and_brand_do_not_cover_primary_targets(browser, site_url, width):
    context = browser.new_context(viewport={'width': width, 'height': 844})
    try:
        page = context.new_page()
        page.goto(site_url + '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT',
                  wait_until='networkidle')
        page.evaluate('() => document.fonts.ready')
        boxes = page.evaluate('''() => {
          const box=e=>e.getBoundingClientRect().toJSON();
          return {utility:box(document.querySelector('.app-more > summary')),
                  brand:box(document.querySelector('.brand')),
                  nav:[...document.querySelectorAll('.app-nav-link')].map(box)};
        }''')
        utility = boxes['utility']

        def separate(a, b):
            return a['right'] <= b['left'] or a['left'] >= b['right'] or \
                a['bottom'] <= b['top'] or a['top'] >= b['bottom']

        assert len(boxes['nav']) == 3
        assert all(separate(utility, target) for target in boxes['nav'])
        assert separate(utility, boxes['brand'])
        assert utility['height'] >= 44
        assert page.locator('.app-more > summary').evaluate(
            '(e) => parseFloat(getComputedStyle(e).fontSize)') >= 26.64
        page.locator('.app-more > summary').click()
        assert page.locator('.app-more').get_attribute('open') is not None
        assert page.locator('.app-more .app-panel').is_visible()
        assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth + 1')
    finally:
        context.close()
