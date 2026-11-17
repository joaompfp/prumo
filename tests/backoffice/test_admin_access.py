"""Admin entry, prefix and access boundary for the statistics CMS (plan A1/A2).

These tests exercise the real app: both mount positions, a hostile prefix, local developer
mode, and the fail-closed Traefik/Authelia proxy mode. The deployment files are parsed as
YAML after the one Go-template expression is rendered, so a broken template is caught here
rather than on the edge.
"""
import logging
import re
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from starlette.requests import Request

import backoffice.access as access_module
from app.main import _base as public_base
from backoffice import reads
from backoffice.access import (
    IDENTITY_HEADER,
    LOCAL_ACTOR,
    PROXY_SECRET_HEADER,
    AccessConfigError,
    AccessPolicy,
    ProxyAccess,
)
from backoffice.app import app_from_env, create_app
from presentation.web import mount_prefix, prefixed
from tests.backoffice.conftest import NOW

ROOT = Path(__file__).resolve().parents[2]
SECRET = "0123456789abcdef" * 4
PROXY_HEADERS = {PROXY_SECRET_HEADER: SECRET, IDENTITY_HEADER: "joao"}
PREFIX = "/dados/admin"


def _request(prefix: str | None) -> Request:
    headers = [] if prefix is None else [(b"x-forwarded-prefix", prefix.encode())]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def _proxy_app(env, *, allowed_hosts=("joao.date",), editorial_db_path=None):
    policy = AccessPolicy(ProxyAccess.create(SECRET))
    return create_app(env.db_path, env.registry, now=lambda: NOW,
                      allowed_hosts=list(allowed_hosts),
                      editorial_db_path=editorial_db_path, access_policy=policy)


def _with_probe_routes(app):
    @app.get("/_actor")
    def actor(request: Request):
        return {"actor": request.app.state.admin.actor(request)}

    @app.post("/_guard")
    def guarded(request: Request):
        request.app.state.admin.guard(request)
        return {"ok": True}

    return app


# --- A1: the shared prefix helper ------------------------------------------------------------

def test_public_app_uses_the_shared_helper():
    assert public_base is mount_prefix


@pytest.mark.parametrize("raw, expected", [
    (None, ""),
    ("", ""),
    ("/", ""),
    ("/dados", "/dados"),
    ("dados", "/dados"),
    ("/dados/", "/dados"),
    ("  /dados  ", "/dados"),
    ("/dados/admin", "/dados/admin"),
    ("//evil.example", ""),
    ("/dados//x", ""),
    ("https://evil.example", ""),
    ("/dados?x=1", ""),
    ("/dados\\x", ""),
    ("/dados/../x", ""),
    ("/a_b.c~d", "/a_b.c~d"),
])
def test_prefix_validation_is_unchanged(raw, expected):
    assert mount_prefix(_request(raw)) == expected


def test_prefixed_joins_only_an_absolute_path():
    assert prefixed("", "/series") == "/series"
    assert prefixed(PREFIX, "/series?page=2") == f"{PREFIX}/series?page=2"
    with pytest.raises(ValueError):
        prefixed(PREFIX, "series")


def test_backoffice_links_and_nav_are_prefixed(env):
    html = env.client().get("/series", headers={"X-Forwarded-Prefix": PREFIX}).text
    assert f'href="{PREFIX}/"' in html
    assert f'href="{PREFIX}/series"' in html
    assert f'action="{PREFIX}/series"' in html
    assert not re.search(r'(?:href|action)="/(?!dados/admin[/"])', html)
    assert f'href="{PREFIX}/series/s1"' in html


def test_editorial_forms_and_filter_are_prefixed(env):
    html = env.client().get("/editorial/inicio", headers={"X-Forwarded-Prefix": PREFIX}).text
    actions = re.findall(r'action="([^"]+)"', html)
    assert actions
    assert all(a.startswith(f"{PREFIX}/") for a in actions), actions
    assert f'action="{PREFIX}/editorial/inicio/reset"' in html


