"""Pinned public frontend toolkit: local Bootstrap subset and its byte receipt."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "static" / "vendor" / "bootstrap"
SUBSET = VENDOR / "bootstrap-subset.css"
MANIFEST = VENDOR / "MANIFEST.json"


def _manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_bootstrap_subset_is_pinned_and_matches_its_manifest():
    manifest = _manifest()
    assert manifest["package"] == "bootstrap"
    assert manifest["version"] == "5.3.9"
    body = SUBSET.read_bytes()
    assert body.startswith(b"/*!\n * Bootstrap Components Subset v5.3.9")
    assert len(body) == manifest["subset"]["bytes"]
    assert hashlib.sha256(body).hexdigest() == manifest["subset"]["sha256"]
    licence = (VENDOR / "LICENSE").read_bytes()
    assert hashlib.sha256(licence).hexdigest() == manifest["license"]["sha256"]
    assert b"MIT License" in licence


def test_bootstrap_subset_is_local_and_limited_to_reviewed_components():
    css = SUBSET.read_text(encoding="utf-8")
    assert "@import" not in css
    assert "url(http" not in css
    assert "cdn." not in css
    for token in (".btn {", ".form-control {", ".form-select {", ".form-check-input {",
                  ".input-group {", ".nav {", ".nav-link {", ".pagination {",
                  ".visually-hidden"):
        assert token in css, token
    # Prumo owns these product classes; the vendor subset must not overwrite them.
    for absent in (".card {", ".badge {", ".navbar {", ".container {"):
        assert absent not in css, absent


def test_reproduction_script_verifies_the_checked_in_bytes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor_bootstrap.py"), "--check"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "sha256" in result.stdout
