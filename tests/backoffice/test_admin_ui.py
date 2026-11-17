"""Admin shell and CMS editor affordances: local assets, active navigation, prefixed public
link, progressive hooks that leave the server-rendered forms authoritative."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backoffice.access import IDENTITY_HEADER, PROXY_SECRET_HEADER, AccessPolicy, ProxyAccess
from backoffice.app import SECURITY_HEADERS, create_app
from tests.backoffice.conftest import NOW
from tests.backoffice.test_cms_routes import Env as CmsEnv
from tests.backoffice.test_cms_routes import page_create

ROOT = Path(__file__).resolve().parents[2]

SECRET = "0123456789abcdef" * 4
PREFIX = "/dados/admin"
PROXY = {PROXY_SECRET_HEADER: SECRET, IDENTITY_HEADER: "joao"}


def _nav(html):
    match = re.search(r'<nav class="nav".*?</nav>', html, re.S)
    assert match is not None
    return match.group(0)


def test_shell_loads_only_local_css_font_and_icons(env):
    c = env.client()
    html = c.get("/").text
    assert 'href="/static/css/admin.css"' in html
    assert 'href="/static/css/icons.css"' in html
    assert 'href="/static/images/prumo/favicon.svg"' in html
    assert "<style" not in html.lower()
    assert not re.search(r'\sstyle="', html)
    assert c.get("/static/css/admin.css").status_code == 200
    assert c.get("/static/css/icons.css").status_code == 200
    assert c.get("/static/fonts/icons/prumo-icons.woff2").status_code == 200
    for tag in re.findall(r'<i class="icon[^"]*"[^>]*>', html):
        assert 'aria-hidden="true"' in tag, tag


def test_navigation_is_content_first_and_marks_legacy_editorial(env):
    html = env.client().get("/").text
    nav = _nav(html)
    for label in ("Página inicial", "Páginas e gráficos", "Editorial",
                  "Visão geral", "Fila de revisão", "Séries", "Calculadas"):
        assert label in nav, label
    assert nav.index("Página inicial") < nav.index("Visão geral")
    assert re.search(r'class="nav-link is-legacy" href="/editorial".*?</a>', nav, re.S)
    assert 'class="tag tag-legacy">legado</span>' in nav
    assert 'href="/cms/home"' in nav


@pytest.mark.parametrize(("path", "href"), [
    ("/", "/"),
    ("/queue", "/queue"),
    ("/series", "/series"),
    ("/derived", "/derived"),
    ("/cms", "/cms"),
    ("/editorial", "/editorial"),
])
def test_one_nav_item_is_current(env, path, href):
    html = env.client().get(path).text
    nav = _nav(html)
    assert nav.count('aria-current="page"') == 1, path
    assert re.search(rf'href="{re.escape(href)}"[^>]*aria-current="page"', nav), path


def test_active_navigation_uses_the_path_below_the_validated_mount(env):
    html = env.client().get("/series", headers={"X-Forwarded-Prefix": PREFIX}).text
    nav = _nav(html)
    assert nav.count('aria-current="page"') == 1
    assert re.search(rf'href="{PREFIX}/series"[^>]*aria-current="page"', nav)
    assert f'href="{PREFIX}/cms/home"' in nav
    assert f'href="{PREFIX}/static/css/admin.css"' in html


def test_hostile_prefix_cannot_supply_the_public_link(env):
    html = env.client().get("/", headers={"X-Forwarded-Prefix": "https://evil.example"}).text
    assert "evil.example" not in html
    assert 'class="site-link" href="/"' in html


def test_proxy_mode_public_link_uses_the_configured_origin(env):
    policy = AccessPolicy(ProxyAccess.create(SECRET))
    app = create_app(env.db_path, env.registry, now=lambda: NOW,
                     allowed_hosts=["joao.date"], access_policy=policy)
    c = TestClient(app, base_url="https://joao.date")
    r = c.get("/", headers={**PROXY, "X-Forwarded-Prefix": PREFIX})
    assert r.status_code == 200
    assert 'href="https://joao.date/dados/"' in r.text
    assert 'href="https://evil.example' not in r.text


def test_cms_dashboard_and_editor_load_one_local_admin_script(tmp_path):
    env = CmsEnv(tmp_path)
    c = env.client()
    assert page_create(c).status_code == 303

    dashboard = c.get("/cms")
    assert dashboard.status_code == 200
    assert 'href="/cms/home"' in dashboard.text
    assert "Preparar página inicial" in dashboard.text
    assert '<script src="/static/js/admin.js" defer></script>' in dashboard.text
    assert "data-filterable" in dashboard.text

    editor = c.get("/cms/page/precos")
    assert editor.status_code == 200
    for hook in ('data-dirty-watch', 'data-block', 'data-block-type-select',
                 'data-show-for="text"', 'data-show-for="card"', 'data-show-for="chart"'):
        assert hook in editor.text, hook
    assert "Guardar rascunho" in editor.text and "button-primary" in editor.text
    assert '<script src="/static/js/admin.js" defer></script>' in editor.text
    assert not re.search(r'\sstyle="', editor.text)


def test_home_entry_reflects_a_prepared_home(tmp_path):
    env = CmsEnv(tmp_path)
    c = env.client()
    prepared = c.post("/cms/home/prepare", data={"note": "preparar a página inicial"},
                      headers={"Origin": "http://localhost"})
    assert prepared.status_code == 303
    dashboard = c.get("/cms").text
    assert "Gerir página inicial" in dashboard
    assert "Rascunho privado" in dashboard
    editor = c.get("/cms/page/inicio")
    assert editor.status_code == 200
    nav = _nav(editor.text)
    assert nav.count('aria-current="page"') == 1
    assert re.search(r'href="/cms/home"[^>]*aria-current="page"', nav)


def test_legacy_editorial_stays_script_free(tmp_path):
    env = CmsEnv(tmp_path)
    c = env.client()
    for path in ("/editorial", "/editorial/inicio"):
        html = c.get(path).text
        assert "<script" not in html.lower(), path
        assert 'class="tag tag-legacy">legado</span>' in html, path


def test_admin_csp_is_strict_and_local(env):
    csp = env.client().get("/").headers["content-security-policy"]
    assert csp == SECURITY_HEADERS["Content-Security-Policy"]
    assert "style-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "font-src 'self'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "http:" not in csp and "https:" not in csp


def test_admin_css_keeps_the_editorial_identity(env):
    css = env.client().get("/static/css/admin.css").text
    assert "linear-gradient" not in css and "radial-gradient" not in css
    assert "--red" in css and "--paper" in css and "--serif" in css
    assert "prefers-reduced-motion" in css


def test_reorder_controls_keep_visible_text_when_the_icon_font_fails():
    html = (ROOT / "backoffice/templates/editorial_page.html").read_text(encoding="utf-8")
    assert '<span class="sr-only">Subir</span>' not in html
    assert '<span class="sr-only">Descer</span>' not in html
    assert re.search(r'aria-hidden="true"></i> Subir</button>', html)
    assert re.search(r'aria-hidden="true"></i> Descer</button>', html)


def test_admin_script_splits_the_show_for_attribute_on_whitespace():
    js = (ROOT / "static/js/admin.js").read_text(encoding="utf-8")
    assert ".split(/\\s+/)" in js
    assert ".split(/\\\\s+/)" not in js
