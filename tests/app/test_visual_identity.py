"""The public identity stays lightweight; the admin toolkit is pinned and local."""
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "static/vendor/tabler/1.7.5"


def test_vendor_receipt_pins_the_installed_bytes():
    manifest = json.loads((VENDOR / "manifest.json").read_text())
    assert manifest["version"] == "1.7.5"
    assert manifest["archive_integrity"].startswith("sha512-")
    for filename, expected in manifest["files"].items():
        body = (VENDOR / filename).read_bytes()
        assert hashlib.sha256(body).hexdigest() == expected["sha256"]
        assert len(body) == expected["bytes"]
    assert "MIT License" in (VENDOR / "LICENSE").read_text()


def test_tabler_has_no_imports_or_nonembedded_browser_resources():
    css = (VENDOR / "tabler.min.css").read_text()
    assert "@import" not in css
    assert "sourceMappingURL" not in css
    assert chr(0x2014) not in css
    urls = re.findall(r"url\(([^)]+)\)", css)
    assert urls and all(url.strip("\"'").startswith("data:") for url in urls)


def test_public_summaries_do_not_load_admin_toolkit(client):
    html = client.get("/").text
    assert "vendor/tabler" not in html
    assert "admin.js" not in html
    assert "<script" not in html


def test_brand_is_a_vector_plumb_bob_not_font_text(client):
    icon = ElementTree.fromstring(client.get("/static/images/prumo/favicon.svg").content)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    assert icon.attrib["viewBox"] == "0 0 32 32"
    assert not icon.findall(".//svg:text", ns)
    assert icon.find("svg:path[@id='plumb-line']", ns) is not None
    assert icon.find("svg:path[@id='plumb-weight']", ns) is not None


def test_public_palette_separates_brand_from_second_chart_line(client):
    css = client.get("/static/css/prumo.css").text
    assert "--accent: #1b514b" in css
    assert "--series-b: #9c5b24" in css
    # The existing ECharts adapter uses this compatibility token; SVG uses the same one.
    assert "--red: var(--series-b)" in css
    assert "prefers-reduced-motion" in css
