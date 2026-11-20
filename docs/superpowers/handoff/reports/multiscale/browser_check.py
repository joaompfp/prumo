#!/usr/bin/env python3
"""Multiscale chart browser acceptance harness.

Runs read-only against an already running Prumo server. It does not start, stop or
mutate anything. Every check is recorded in a JSON receipt; screenshot evidence is
written next to this file under browser/.

Usage:
  .venv-ci/bin/python docs/superpowers/handoff/reports/multiscale/browser_check.py \
      --base http://127.0.0.1:18137 \
      --output docs/superpowers/handoff/reports/multiscale/browser/receipt.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import traceback
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SIX = [
    "bportugal.euribor_3m.EA",
    "bportugal.euribor_12m.EA",
    "bportugal.pt_10y.PT",
    "ine.hicp_yoy.PT",
    "bportugal.credit_housing.PT",
    "bportugal.deposits_households.PT",
]
SPARSE = [
    "eurostat.gdp_per_capita_eur.PT",
    "ine.hicp_yoy.PT",
    "ine.unemployment_monthly.PT",
]
ONEGROUP = [
    "bportugal.euribor_3m.EA",
    "bportugal.euribor_12m.EA",
    "bportugal.pt_10y.PT",
]

FULL_WIDTHS = (390, 1440)
LIGHT_WIDTHS = (320, 768, 1920)

CSP_RE = re.compile(r"content security policy|refused to|blocked by CSP|cross-origin|CORS", re.I)


def caderno_url(base, ids, *, grafico=True, groups=True, escala="dupla",
                frequencia=None, janela="10a"):
    pairs = [("s", value) for value in ids]
    if grafico:
        pairs.append(("grafico", "on"))
    if groups:
        pairs.extend(("g", value) for value in ids)
    pairs.append(("escala", escala))
    pairs.append(("janela", janela))
    if frequencia:
        pairs.append(("frequencia", frequencia))
    return base.rstrip("/") + "/caderno?" + urllib.parse.urlencode(pairs)


def add(checks, name, ok, detail=None):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def axis_values(payload):
    """Axis per series. A legacy pair may omit axis; that is accepted on purpose."""
    axes = payload.get("axes") or []
    values = []
    for index, series in enumerate(payload.get("series") or []):
        value = series.get("axis") if isinstance(series, dict) else None
        if value is None:
            value = index if index < len(axes) else 0
        values.append(value)
    return values


def expected_tip_lines(payload, point):
    lines = []
    series = payload["series"]
    if series[0].get("badge"):
        lines.append(series[0]["badge"])
    lines.append(payload["periods"][point])
    for index, item in enumerate(series):
        if payload.get("version") == 2:
            period = payload["cell_periods"][point][index]
            display = payload["display"][point][index]
            if period is None or display is None:
                lines.append(item["title"] + " - " + payload["missing"])
            else:
                lines.append(item["title"] + " - " + period + ": " + display)
        else:
            lines.append(item["title"] + ": " + payload["display"][point][index])
    return lines


def expected_readout(payload, point):
    series = payload["series"]
    if payload.get("version") == 2:
        parts = []
        for index, item in enumerate(series):
            period = payload["cell_periods"][point][index]
            display = payload["display"][point][index]
            if period is None or display is None:
                parts.append(item["title"] + " - " + payload["missing"])
            else:
                parts.append(item["title"] + " - " + period + ": " + display)
        return payload["periods"][point] + " - " + "; ".join(parts)
    if len(series) == 1:
        return payload["periods"][point] + ": " + payload["display"][point][0]
    parts = [item["title"] + ": " + payload["display"][point][index]
             for index, item in enumerate(series)]
    return payload["periods"][point] + " - " + "; ".join(parts)


def inspect_payload(payload, expected_axes, checks, notes):
    if not isinstance(payload, dict):
        add(checks, "payload_json", False, "missing chart-data JSON")
        return
    add(checks, "payload_json", True, {"version": payload.get("version"),
                                       "kind": payload.get("kind")})
    series = payload.get("series") or []
    axes = payload.get("axes") or []
    add(checks, "series_count", len(series) == len(expected_axes),
        {"expected": len(expected_axes), "actual": len(series)})
    if not series or not axes:
        return
    expected_axis_values = [int(ch) for ch in expected_axes]
    actual_axis_values = axis_values(payload)
    add(checks, "axis_membership", actual_axis_values == expected_axis_values,
        {"expected": expected_axis_values, "actual": actual_axis_values,
         "series": [item.get("title") for item in series]})
    add(checks, "two_axes", len(axes) == 2, {"count": len(axes)})
    add(checks, "axes_used_once", set(actual_axis_values) == set(range(len(axes))),
        {"axes": len(axes), "used": sorted(set(actual_axis_values))})

    domain_ok = True
    domain_detail = []
    for index, item in enumerate(series):
        axis_index = actual_axis_values[index]
        if not (0 <= axis_index < len(axes)):
            domain_ok = False
            domain_detail.append({"series": item.get("title"), "axis": axis_index,
                                  "error": "axis out of range"})
            continue
        axis = axes[axis_index]
        low = min(float(axis["min"]), float(axis["max"]))
        high = max(float(axis["min"]), float(axis["max"]))
        slack = max(1e-9, abs(high - low) * 1e-9)
        native = [row[index] for row in payload.get("y") or []
                  if row[index] is not None]
        if not native:
            domain_ok = False
            domain_detail.append({"series": item.get("title"), "error": "no values"})
            continue
        outside = [value for value in native if value < low - slack or value > high + slack]
        if outside:
            domain_ok = False
        domain_detail.append({"series": item.get("title"), "axis": axis_index,
                              "domain": [axis["min"], axis["max"]],
                              "min": min(native), "max": max(native),
                              "outside": outside[:3]})
    add(checks, "domains_cover_native_values", domain_ok, domain_detail)

    xs = payload.get("x") or []
    x_ok = bool(xs) and payload.get("x_min") is not None and payload.get("x_max") is not None
    if x_ok:
        low = min(payload["x_min"], payload["x_max"])
        high = max(payload["x_min"], payload["x_max"])
        x_ok = low <= min(xs) and high >= max(xs)
    add(checks, "x_domain_contains_rows", x_ok,
        {"x_min": payload.get("x_min"), "x_max": payload.get("x_max"),
         "first": xs[0] if xs else None, "last": xs[-1] if xs else None,
         "rows": len(xs)})

    display = payload.get("display") or []
    ys = payload.get("y") or []
    if payload.get("version") == 2:
        display_ok = len(display) == len(xs) and len(ys) == len(xs)
        if display_ok:
            for index_row, shown in enumerate(display):
                values = ys[index_row]
                if len(shown) != len(series) or len(values) != len(series):
                    display_ok = False
                    break
                for value, text in zip(values, shown):
                    if value is None:
                        if text is not None:
                            display_ok = False
                    elif not (isinstance(text, str) and text):
                        display_ok = False
    else:
        display_ok = len(display) == len(xs) and all(
            isinstance(row, list) and len(row) == len(series)
            and all(isinstance(value, str) and value for value in row)
            for row in display)
    add(checks, "display_matrix", display_ok,
        {"rows": len(display), "columns": len(display[0]) if display else 0,
         "version": payload.get("version")})

    if payload.get("version") == 2:
        missing_ok = isinstance(payload.get("missing"), str) and bool(payload["missing"])
        cells = payload.get("cell_periods") or []
        cells_ok = len(cells) == len(xs)
        if cells_ok:
            for index_row, row in enumerate(cells):
                values = ys[index_row]
                shown = display[index_row]
                if len(row) != len(series) or len(shown) != len(series) or len(values) != len(series):
                    cells_ok = False
                    break
                for cell, text, value in zip(row, shown, values):
                    if value is None:
                        if cell is not None or text is not None:
                            cells_ok = False
                    elif not (isinstance(cell, str) and cell and isinstance(text, str) and text):
                        cells_ok = False
        add(checks, "calendar_missing_text", missing_ok, payload.get("missing"))
        add(checks, "calendar_cell_periods", cells_ok,
            {"rows": len(cells), "columns": len(cells[0]) if cells else 0})
        add(checks, "calendar_kind", payload.get("kind") == "calendar",
            payload.get("kind"))
    else:
        notes.append("v1 payload: missing/cell_periods checks do not apply")


def read_tip_lines(page):
    return page.eval_on_selector_all(
        ".chart-tip-line", "els => els.map(function (el) { return el.textContent; })")


def wait_for_readout(page, expected, timeout=3000):
    page.wait_for_function(
        "expected => (document.querySelector('.chart-readout') || {}).textContent === expected",
        arg=expected, timeout=timeout)


def wait_for_tips(page, expected, timeout=3000):
    page.wait_for_function(
        "expected => JSON.stringify(Array.from(document.querySelectorAll('.chart-tip-line'))"
        ".map(el => el.textContent)) === JSON.stringify(expected)",
        arg=expected, timeout=timeout)


def tooltip_neutral(page):
    return page.evaluate("""() => {
      const tip = document.querySelector('.chart-tooltip');
      if (!tip) return true;
      const style = getComputedStyle(tip);
      if (style.display === 'none' || style.visibility === 'hidden' ||
          Number(style.opacity) < 0.05) return true;
      const rect = tip.getBoundingClientRect();
      return rect.width === 0 || rect.height === 0 ||
        rect.right <= 0 || rect.bottom <= 0 ||
        rect.left >= window.innerWidth || rect.top >= window.innerHeight;
    }""")


def check_keyboard(page, payload, checks):
    count = len(payload.get("x") or [])
    if count < 2:
        add(checks, "range_controls", False, {"rows": count})
        return
    range_box = page.locator(".chart-range").first
    add(checks, "range_present", range_box.count() == 1, {"count": range_box.count()})
    if range_box.count() != 1:
        return
    add(checks, "range_visible", range_box.is_visible(), None)
    add(checks, "range_max", range_box.get_attribute("max") == str(count - 1),
        {"expected": str(count - 1), "actual": range_box.get_attribute("max")})
    range_box.focus()
    page.keyboard.press("Home")
    page.wait_for_timeout(160)
    home_readout = page.locator(".chart-readout").first.text_content()
    add(checks, "keyboard_home_readout", home_readout == expected_readout(payload, 0),
        {"expected": expected_readout(payload, 0), "actual": home_readout})
    home_tips = read_tip_lines(page)
    add(checks, "keyboard_home_tooltip", home_tips == expected_tip_lines(payload, 0),
        {"expected": expected_tip_lines(payload, 0), "actual": home_tips})
    page.keyboard.press("End")
    page.wait_for_timeout(160)
    last = count - 1
    end_readout = page.locator(".chart-readout").first.text_content()
    add(checks, "keyboard_end_readout", end_readout == expected_readout(payload, last),
        {"expected": expected_readout(payload, last), "actual": end_readout})
    end_tips = read_tip_lines(page)
    add(checks, "keyboard_end_tooltip", end_tips == expected_tip_lines(payload, last),
        {"expected": expected_tip_lines(payload, last), "actual": end_tips})
    mid = last // 2
    page.evaluate("""value => {
      const range = document.querySelector('.chart-range');
      range.value = String(value);
      range.dispatchEvent(new Event('input', {bubbles: true}));
    }""", mid)
    page.wait_for_timeout(160)
    mid_readout = page.locator(".chart-readout").first.text_content()
    add(checks, "mid_readout", mid_readout == expected_readout(payload, mid),
        {"expected": expected_readout(payload, mid), "actual": mid_readout})
    mid_tips = read_tip_lines(page)
    add(checks, "mid_tooltip", mid_tips == expected_tip_lines(payload, mid),
        {"expected": expected_tip_lines(payload, mid), "actual": mid_tips})


def ink_span(page):
    """Core test geometry: saturated series pixels in the canvas, not axis text or rules."""
    return page.evaluate("""() => {
      const stage = document.querySelector('.chart-canvas');
      const canvas = stage.querySelector('canvas');
      if (!canvas) return null;
      const ctx = canvas.getContext('2d', {willReadFrequently: true});
      const width = canvas.width;
      const height = canvas.height;
      const data = ctx.getImageData(0, 0, width, height).data;
      let min = null;
      let max = null;
      for (let x = 0; x < width; x += 1) {
        for (let y = 0; y < height; y += 1) {
          const i = (y * width + x) * 4;
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          const a = data[i + 3];
          const high = Math.max(r, g, b);
          const low = Math.min(r, g, b);
          if (a > 128 && high - low > 30) {
            if (min === null || x < min) min = x;
            if (max === null || x > max) max = x;
          }
        }
      }
      const rect = stage.getBoundingClientRect();
      return {min: min, max: max,
              box: {left: rect.left, top: rect.top,
                    width: rect.width, height: rect.height}};
    }""")


def pointer_probe(page, payload, checks, notes, points, label):
    count = len(payload["x"])
    page.locator(".chart-shell").scroll_into_view_if_needed()
    page.evaluate("""() => {
      const shell = document.querySelector('.chart-shell');
      const root = document.documentElement;
      const previous = root.style.scrollBehavior;
      root.style.scrollBehavior = 'auto';
      const top = shell.getBoundingClientRect().top + window.scrollY - 120;
      window.scrollTo(0, Math.max(0, top));
      root.style.scrollBehavior = previous;
    }""")
    page.wait_for_timeout(180)
    span = ink_span(page)
    if not span or span["min"] is None or span["max"] is None:
        add(checks, "pointer_geometry", False, {"error": "no saturated series pixels"})
        return
    add(checks, "pointer_geometry", True,
        {"ink_min": span["min"], "ink_max": span["max"]})
    box = span["box"]
    for name, index in points:
        if name == "mid":
            x = (span["min"] + span["max"]) / 2
        else:
            x = span["max"] - 1
        page.mouse.move(box["left"] + x, box["top"] + box["height"] / 2)
        page.wait_for_timeout(260)
        selected = int(page.locator(".chart-range").first.input_value())
        readout = page.locator(".chart-readout").first.text_content()
        add(checks, "pointer_" + name + "_selected", selected == index,
            {"expected": index, "actual": selected})
        add(checks, "pointer_" + name + "_readout",
            readout == expected_readout(payload, selected),
            {"index": selected, "expected": expected_readout(payload, selected),
             "actual": readout})
        tips = read_tip_lines(page)
        add(checks, "pointer_" + name + "_tooltip",
            tips == expected_tip_lines(payload, selected),
            {"index": selected, "expected": expected_tip_lines(payload, selected),
             "actual": tips})
    page.locator(".chart-canvas").dispatch_event("pointerleave")
    page.mouse.move(2, 2)
    page.wait_for_timeout(450)
    add(checks, "pointer_tooltip_hidden", tooltip_neutral(page), label)


def origin_issues(base, events):
    base_parts = urllib.parse.urlparse(base)
    bad = []
    for response in events["responses"]:
        parts = urllib.parse.urlparse(response["url"])
        if parts.scheme in ("http", "https") and parts.netloc != base_parts.netloc:
            bad.append(response)
    return bad


def console_issues(events):
    bad = []
    for item in events["console"]:
        if item["type"] == "error" and CSP_RE.search(item["text"]):
            bad.append(item)
    return bad


def fetch_bundle_manifest(page, base):
    srcs = page.evaluate(
        "Array.from(document.scripts).map(function (s) { return s.src; })"
        ".filter(function (src) { return !!src; })")
    base_parts = urllib.parse.urlparse(base)
    manifest = []
    for src in dict.fromkeys(srcs):
        parts = urllib.parse.urlparse(src)
        if parts.netloc != base_parts.netloc:
            continue
        try:
            request = urllib.request.Request(src, headers={"User-Agent": "prumo-browser-check"})
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read()
                manifest.append({"url": src, "status": response.status,
                                 "bytes": len(body),
                                 "sha256": hashlib.sha256(body).hexdigest()})
        except Exception as exc:  # recorded, never hidden
            manifest.append({"url": src, "error": repr(exc)})
    return manifest


def snapshot(page):
    return page.evaluate("""() => {
      const root = document.querySelector('.chart-shell[data-chart]');
      if (!root) return null;
      const data = root.querySelector('script.chart-data');
      let payload = null;
      try { payload = data ? JSON.parse(data.textContent) : null; } catch (error) { payload = null; }
      const legend = Array.from(root.querySelectorAll('ul.legend > li'));
      return {
        payload: payload,
        enhanced: root.classList.contains('chart-enhanced'),
        readout: (root.querySelector('.chart-readout') || {}).textContent || '',
        rangeValue: (root.querySelector('.chart-range') || {}).value || null,
        rangeHidden: (root.querySelector('.chart-range') || {}).hidden,
        rangeMax: (root.querySelector('.chart-range') || {}).max || null,
        legendAxes: legend.map(function (item) { return item.getAttribute('data-axis'); }),
        legendCount: legend.length,
        svgRoleImg: root.querySelectorAll('svg[role="img"]').length,
        svgPathCount: root.querySelectorAll('svg.chart-compare path.chart-line').length,
        tableRows: document.querySelectorAll(
          '.notebook-table-scroll > table > tbody > tr').length,
        canvasChildren: root.querySelector('.chart-canvas')
          ? root.querySelector('.chart-canvas').childElementCount : -1,
        shellWidth: root.getBoundingClientRect().width,
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        scrollY: window.scrollY
      };
    }""")


def finalize(page, path, checks):
    page.evaluate("window.scrollTo(0, 0)")
    try:
        page.wait_for_function("() => document.fonts.status === 'loaded'", timeout=4000)
    except Exception:
        pass
    page.wait_for_timeout(120)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(80)
    scroll_y = page.evaluate("window.scrollY")
    add(checks, "screenshot_scroll_zero", scroll_y == 0, {"scrollY": scroll_y})
    page.locator(".chart-canvas").dispatch_event("pointerleave")
    page.mouse.move(2, 2)
    page.wait_for_timeout(450)
    page.screenshot(path=str(path), full_page=False)


def run_full_case(browser, base, case, width, screenshot_dir, take_shot, deadline):
    result = {"case": case["name"], "width": width, "kind": case["type"],
              "status": "failed", "checks": [], "notes": [], "url": None,
              "screenshot": None, "duration_s": None}
    checks = result["checks"]
    if time.time() > deadline:
        result["status"] = "skipped"
        result["notes"].append("timeout budget reached before case")
        return result
    started = time.time()
    context = browser.new_context(viewport={"width": width, "height": 900},
                                  device_scale_factor=1)
    page = context.new_page()
    page.set_default_timeout(9000)
    events = {"console": [], "pageerrors": [], "responses": [], "failed": []}
    page.on("console", lambda msg: events["console"].append(
        {"type": msg.type, "text": msg.text}))
    page.on("pageerror", lambda error: events["pageerrors"].append(str(error)))
    page.on("response", lambda response: events["responses"].append(
        {"url": response.url, "status": response.status}))
    page.on("requestfailed", lambda request: events["failed"].append(
        {"url": request.url, "failure": request.failure}))
    try:
        url = case["url"]
        result["url"] = url
        response = page.goto(url, wait_until="load", timeout=20000)
        add(checks, "http_200", bool(response) and response.status == 200,
            response.status if response else None)
        page.wait_for_selector(".chart-shell", timeout=9000)
        page.wait_for_selector(".chart-shell.chart-enhanced", timeout=9000)
        add(checks, "chart_enhanced", True, None)
        state = snapshot(page)
        if not state or not state.get("payload"):
            add(checks, "payload_json", False, "chart-data missing")
            raise RuntimeError("chart-data missing")
        payload = state["payload"]
        result["payload_summary"] = {
            "version": payload.get("version"), "kind": payload.get("kind"),
            "series": [item.get("title") for item in payload.get("series") or []],
            "axes": [{"unit": a.get("unit"), "min": a.get("min"), "max": a.get("max")}
                     for a in payload.get("axes") or []],
            "rows": len(payload.get("x") or []),
            "periods_first_last": [payload["periods"][0], payload["periods"][-1]]
            if payload.get("periods") else None,
            "missing": payload.get("missing"),
            "series_frequency": [item.get("frequency")
                                 for item in payload.get("series") or []],
        }
        inspect_payload(payload, case["axes"], checks, result["notes"])
        add(checks, "table_rows_match_payload", state["tableRows"] == len(payload["x"]),
            {"table": state["tableRows"], "payload_x": len(payload["x"])})
        version = payload.get("version")
        if version == 1:
            add(checks, "legend_series_count", state["legendCount"] == len(payload["series"]),
                {"legend": state["legendCount"], "series": len(payload["series"])})
            add(checks, "legend_axis_membership",
                "".join(str(value) for value in state["legendAxes"]) == case["axes"],
                {"expected": case["axes"], "actual": state["legendAxes"]})
            add(checks, "svg_series_paths", state["svgPathCount"] == len(payload["series"]),
                {"paths": state["svgPathCount"], "series": len(payload["series"])})
        else:
            allowed = {str(value) for value in axis_values(payload)}
            actual = [str(value) for value in state["legendAxes"] if value is not None]
            add(checks, "legend_axis_membership",
                all(value in allowed for value in actual) and 0 < state["legendCount"] <= len(payload["series"]),
                {"allowed": sorted(allowed), "actual": state["legendAxes"],
                 "legend": state["legendCount"], "series": len(payload["series"])})
            add(checks, "svg_role_img", state["svgRoleImg"] == 1,
                {"count": state["svgRoleImg"]})
        check_keyboard(page, payload, checks)
        if case["name"] == "six":
            row_count = len(payload["x"])
            pointer_probe(page, payload, checks, result["notes"],
                          [("mid", (row_count - 1) // 2), ("last", row_count - 1)],
                          "six")

        # Calendar annual case: the payload may stay v1. Verify the annual aggregation itself.
        if case.get("annual"):
            periods = payload.get("periods") or []
            years_ok = bool(periods) and all(re.fullmatch(r"\d{4}", str(value)) for value in periods)
            add(checks, "annual_periods_are_years", years_ok,
                {"first": periods[0] if periods else None,
                 "last": periods[-1] if periods else None,
                 "rows": len(periods)})
            frequencies = [item.get("frequency") for item in payload["series"]]
            if all(frequencies):
                lower = [str(value).lower() for value in frequencies]
                add(checks, "annual_frequencies", all("anual" in value or value == "a" for value in lower),
                    {"frequencies": frequencies})
            else:
                result["notes"].append("annual case payload v1: frequency not exposed; "
                                       "annual periods assert the aggregation")

        csp = console_issues(events)
        off_origin = origin_issues(base, events)
        http_errors = [item for item in events["responses"]
                       if item["status"] >= 400 and not item["url"].endswith("favicon.ico")]
        add(checks, "no_csp_console_errors", not csp, csp[:3])
        add(checks, "no_off_origin_requests", not off_origin, off_origin[:3])
        add(checks, "no_page_errors", not events["pageerrors"], events["pageerrors"][:3])
        add(checks, "no_http_errors", not http_errors, http_errors[:3])

        if take_shot:
            slug = urllib.parse.urlparse(base).netloc.replace(":", "_")
            name = case["name"].replace("/", "_")
            path = screenshot_dir / f"{slug}_{name}_{width}.png"
            finalize(page, path, checks)
            result["screenshot"] = str(path)
            add(checks, "neutral_after_pointerleave", tooltip_neutral(page),
                {"scrollY": page.evaluate("window.scrollY")})
        result["status"] = "passed" if all(item["ok"] for item in checks) else "failed"
    except Exception as exc:
        add(checks, "case_completed", False,
            {"error": repr(exc), "trace": traceback.format_exc().splitlines()[-3:]})
        result["status"] = "failed"
    finally:
        result["duration_s"] = round(time.time() - started, 2)
        result["console_errors"] = [item for item in events["console"]
                                    if item["type"] == "error"][:10]
        result["page_errors"] = events["pageerrors"][:5]
        result["failed_requests"] = events["failed"][:5]
        try:
            if result["status"] != "passed" and result["screenshot"] is None:
                slug = urllib.parse.urlparse(base).netloc.replace(":", "_")
                path = screenshot_dir / f"{slug}_{case['name']}_failure_{width}.png"
                page.screenshot(path=str(path), full_page=False)
                result["screenshot"] = str(path)
        except Exception:
            pass
        context.close()
    return result


def run_light_case(browser, base, case, width, deadline):
    result = {"case": case["name"] + "_light", "width": width, "kind": "light",
              "status": "failed", "checks": [], "notes": [], "url": case["url"],
              "screenshot": None, "duration_s": None}
    checks = result["checks"]
    if time.time() > deadline:
        result["status"] = "skipped"
        result["notes"].append("timeout budget reached before case")
        return result
    started = time.time()
    context = browser.new_context(viewport={"width": width, "height": 900},
                                  device_scale_factor=1)
    page = context.new_page()
    page.set_default_timeout(9000)
    events = {"console": [], "pageerrors": [], "responses": [], "failed": []}
    page.on("console", lambda msg: events["console"].append(
        {"type": msg.type, "text": msg.text}))
    page.on("pageerror", lambda error: events["pageerrors"].append(str(error)))
    page.on("response", lambda response: events["responses"].append(
        {"url": response.url, "status": response.status}))
    try:
        page.goto(case["url"], wait_until="load", timeout=20000)
        page.wait_for_selector(".chart-shell.chart-enhanced", timeout=9000)
        state = snapshot(page)
        add(checks, "chart_enhanced", bool(state and state["enhanced"]), None)
        add(checks, "page_no_horizontal_overflow",
            bool(state) and state["scrollWidth"] <= state["innerWidth"] + 1,
            {"scrollWidth": state["scrollWidth"] if state else None,
             "innerWidth": state["innerWidth"] if state else None})
        add(checks, "shell_within_viewport",
            bool(state) and state["shellWidth"] <= state["innerWidth"] + 1,
            {"shellWidth": state["shellWidth"] if state else None,
             "innerWidth": state["innerWidth"] if state else None})
        add(checks, "readout_present", bool(state and state["readout"]), None)
        add(checks, "no_csp_console_errors", not console_issues(events), console_issues(events)[:3])
        add(checks, "no_off_origin_requests", not origin_issues(base, events),
            origin_issues(base, events)[:3])
        add(checks, "no_page_errors", not events["pageerrors"], events["pageerrors"][:3])
        result["status"] = "passed" if all(item["ok"] for item in checks) else "failed"
    except Exception as exc:
        add(checks, "case_completed", False, repr(exc))
        result["status"] = "failed"
    finally:
        result["duration_s"] = round(time.time() - started, 2)
        result["console_errors"] = [item for item in events["console"]
                                    if item["type"] == "error"][:10]
        context.close()
    return result


def run_nojs(browser, base, deadline):
    url = caderno_url(base, ONEGROUP, escala="comum")
    result = {"case": "nojs_onegroup", "width": 390, "kind": "nojs",
              "status": "failed", "checks": [], "notes": [], "url": url,
              "screenshot": None, "duration_s": None}
    checks = result["checks"]
    if time.time() > deadline:
        result["status"] = "skipped"
        result["notes"].append("timeout budget reached before case")
        return result
    started = time.time()
    context = browser.new_context(viewport={"width": 390, "height": 900},
                                  java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(url, wait_until="load", timeout=20000)
        state = snapshot(page)
        add(checks, "shell_present", bool(state), None)
        add(checks, "not_enhanced", bool(state) and not state["enhanced"], None)
        svg_count = page.locator("svg.chart").count()
        add(checks, "svg_fallback_present", svg_count >= 1, {"count": svg_count})
        add(checks, "canvas_empty", bool(state) and state["canvasChildren"] == 0,
            {"children": state["canvasChildren"] if state else None})
        add(checks, "readout_empty", bool(state) and state["readout"] == "",
            {"readout": state["readout"] if state else None})
        add(checks, "range_hidden", bool(state) and state["rangeHidden"] is True,
            {"hidden": state["rangeHidden"] if state else None})
        result["status"] = "passed" if all(item["ok"] for item in checks) else "failed"
    except Exception as exc:
        add(checks, "case_completed", False, repr(exc))
        result["status"] = "failed"
    finally:
        result["duration_s"] = round(time.time() - started, 2)
        context.close()
    return result


def run_print(browser, base, deadline):
    url = caderno_url(base, ONEGROUP, escala="comum")
    result = {"case": "print_svg", "width": 1440, "kind": "print",
              "status": "failed", "checks": [], "notes": [], "url": url,
              "screenshot": None, "duration_s": None}
    checks = result["checks"]
    if time.time() > deadline:
        result["status"] = "skipped"
        result["notes"].append("timeout budget reached before case")
        return result
    started = time.time()
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.set_default_timeout(9000)
    try:
        page.goto(url, wait_until="load", timeout=20000)
        page.wait_for_selector(".chart-shell.chart-enhanced", timeout=9000)
        page.emulate_media(media="print")
        page.wait_for_timeout(150)
        styles = page.evaluate("""() => {
          const svg = document.querySelector('.chart-shell svg.chart');
          const canvas = document.querySelector('.chart-shell .chart-canvas');
          const controls = document.querySelector('.chart-shell .chart-controls');
          return {
            svgOpacity: svg ? getComputedStyle(svg).opacity : null,
            svgDisplay: svg ? getComputedStyle(svg).display : null,
            canvasDisplay: canvas ? getComputedStyle(canvas).display : null,
            controlsDisplay: controls ? getComputedStyle(controls).display : null
          };
        }""")
        add(checks, "print_svg_visible", styles["svgOpacity"] == "1",
            styles)
        add(checks, "print_canvas_hidden", styles["canvasDisplay"] == "none", styles)
        add(checks, "print_controls_hidden", styles["controlsDisplay"] == "none", styles)
        result["status"] = "passed" if all(item["ok"] for item in checks) else "failed"
    except Exception as exc:
        add(checks, "case_completed", False, repr(exc))
        result["status"] = "failed"
    finally:
        result["duration_s"] = round(time.time() - started, 2)
        context.close()
    return result


def resolve_compare_links(browser, base, deadline):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    errors = []
    try:
        for path in ("/comparar", "/comparar3cards"):
            try:
                response = page.goto(base.rstrip("/") + path,
                                     wait_until="load", timeout=20000)
            except Exception as exc:
                errors.append({"path": path, "error": repr(exc)})
                continue
            if not response or response.status != 200:
                errors.append({"path": path, "status":
                               response.status if response else None})
                continue
            hrefs = page.evaluate(
                "Array.from(document.querySelectorAll('a'))"
                ".filter(function (a) { return a.textContent.indexOf('Abrir no Caderno') !== -1; })"
                ".map(function (a) { return a.href; })")
            unique = list(dict.fromkeys(hrefs))
            if len(unique) >= 3:
                return unique[:3], None, path
            errors.append({"path": path, "error": "fewer than three links",
                           "hrefs": unique})
        return [], {"error": "no comparison page with three links", "tried": errors}, None
    except Exception as exc:
        return [], {"error": repr(exc)}, None
    finally:
        context.close()


def build_cases(base, link_urls):
    cases = []
    for index, url in enumerate(link_urls[:3]):
        cases.append({"name": f"comparar3_link{index}",
                      "type": "compare_link",
                      "url": url,
                      "axes": "0011" if index == 0 else "001"})
    cases.append({"name": "six", "type": "six",
                  "url": caderno_url(base, SIX), "axes": "000011"})
    cases.append({"name": "sparse", "type": "sparse",
                  "url": caderno_url(base, SPARSE), "axes": "011"})
    cases.append({"name": "sparse_annual", "type": "sparse",
                  "url": caderno_url(base, SPARSE, frequencia="anual"),
                  "axes": "011", "annual": True})
    cases.append({"name": "implicit_all", "type": "implicit",
                  "url": caderno_url(base, SIX, grafico=False, groups=False),
                  "axes": "000011"})
    return cases


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prumo multiscale browser acceptance")
    parser.add_argument("--base", action="append", default=[],
                        help="server base URL; repeat for more servers")
    parser.add_argument("--output", default=None,
                        help="JSON receipt path")
    parser.add_argument("--timeout", type=int, default=230,
                        help="soft wall clock budget in seconds")
    args = parser.parse_args(argv)
    bases = list(dict.fromkeys(args.base or ["http://127.0.0.1:18137"]))
    output = Path(args.output) if args.output else (
        Path(__file__).resolve().parent / "browser" / "receipt.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir = output.parent
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + max(10, args.timeout)

    started = time.time()
    receipt = {"tool": "multiscale browser acceptance",
               "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "bases": bases,
               "scope": {
                   "full_widths": list(FULL_WIDTHS),
                   "light_widths": list(LIGHT_WIDTHS),
                   "full_cases": ["comparar3_link0..2", "six", "sparse",
                                  "sparse_annual", "implicit_all"],
                   "light_cases": ["six"],
                   "pointer_probe": "six, mid and last, full widths",
                   "nojs_print": "onegroup comum at 390 and print at 1440",
                   "limits": ["read-only HTTP GET only",
                              "no server start or stop",
                              "no DB or CMS write",
                              "comparison links sourced from /comparar; /comparar3cards returns 404 on this server",
                              "calendar legend membership checked against payload on v2",
                              "pointer geometry uses the core test canvas saturated-series span, not SVG coordinates",
                              "pointer last tooltip not asserted; pointer last readout and keyboard End tooltip are exact"],
               },
               "results": [], "bundle_manifest": [], "fatal": None}

    try:
        from tests.app.test_chart_layout import _chromium
        executable = _chromium()
    except Exception as exc:
        receipt["fatal"] = "chromium lookup failed: " + repr(exc)
        receipt["summary"] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
        print("FATAL:", receipt["fatal"])
        print("receipt:", output)
        return 2

    if not executable:
        receipt["fatal"] = "no Chromium executable found by tests.app.test_chart_layout._chromium"
        receipt["summary"] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
        print("FATAL:", receipt["fatal"])
        print("receipt:", output)
        return 2

    receipt["chromium"] = executable
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True,
                                            args=["--no-sandbox", "--disable-dev-shm-usage"])
        for base in bases:
            base_started = time.time()
            link_urls, link_error, compare_source = resolve_compare_links(
                browser, base, deadline)
            if link_error:
                receipt.setdefault("base_errors", []).append({"base": base, **link_error})
            if compare_source:
                receipt.setdefault("compare_sources", []).append(
                    {"base": base, "path": compare_source})
            cases = build_cases(base, link_urls)
            for case in cases:
                for width in FULL_WIDTHS:
                    result = run_full_case(browser, base, case, width, screenshot_dir,
                                           case["name"] in ("six", "comparar3_link0"),
                                           deadline)
                    result["base"] = base
                    receipt["results"].append(result)
            if time.time() <= deadline:
                light_case = next(item for item in cases if item["name"] == "six")
                for width in LIGHT_WIDTHS:
                    result = run_light_case(browser, base, light_case, width, deadline)
                    result["base"] = base
                    receipt["results"].append(result)
            if time.time() <= deadline:
                result = run_nojs(browser, base, deadline)
                result["base"] = base
                receipt["results"].append(result)
            if time.time() <= deadline:
                result = run_print(browser, base, deadline)
                result["base"] = base
                receipt["results"].append(result)
            if not receipt["bundle_manifest"]:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                try:
                    page.goto(caderno_url(base, SIX), wait_until="load", timeout=20000)
                    page.wait_for_selector(".chart-shell.chart-enhanced", timeout=9000)
                    receipt["bundle_manifest"] = fetch_bundle_manifest(page, base)
                except Exception as exc:
                    receipt["bundle_manifest"] = [{"error": repr(exc), "base": base}]
                finally:
                    context.close()
            receipt.setdefault("base_durations", []).append(
                {"base": base, "seconds": round(time.time() - base_started, 2)})
        browser.close()

    total = len(receipt["results"])
    passed = sum(1 for item in receipt["results"] if item["status"] == "passed")
    failed = sum(1 for item in receipt["results"] if item["status"] == "failed")
    skipped = sum(1 for item in receipt["results"] if item["status"] == "skipped")
    receipt["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    receipt["duration_s"] = round(time.time() - started, 2)
    receipt["summary"] = {"total": total, "passed": passed, "failed": failed,
                          "skipped": skipped}
    output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

    print("results: {}/{} passed, {} failed, {} skipped".format(
        passed, total, failed, skipped))
    for item in receipt["results"]:
        if item["status"] != "passed":
            failed_checks = [check["name"] for check in item["checks"] if not check["ok"]]
            print("{} {} @{}: {} {}".format(
                item["status"].upper(), item["case"], item["width"],
                ", ".join(failed_checks) or "no failed checks", item["url"]))
    print("receipt:", output)
    print("screenshots:", screenshot_dir)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
