"""Public shell affordances: local stylesheet/icon font, labels that survive a blocked font,
and the same prefixing/no-external rules as the rest of the public site."""
from app.main import SECURITY_HEADERS


def test_public_html_draws_the_search_icon_locally(client):
    html = client.get("/", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert 'href="/dados/static/css/prumo.css"' in html
    assert 'href="/dados/static/vendor/bootstrap/bootstrap-subset.css"' in html
    assert 'href="/dados/static/images/prumo/favicon.svg"' in html
    assert "cdn." not in html and "googleapis" not in html

    assert "Procurar" in html
    assert '<svg class="ui-icon"' in html
    css = client.get("/static/css/app-shell.css").text
    assert "data:image/svg+xml" not in css
    assert "url(http" not in css


def test_icon_font_and_licence_are_served_locally(client):
    css = client.get("/static/css/icons.css")
    assert css.status_code == 200
    assert 'url("../fonts/icons/prumo-icons.woff2")' in css.text
    assert "@font-face" in css.text and "http" not in css.text

    font = client.get("/static/fonts/icons/prumo-icons.woff2")
    assert font.status_code == 200
    assert font.content.startswith(b"wOF2")
    assert len(font.content) < 20_000  # subset, not the 130 kB upstream build

    licence = client.get("/static/fonts/icons/LICENSE.bootstrap-icons.txt")
    assert licence.status_code == 200 and "MIT License" in licence.text


def test_public_csp_still_forbids_inline_execution(client):
    csp = client.get("/").headers["content-security-policy"]
    assert csp == SECURITY_HEADERS["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
