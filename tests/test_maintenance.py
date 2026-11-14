"""The legacy UI is gone: the app serves a maintenance page and a health check."""
import os
import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "venv", ".venv", ".venv-ci", ".superpowers", "docs", "tests", "static", "__pycache__"}
CODE_FILE = re.compile(r"(\.(py|sh|yml|yaml|txt|toml)$|^Dockerfile$|^requirements.*)")
FORBIDDEN = ("claude-max-proxy", "anthropic")
# Served static files and current documentation: no AI remnants either (Task 23, D-M5).
AI_REMNANTS = ("claude-max-proxy", "anthropic", "haiku")
TEXT_FILE = re.compile(r"\.(md|txt|html|js|css|json|svg|py|sh|yml|yaml|toml)$")
# Handoff/review history lives under docs/superpowers/; these older documents describe the
# retired AI dashboard and are listed as historical in DOCS_MAP.md.
HISTORICAL_DOCS = {
    "ROADMAP.md", "OPENSOURCE.md",
    "docs/operations/PHASE_1_SUMMARY.md", "docs/operations/PHASE_4_MONITORING.md",
    "docs/testing/2026-03-01-v9-report.md",
}
NOT_SCANNED_DIRS = {".git", "venv", ".venv", ".venv-ci", ".superpowers", "tests",
                    "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache"}


def test_root_is_maintenance():
    r = client.get("/")
    assert r.status_code == 200
    assert "Em manutenção" in r.text


def test_deep_path_is_maintenance():
    r = client.get("/painel/xyz")
    assert r.status_code == 200
    assert "Em manutenção" in r.text


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_head_root_deep_path_and_healthz_answer_200():
    """Uptime probes commonly use HEAD (D-M8)."""
    for path in ("/", "/healthz", "/painel/xyz"):
        r = client.head(path)
        assert r.status_code == 200, path
        assert r.content == b""


def test_only_the_favicon_static_file_is_kept_and_served():
    static = os.path.join(REPO, "static")
    kept = sorted(os.path.relpath(os.path.join(root, name), static)
                  for root, _dirs, files in os.walk(static) for name in files)
    assert kept == ["images/prumo/favicon.svg"]
    assert client.get("/static/images/prumo/favicon.svg").status_code == 200
    assert client.get("/static/js/sections/analise.js").status_code == 404


def test_dead_legacy_config_module_is_gone():
    assert not os.path.exists(os.path.join(REPO, "app", "config.py"))


def test_no_claude_references():
    hits = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not CODE_FILE.search(name):
                continue
            path = os.path.join(root, name)
            try:
                text = open(path, encoding="utf-8").read().lower()
            except (UnicodeDecodeError, OSError):
                continue
            if any(f in text for f in FORBIDDEN):
                hits.append(os.path.relpath(path, REPO))
    assert not hits, hits


def test_no_ai_remnants_in_static_or_current_docs():
    hits = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in NOT_SCANNED_DIRS]
        rel_root = os.path.relpath(root, REPO)
        if rel_root == os.path.join("docs", "superpowers") or rel_root.startswith(
                os.path.join("docs", "superpowers") + os.sep):
            dirs[:] = []
            continue
        for name in files:
            rel = os.path.normpath(os.path.join(rel_root, name))
            if not TEXT_FILE.search(name) or rel in HISTORICAL_DOCS:
                continue
            try:
                text = open(os.path.join(root, name), encoding="utf-8").read().lower()
            except (UnicodeDecodeError, OSError):
                continue
            if any(f in text for f in AI_REMNANTS):
                hits.append(rel)
    assert not hits, hits
