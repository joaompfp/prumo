#!/usr/bin/env python3
"""
Prumo — Visual chart validation for all 372 indicators.

Takes a screenshot of each indicator's chart in the Análise tab.
Detects rendering issues: empty canvas, missing lines, scale problems.

Outputs:
  - Screenshot per indicator: docs/testing/screenshots/{SOURCE}_{INDICATOR}.png
  - JSON report: docs/testing/chart-validation-report.json
  - Log: /tmp/prumo-chart-validation.log

Usage:
    cd stacks/jarbas/images/prumo
    source venv/bin/activate
    python docs/testing/validate_charts.py [--headless] [--resume N]
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────
APP_URL = "https://joao.date/dados/"
INTERNAL_API = "http://172.20.0.6:8080"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
REPORT_FILE = Path(__file__).parent / "chart-validation-report.json"
LOG_FILE = "/tmp/prumo-chart-validation.log"

# Use frontend default 5-year window
_now = datetime.now()
DEFAULT_FROM = f"{_now.year - 5}-{_now.month:02d}"
DEFAULT_TO = f"{_now.year}-{_now.month:02d}"

MAX_CHART_WAIT = 30  # seconds


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def fetch_indicators():
    resp = urllib.request.urlopen(f"{INTERNAL_API}/api/catalog", timeout=30)
    catalog = json.loads(resp.read())
    indicators = []
    for src, src_info in catalog.items():
        for ind_id, ind_info in src_info.get("indicators", {}).items():
            indicators.append({
                "source": src,
                "id": ind_id,
                "label": ind_info.get("label", ind_id),
                "unit": ind_info.get("unit", ""),
                "frequency": ind_info.get("frequency", ""),
            })
    return indicators


def validate_chart(context, source, ind_id, label):
    """
    Open indicator in browser, wait for chart, take screenshot,
    analyse the canvas for rendering issues.
    Returns dict with validation results.
    """
    hash_url = (
        f"{APP_URL}#explorador"
        f"?s={urllib.parse.quote(source + '/' + ind_id)}"
        f"&from={DEFAULT_FROM}&to={DEFAULT_TO}"
    )

    result = {
        "source": source,
        "indicator": ind_id,
        "label": label,
        "status": "UNKNOWN",
        "has_canvas": False,
        "canvas_has_content": False,
        "line_colors_detected": 0,
        "error_state": None,
        "screenshot": None,
        "issues": [],
    }

    page = context.new_page()
    try:
        page.goto(hash_url, wait_until="networkidle", timeout=45000)

        # Wait for chip
        try:
            page.wait_for_selector(".indicator-chip", timeout=10000)
        except Exception:
            result["issues"].append("chip_not_loaded")

        # Wait for chart or error
        deadline = time.time() + MAX_CHART_WAIT
        chart_state = "timeout"
        while time.time() < deadline:
            state = page.evaluate("""() => {
                const scope = document.getElementById('explorador') || document;
                const err = scope.querySelector('.error-state');
                if (err) return JSON.stringify({state: 'error', msg: err.textContent.trim().substring(0, 200)});
                const canvas = scope.querySelector('#exp-chart-wrap canvas');
                if (canvas) return JSON.stringify({state: 'chart', w: canvas.width, h: canvas.height});
                return JSON.stringify({state: 'waiting'});
            }""")
            info = json.loads(state)
            if info["state"] == "chart":
                chart_state = "chart"
                result["has_canvas"] = True
                break
            elif info["state"] == "error":
                chart_state = "error"
                result["error_state"] = info.get("msg", "")
                break
            time.sleep(0.5)

        if chart_state == "timeout":
            result["status"] = "TIMEOUT"
            result["issues"].append("chart_render_timeout")
        elif chart_state == "error":
            result["status"] = "ERROR"
            result["issues"].append(f"error_state: {result['error_state']}")
        else:
            # Analyse canvas content
            analysis = page.evaluate("""() => {
                const scope = document.getElementById('explorador') || document;
                const canvas = scope.querySelector('#exp-chart-wrap canvas');
                if (!canvas) return {empty: true};
                const ctx = canvas.getContext('2d');
                if (!ctx) return {empty: true};
                // Sample pixels across the canvas to detect drawn content
                const w = canvas.width, h = canvas.height;
                let nonWhite = 0, total = 0;
                const colors = new Set();
                // Sample grid of points in the chart area (skip axes: left 10%, bottom 10%)
                const startX = Math.floor(w * 0.12);
                const endX = Math.floor(w * 0.88);
                const startY = Math.floor(h * 0.05);
                const endY = Math.floor(h * 0.85);
                const step = Math.max(4, Math.floor(Math.min(w, h) / 80));
                for (let x = startX; x < endX; x += step) {
                    for (let y = startY; y < endY; y += step) {
                        total++;
                        const px = ctx.getImageData(x, y, 1, 1).data;
                        const r = px[0], g = px[1], b = px[2], a = px[3];
                        // Skip near-white, near-black (axes), and transparent
                        if (a < 128) continue;
                        if (r > 240 && g > 240 && b > 240) continue;  // white bg
                        if (r < 30 && g < 30 && b < 30) continue;     // black axes/text
                        if (r > 200 && g > 200 && b > 200) continue;  // light gray grid
                        nonWhite++;
                        // Quantize color to detect distinct line colors
                        const cq = `${Math.round(r/32)*32}-${Math.round(g/32)*32}-${Math.round(b/32)*32}`;
                        colors.add(cq);
                    }
                }
                return {
                    empty: false,
                    total_sampled: total,
                    colored_pixels: nonWhite,
                    color_ratio: total > 0 ? nonWhite / total : 0,
                    distinct_colors: colors.size,
                    colors: [...colors].slice(0, 20),
                };
            }""")

            result["canvas_has_content"] = analysis.get("colored_pixels", 0) > 5
            result["line_colors_detected"] = analysis.get("distinct_colors", 0)

            if not result["canvas_has_content"]:
                result["issues"].append("canvas_empty_no_visible_lines")
                result["status"] = "FAIL"
            elif analysis.get("color_ratio", 0) < 0.001:
                result["issues"].append("very_sparse_rendering")
                result["status"] = "WARN"
            else:
                result["status"] = "OK"

        # Screenshot (always)
        safe_name = f"{source}_{ind_id}".replace("/", "_").replace("€", "EUR")
        ss_path = str(SCREENSHOTS_DIR / f"{safe_name}.png")
        try:
            # Screenshot just the chart area
            chart_el = page.query_selector("#exp-chart-wrap")
            if chart_el:
                chart_el.screenshot(path=ss_path)
            else:
                page.screenshot(path=ss_path, full_page=False)
            result["screenshot"] = ss_path
        except Exception:
            pass

    except Exception as e:
        result["status"] = "ERROR"
        result["issues"].append(str(e)[:200])
    finally:
        page.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate Prumo charts visually")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--resume", type=int, default=0)
    args = parser.parse_args()

    # Clear log
    open(LOG_FILE, "w").close()
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("PRUMO CHART VALIDATION — STARTING")
    log(f"Period: {DEFAULT_FROM} → {DEFAULT_TO}")
    log(f"Screenshots: {SCREENSHOTS_DIR}")
    log("=" * 60)

    indicators = fetch_indicators()
    log(f"Loaded {len(indicators)} indicators")

    # Load existing report for resume
    report = {}
    if args.resume > 0 and REPORT_FILE.exists():
        report = json.loads(REPORT_FILE.read_text())
    if "results" not in report:
        report["results"] = {}

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=args.headless,
            args=["--disable-quic"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="pt-PT",
        )

        total = len(indicators)
        ok = warn = fail = error = 0

        for i, ind in enumerate(indicators):
            if i < args.resume:
                continue

            key = f"{ind['source']}/{ind['id']}"

            # Skip if already validated OK
            if key in report["results"] and report["results"][key].get("status") == "OK":
                ok += 1
                continue

            log(f"[{i+1}/{total}] Validating: {key} — {ind['label']}")

            r = validate_chart(context, ind["source"], ind["id"], ind["label"])
            report["results"][key] = r

            if r["status"] == "OK":
                ok += 1
            elif r["status"] == "WARN":
                warn += 1
                log(f"  WARN: {r['issues']}", "WARN")
            elif r["status"] == "FAIL":
                fail += 1
                log(f"  FAIL: {r['issues']}", "ERROR")
            elif r["status"] == "TIMEOUT":
                fail += 1
                log(f"  TIMEOUT: {r['issues']}", "ERROR")
            else:
                error += 1
                log(f"  ERROR: {r['issues']}", "ERROR")

            # Save every 10
            if (i + 1) % 10 == 0:
                REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
                log(f"── Progress: {i+1}/{total} | OK={ok} WARN={warn} FAIL={fail} ERROR={error} ──")

        # Final save
        report["summary"] = {
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "ok": ok,
            "warn": warn,
            "fail": fail,
            "error": error,
            "issues_by_type": {},
        }

        # Aggregate issues
        issue_counts = {}
        for key, r in report["results"].items():
            for issue in r.get("issues", []):
                tag = issue.split(":")[0].strip()
                issue_counts[tag] = issue_counts.get(tag, 0) + 1
        report["summary"]["issues_by_type"] = issue_counts

        # List all non-OK indicators
        report["failures"] = [
            {"key": k, "status": v["status"], "issues": v["issues"]}
            for k, v in report["results"].items()
            if v["status"] not in ("OK",)
        ]

        REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))

        log("=" * 60)
        log(f"VALIDATION COMPLETE")
        log(f"OK={ok} WARN={warn} FAIL={fail} ERROR={error}")
        if report["failures"]:
            log(f"Issues ({len(report['failures'])}):")
            for f in report["failures"]:
                log(f"  {f['key']}: {f['status']} — {f['issues']}")
        log("=" * 60)

        browser.close()


if __name__ == "__main__":
    main()