def test_series_pagination_is_prefixed(env, monkeypatch):
    monkeypatch.setattr(reads, "PAGE_SIZE", 1)
    html = env.client().get("/series", headers={"X-Forwarded-Prefix": PREFIX}).text
    assert f'href="{PREFIX}/series?page=2"' in html


def test_redirect_after_a_form_is_prefixed(env):
    c = TestClient(
        create_app(env.db_path, env.registry, now=lambda: NOW, editorial_db_path=env.db_path),
        base_url="http://localhost", follow_redirects=False)
    r = c.post("/editorial/inicio/discard", data={"version": "0", "note": "prefix redirect"},
               headers={"Origin": "http://localhost", "X-Forwarded-Prefix": PREFIX})
    assert r.status_code == 303
    assert r.headers["location"] == f"{PREFIX}/editorial/inicio"


@pytest.mark.parametrize("hostile", [
    "//evil.example", "https://evil.example", "/dados/admin/../x", "/dados/admin?x=1",
    "/evil",
])
def test_hostile_or_unapproved_prefixes_are_ignored(env, hostile):
    c = env.client()
    html = c.get("/series", headers={"X-Forwarded-Prefix": hostile}).text
    assert "evil.example" not in html
    assert 'href="/series"' in html
    assert '"/evil' not in html


def test_backoffice_responses_are_no_store_and_vary_on_the_prefix(env):
    c = env.client()
    r = c.get("/", headers={"X-Forwarded-Prefix": PREFIX})
    assert r.headers["cache-control"] == "no-store"
    assert "x-forwarded-prefix" in r.headers["vary"].lower()
    assert "form-action 'self'" in r.headers["content-security-policy"]
    assert "base-uri 'none'" in r.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


# --- A2: local mode --------------------------------------------------------------------------

def test_local_mode_is_explicit_and_binds_the_developer_actor(env):
    app = _with_probe_routes(create_app(env.db_path, env.registry, now=lambda: NOW))
    c = TestClient(app, base_url="http://localhost")
    assert c.get("/").status_code == 200
    assert c.get("/_actor").json() == {"actor": LOCAL_ACTOR}
    assert c.get("/healthz").json() == {"status": "ok", "db": "ready"}


# --- A2: proxy mode --------------------------------------------------------------------------

@pytest.mark.parametrize("headers", [
    {},
    {IDENTITY_HEADER: "joao"},                        # forged identity, no secret
    {PROXY_SECRET_HEADER: SECRET},                    # secret, no identity
    {PROXY_SECRET_HEADER: SECRET, IDENTITY_HEADER: "someone"},
    {PROXY_SECRET_HEADER: "wrong-secret", IDENTITY_HEADER: "joao"},
])
def test_proxy_mode_rejects_missing_or_wrong_credentials(env, headers):
    c = TestClient(_proxy_app(env), base_url="https://joao.date")
    r = c.get("/", headers=headers)
    assert r.status_code == 401
    assert r.text == "admin access denied"
    assert SECRET not in r.text and "joao" not in r.text
    assert r.headers["cache-control"] == "no-store"
    assert "form-action 'self'" in r.headers["content-security-policy"]


def test_proxy_mode_accepts_the_verified_actor(env):
    c = TestClient(_with_probe_routes(_proxy_app(env)), base_url="https://joao.date")
    assert c.get("/", headers=PROXY_HEADERS).status_code == 200
    assert c.get("/_actor", headers=PROXY_HEADERS).json() == {"actor": "joao"}


def test_correct_secret_with_a_non_owner_identity_is_refused_before_html(env):
    c = TestClient(_proxy_app(env), base_url="https://joao.date")
    r = c.get("/", headers={PROXY_SECRET_HEADER: SECRET, IDENTITY_HEADER: "other"})
    assert r.status_code == 401
    assert r.text == "admin access denied"
    assert "<html" not in r.text.lower()


