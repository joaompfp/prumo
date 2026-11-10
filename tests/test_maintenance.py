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
