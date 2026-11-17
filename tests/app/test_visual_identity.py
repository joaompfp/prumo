"""The public identity stays lightweight; the admin toolkit is pinned and local."""
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "static/vendor/tabler/1.7.5"
CARMIN = "#9b1c2e"
WARM_PAPER = "#f6f4f1"
CHART_B = "#c0392b"


def _luminance(value):
    value = value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045
              else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first, second):
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


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


def test_public_palette_restores_warm_paper_charcoal_and_carmin(client):
    css = client.get("/static/css/prumo.css").text
    for token in ("--paper: " + WARM_PAPER, "--surface: #ffffff", "--ink: #1a1a1a",
                  "--muted: #524d48", "--rule: #e2ded9", "--rule-strong: #c9c3bc",
                  "--accent: " + CARMIN, "--accent-hover: #7d1524",
                  "--accent-soft: #f7e7ea"):
        assert token in css, token
    for retired in ("#1b514b", "#18322f", "#123d38", "#52645f", "#dbe2dd",
                    "#b8c8c0", "#e8efea"):
        assert retired not in css, retired
    assert "prefers-reduced-motion" in css


def test_public_chart_tokens_keep_two_distinguishable_series(client):
    css = client.get("/static/css/prumo.css").text
    assert "--series-b: " + CHART_B in css
    # The existing ECharts adapter uses this compatibility token; SVG uses the same one.
    assert "--red: var(--series-b)" in css
    assert ".chart-line-a { stroke: var(--ink); }" in css
    assert ".chart-line-b { stroke: var(--red); stroke-dasharray: 6 3; }" in css
    assert ".chart-last-b { fill: var(--red); }" in css
    # The single-series latest point is a brand highlight, not a second data series.
    assert ".spark-end { fill: var(--accent); }" in css
    assert ".chart-last { fill: var(--accent); }" in css
    assert ".chart-last-label { fill: var(--accent); font-family: var(--sans);" in css
    assert _contrast("#1a1a1a", CHART_B) >= 3
    assert _contrast(WARM_PAPER, CARMIN) >= 4.5


def test_public_carmin_meets_text_and_control_contrast(client):
    css = client.get("/static/css/prumo.css").text
    assert css.count(CARMIN) >= 1
    assert _contrast(CARMIN, WARM_PAPER) >= 4.5
    assert _contrast(CARMIN, "#ffffff") >= 4.5
    assert _contrast("#ffffff", CARMIN) >= 4.5
    assert _contrast("#524d48", WARM_PAPER) >= 4.5


def test_brand_is_a_vector_plumb_bob_not_font_text(client):
    icon = ElementTree.fromstring(client.get("/static/images/prumo/favicon.svg").content)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    assert icon.attrib["viewBox"] == "0 0 32 32"
    assert not icon.findall(".//svg:text", ns)
    assert icon.find("svg:path[@id='plumb-line']", ns) is not None
    assert icon.find("svg:path[@id='plumb-weight']", ns) is not None


def test_favicon_uses_the_carmin_and_keeps_the_plumb_geometry(client):
    icon = ElementTree.fromstring(client.get("/static/images/prumo/favicon.svg").content)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    rect = icon.find("svg:rect", ns)
    assert rect is not None
    assert rect.attrib["fill"].lower() == CARMIN
    line = icon.find("svg:path[@id='plumb-line']", ns)
    weight = icon.find("svg:path[@id='plumb-weight']", ns)
    assert line is not None and weight is not None
    assert line.attrib["d"] == "M15 4h2v10h-2z"
    assert weight.attrib["d"] == "M12 13h8v4l3 3-7 9-7-9 3-3z"


def test_chart_adapter_fallbacks_match_the_restored_reading_palette():
    adapter = (ROOT / "tools/charts/src/adapter.js").read_text(encoding="utf-8")
    assert "css('--ink', '#1a1a1a')" in adapter
    assert "css('--muted', '#524d48')" in adapter
    assert "css('--rule', '#e2ded9')" in adapter
    assert "css('--red', '" + CHART_B + "')" in adapter
    assert _contrast("#1a1a1a", CHART_B) >= 3