def test_rejected_credentials_are_not_logged(env, caplog):
    c = TestClient(_proxy_app(env), base_url="https://joao.date")
    with caplog.at_level(logging.INFO, logger="backoffice"):
        r = c.get("/", headers={PROXY_SECRET_HEADER: "wrong-secret", IDENTITY_HEADER: "joao"})
    assert r.status_code == 401
    assert "wrong-secret" not in caplog.text and "joao" not in caplog.text


def test_tailnet_address_and_remote_user_alone_are_not_enough(env):
    app = _proxy_app(env, allowed_hosts=("100.118.19.6", "joao.date"))
    c = TestClient(app, base_url="http://100.118.19.6:8089")
    assert c.get("/", headers={IDENTITY_HEADER: "joao"}).status_code == 401
    # The secret alone is not the boundary either: Host must still be the canonical origin.
    assert c.get("/", headers=PROXY_HEADERS).status_code == 401


def test_missing_secret_is_compared_in_constant_time(env, monkeypatch):
    calls = []

    def spy(a, b):
        calls.append((a, b))
        return False

    monkeypatch.setattr(access_module, "compare_digest", spy)
    c = TestClient(_proxy_app(env), base_url="https://joao.date")
    r = c.get("/", headers={IDENTITY_HEADER: "joao"})
    assert r.status_code == 401
    assert calls == [(b"", SECRET.encode())]


def test_proxy_origin_ignores_a_forged_forwarded_scheme(env):
    c = TestClient(_with_probe_routes(_proxy_app(env)), base_url="https://joao.date")
    ok = c.post("/_guard", headers={**PROXY_HEADERS, "Origin": "https://joao.date",
                                    "X-Forwarded-Proto": "http"})
    assert ok.status_code == 200
    spoofed = c.post("/_guard", headers={**PROXY_HEADERS, "Origin": "http://joao.date",
                                         "X-Forwarded-Proto": "https"})
    assert spoofed.status_code == 403
    assert spoofed.json()["detail"] == "cross-origin form refused"


@pytest.mark.parametrize("origin", [
    "https://evil.example", "http://joao.date", "https://joao.date/other", "null",
])
def test_proxy_origin_must_be_the_configured_canonical_origin(env, origin):
    c = TestClient(_with_probe_routes(_proxy_app(env)), base_url="https://joao.date")
    r = c.post("/_guard", headers={**PROXY_HEADERS, "Origin": origin})
    assert r.status_code == 403


def test_proxy_origin_requires_a_matching_host(env):
    app = _proxy_app(env, allowed_hosts=("joao.date", "joao.date.evil"))
    c = TestClient(app, base_url="https://joao.date.evil")
    r = c.post("/_guard", headers={**PROXY_HEADERS, "Origin": "https://joao.date"})
    assert r.status_code == 401


def test_proxy_origin_refuses_cross_site_fetch_metadata(env):
    c = TestClient(_with_probe_routes(_proxy_app(env)), base_url="https://joao.date")
    r = c.post("/_guard", headers={**PROXY_HEADERS, "Origin": "https://joao.date",
                                   "Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403


def test_healthz_is_exempt_and_never_exposes_its_database_error(env, tmp_path):
    missing = tmp_path / "missing.sqlite3"
    policy = AccessPolicy(ProxyAccess.create(SECRET))
    app = create_app(missing, env.registry, now=lambda: NOW,
                     allowed_hosts=["100.118.19.6", "joao.date"], access_policy=policy)
    c = TestClient(app, base_url="http://100.118.19.6:8089")
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "unavailable"}
    assert "missing.sqlite3" not in r.text and "database not found" not in r.text
    assert r.headers["cache-control"] == "no-store"
    assert not missing.exists()


# --- A2: configuration ----------------------------------------------------------------------

def test_proxy_configuration_is_optional_and_fails_closed_when_incomplete():
    assert AccessPolicy.from_env({}).proxy is None
    assert AccessPolicy.from_env({"PRUMO_ADMIN_PROXY_SECRET": ""}).proxy is None
    for incomplete in ({"PRUMO_ADMIN_USER": "joao"},
                       {"PRUMO_ADMIN_ORIGIN": "https://joao.date"},
                       {"PRUMO_ADMIN_PROXY_SECRET": "", "PRUMO_ADMIN_ORIGIN": "https://x"}):
        with pytest.raises(AccessConfigError):
            AccessPolicy.from_env(incomplete)
    policy = AccessPolicy.from_env({"PRUMO_ADMIN_PROXY_SECRET": SECRET})
    assert policy.proxy is not None
    assert policy.proxy.users == ("joao",)
    assert policy.proxy.origin == "https://joao.date"


@pytest.mark.parametrize("extra", [
    {"PRUMO_ADMIN_ORIGIN": "http://joao.date"},
    {"PRUMO_ADMIN_ORIGIN": "https://joao.date/admin"},
    {"PRUMO_ADMIN_ORIGIN": "https://joao.date:8443"},
    {"PRUMO_ADMIN_ORIGIN": "https://user@joao.date"},
    {"PRUMO_ADMIN_USER": "joao, bad user"},
    {"PRUMO_ADMIN_PROXY_SECRET": "short"},
    {"PRUMO_ADMIN_PROXY_SECRET": " " + SECRET},
    {"PRUMO_ADMIN_PROXY_SECRET": SECRET[:-1] + "'"},
    {"PRUMO_ADMIN_PROXY_SECRET": SECRET[:-1] + '"'},
    {"PRUMO_ADMIN_PROXY_SECRET": SECRET[:-1] + "$"},
    {"PRUMO_ADMIN_PROXY_SECRET": SECRET[:-1] + "!"},
    {"PRUMO_ADMIN_PROXY_SECRET": SECRET[:-1] + "\\"},
    {"PRUMO_ADMIN_PROXY_SECRET": SECRET[:-1] + "ç"},
])
def test_proxy_configuration_rejects_incomplete_or_weak_values(extra):
    env = {"PRUMO_ADMIN_PROXY_SECRET": SECRET, **extra}
    with pytest.raises(AccessConfigError) as exc:
        AccessPolicy.from_env(env)
    assert SECRET not in str(exc.value)


def test_proxy_secret_accepts_the_documented_template_alphabet():
    for secret in ("a" * 32, "A1_-" * 8, "0123456789abcdef" * 4, "x" * 64):
        assert ProxyAccess.create(secret).secret == secret


def test_app_from_env_does_not_fall_back_when_proxy_is_partial(monkeypatch):
    monkeypatch.delenv("PRUMO_ADMIN_PROXY_SECRET", raising=False)
    monkeypatch.setenv("PRUMO_ADMIN_USER", "joao")
    with pytest.raises(AccessConfigError):
        app_from_env()


# --- deployment templates (versioned, never applied here) ------------------------------------

def _render_traefik_template(text: str) -> dict:
    expression = '{{ env "PRUMO_ADMIN_PROXY_SECRET" }}'
    assert expression in text
    return yaml.safe_load(text.replace(expression, "test-secret"))


def test_traefik_template_has_the_exact_boundary_and_middleware_order():
    text = (ROOT / "deploy/traefik-prumo-admin.yml").read_text(encoding="utf-8")
    doc = _render_traefik_template(text)
    router = doc["http"]["routers"]["prumo-admin"]
    assert router["rule"] == (
        "Host(`joao.date`) && (Path(`/dados/admin`) || PathPrefix(`/dados/admin/`))")
    assert router["priority"] == 60
    assert router["middlewares"] == [
        "prumo-admin-sanitize", "prumo-admin-authelia",
        "prumo-admin-inject-secret", "prumo-admin-strip",
    ]
    order = router["middlewares"]
    assert order.index("prumo-admin-authelia") < order.index("prumo-admin-inject-secret")
    assert order.index("prumo-admin-inject-secret") < order.index("prumo-admin-strip")
    middlewares = doc["http"]["middlewares"]
    assert middlewares["prumo-admin-sanitize"]["headers"]["customRequestHeaders"][
        "X-Prumo-Proxy-Secret"] == ""
    assert middlewares["prumo-admin-inject-secret"]["headers"]["customRequestHeaders"][
        "X-Prumo-Proxy-Secret"] == "test-secret"
    assert middlewares["prumo-admin-strip"]["stripPrefix"]["prefixes"] == [PREFIX]
    assert middlewares["prumo-admin-authelia"]["forwardAuth"]["authResponseHeaders"] == [
        "Remote-User", "Remote-Groups"]
    assert "test-secret" not in text


def test_traefik_template_survives_the_allowed_secret_alphabet():
    text = (ROOT / "deploy/traefik-prumo-admin.yml").read_text(encoding="utf-8")
    expression = '{{ env "PRUMO_ADMIN_PROXY_SECRET" }}'
    secret = "A1_-" * 8
    ProxyAccess.create(secret)          # the app accepts exactly what the template can quote
    doc = yaml.safe_load(text.replace(expression, secret))
    assert doc["http"]["middlewares"]["prumo-admin-inject-secret"]["headers"][
        "customRequestHeaders"]["X-Prumo-Proxy-Secret"] == secret


def test_authelia_template_challenges_the_exact_scope_without_a_subject():
    doc = yaml.safe_load(
        (ROOT / "deploy/authelia-prumo-admin.yml").read_text(encoding="utf-8"))
    rules = doc["access_control"]["rules"]
    assert len(rules) == 1
    challenge = rules[0]
    assert challenge["domain"] == "joao.date"
    assert challenge["resources"] == ["^/dados/admin(/.*)?$"]
    assert challenge["policy"] == "two_factor"
    assert "subject" not in challenge
    assert "networks" not in challenge
    pattern = re.compile(challenge["resources"][0])
    for covered in ("/dados/admin", "/dados/admin/", "/dados/admin/series"):
        assert pattern.search(covered)
    for outside in ("/dados", "/dados/administration", "/dados/adminx"):
        assert not pattern.search(outside)


def test_backoffice_compose_defaults_keep_proxy_mode_disabled():
    doc = yaml.safe_load(
        (ROOT / "deploy/prumo-backoffice.yml").read_text(encoding="utf-8"))
    env = doc["services"]["prumo-backoffice"]["environment"]
    assert env["PRUMO_ADMIN_PROXY_SECRET"] == "${PRUMO_ADMIN_PROXY_SECRET:-}"
    assert env["PRUMO_ADMIN_USER"] == "${PRUMO_ADMIN_USER:-}"
    assert env["PRUMO_ADMIN_ORIGIN"] == "${PRUMO_ADMIN_ORIGIN:-}"
    assert AccessPolicy.from_env({k: "" for k in (
        "PRUMO_ADMIN_PROXY_SECRET", "PRUMO_ADMIN_USER", "PRUMO_ADMIN_ORIGIN")}).proxy is None


def test_deployment_runbook_names_the_boundary_secret_and_rollback():
    text = (ROOT / "deploy/README-admin.md").read_text(encoding="utf-8")
    for needed in (
        "sops secrets/core.enc.env",
        "sops secrets/web.enc.env",
        "Path(`/dados/admin`) || PathPrefix(`/dados/admin/`)",
        "priority 60",
        "rollback",
        "https://joao.date",
        "X-Prumo-Proxy-Secret",
        "[A-Za-z0-9_-]",
        "single-quoted YAML scalar",
        "only after the backoffice itself is in proxy mode",
        "local mode",
        "policy: two_factor",
        "Authelia authenticates; the app authorizes.",
        "before the external wall, the `group:bots` rules and the generic",
        "redirected to the Authelia portal",
        "admin access denied",
    ):
        assert needed in text
