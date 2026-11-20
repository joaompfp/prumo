#!/usr/bin/env python3
"""Real-copy browser acceptance for notebook time transformations.

The harness is read-only. It drives the installed application over HTTP, checks the
real rendered pages and the exact JSON payload against the served observations in a
SQLite copy, and fingerprints every database table before and after the run.

Usage:
    .venv-ci/bin/python docs/superpowers/handoff/reports/time-transformations/run_browser_acceptance.py \
        --base http://127.0.0.1:8197 \
        --db /home/joao/.hermes/cache/scratch/prumo-time-transformations/acceptance.sqlite3

The same command is reusable after deployment by changing --base and --db. The local
mount proxy is started automatically and forwards X-Forwarded-Prefix: /dados. Use
--no-proxy to skip the mounted-prefix half of the matrix.

Exit status is 0 only when every functional check and every matrix cell passes.
A failed run still writes receipt.json and receipt.md, with the exact failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent
REPO = REPORT_DIR.parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.formatting import format_value  # noqa: E402
from presentation import base_unit_text  # noqa: E402

WIDTHS = (320, 390, 768, 1440, 1920)
VIEWPORT_HEIGHT = 900
PREFIX = "/dados"
HICP = "ine.hicp_yoy.PT"
WORLD_GDP = "worldbank.gdp_per_capita.PT"
EURO_GDP = "eurostat.gdp_per_capita_eur.PT"
EURO_GDP_ES = "eurostat.gdp_per_capita_eur.ES"
UNEMP = "ine.unemployment_monthly.PT"
SIX_GDP = (EURO_GDP, EURO_GDP_ES,
           "eurostat.gdp_per_capita_eur.DE",
           "eurostat.gdp_per_capita_eur.FR",
           "eurostat.gdp_per_capita_eur.IT",
           "eurostat.gdp_per_capita_eur.NL")

CSP_BASE = "default-src 'none'"
CSP_SCRIPT = "script-src 'self'"


def query(*pairs: tuple[str, str]) -> str:
    return "/caderno?" + urllib.parse.urlencode(list(pairs))


MIXED_WB = query(("s", HICP), ("s", WORLD_GDP), ("escala", "dupla"))
MIXED_EURO = query(("s", HICP), ("s", EURO_GDP), ("escala", "dupla"))
ANNUAL = query(("s", HICP), ("s", EURO_GDP), ("frequencia", "anual"), ("escala", "dupla"))
BASE100 = query(("s", EURO_GDP), ("s", EURO_GDP_ES), ("frequencia", "anual"),
                ("transformacao", "base100"), ("escala", "comum"), ("base", "2015"))
BASE100_SIX = query(*[("s", sid) for sid in SIX_GDP],
                    ("frequencia", "anual"), ("transformacao", "base100"),
                    ("escala", "comum"), ("base", "2015"))
PP = query(("s", HICP), ("s", UNEMP), ("frequencia", "anual"),
           ("transformacao", "pp"), ("base", "2015"))
WRONG_BASE = query(("s", EURO_GDP), ("s", EURO_GDP_ES), ("frequencia", "anual"),
                   ("transformacao", "base100"), ("base", "1900"))
RATE_BASE100 = query(("s", HICP), ("s", UNEMP), ("frequencia", "anual"),
                     ("transformacao", "base100"), ("base", "2015"))
INTERVAL_MIX = query(("s", HICP), ("s", "eredes.production_total.PT"), ("escala", "dupla"))
EMPTY = query(("s", HICP), ("s", EURO_GDP), ("grafico", "on"))
OFF = query(("s", HICP), ("s", EURO_GDP), ("grafico", "off"))


CASES = (
    {"id": "mixed_ihpc_worldbank", "path": MIXED_WB, "state": "ready",
     "version": 2, "kind": "calendar", "cards": 2, "evidence": False,
     "screenshot": "pib-per-capita-mixed"},
    {"id": "mixed_ihpc_eurostat", "path": MIXED_EURO, "state": "ready",
     "version": 2, "kind": "calendar", "cards": 2, "evidence": False},
    {"id": "annual_ihpc_eurostat", "path": ANNUAL, "state": "ready",
     "version": 1, "kind": "comparison", "cards": 2, "evidence": True,
     "screenshot": "annual-hicp-gdp"},
    {"id": "base100_gdp_pt_es", "path": BASE100, "state": "ready",
     "version": 1, "kind": "comparison", "cards": 2, "evidence": True,
     "screenshot": "base100-gdp-pt-es"},
    {"id": "base100_six_gdp", "path": BASE100_SIX, "state": "ready",
     "version": 1, "kind": "group", "cards": 6, "evidence": True},
    {"id": "pp_ihpc_unemployment", "path": PP, "state": "ready",
     "version": 1, "kind": "comparison", "cards": 2, "evidence": True,
     "screenshot": "pp-hicp-unemployment"},
    {"id": "wrong_base", "path": WRONG_BASE, "state": "unavailable",
     "reason": "O ano de base escolhido não existe em todas as séries escolhidas.",
     "cards": 2},
    {"id": "rate_base100", "path": RATE_BASE100, "state": "unavailable",
     "reason": "O índice base 100 só está definido para séries de nível revistas",
     "cards": 2},
    {"id": "interval_mix", "path": INTERVAL_MIX, "state": "unavailable",
     "reason": "As séries de intervalos de 15 minutos só podem ser comparadas entre si",
     "cards": 2},
    {"id": "empty_group", "path": EMPTY, "state": "empty",
     "reason": "Não há séries escolhidas para o gráfico.", "cards": 2},
    {"id": "off", "path": OFF, "state": "off",
     "reason": "O gráfico está desativado nesta ligação.", "cards": 2},
)


# ---------------------------------------------------------------------------
# Local mount proxy


class _PrefixProxy:
    """Forward requests to --base and preserve the public mount prefix.

    The app derives its public links from X-Forwarded-Prefix. The handler also records
    that the header arrived, so the browser half of the matrix is not trusted alone.
    """

    def __init__(self, upstream: str):
        parsed = urllib.parse.urlsplit(upstream)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"unsupported base URL: {upstream!r}")
        path = parsed.path.rstrip("/")
        if path.endswith(PREFIX):
            path = path[: -len(PREFIX)]
        self.scheme = parsed.scheme
        self.netloc = parsed.netloc
        self.base_path = path
        self.upstream = f"{parsed.scheme}://{parsed.netloc}{path}"
        self.seen: list[dict] = []
        self.lock = threading.Lock()
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def _serve(self):
                parsed = urllib.parse.urlsplit(self.path)
                if not parsed.path.startswith(PREFIX):
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                mapped = parsed.path[len(PREFIX):] or "/"
                target = proxy.upstream + mapped
                if parsed.query:
                    target += "?" + parsed.query
                headers = {
                    "Accept": self.headers.get("Accept", "*/*"),
                    "Accept-Language": self.headers.get("Accept-Language", "pt-PT,pt;q=0.9"),
                    "User-Agent": self.headers.get("User-Agent", "prumo-acceptance"),
                    "X-Forwarded-Prefix": PREFIX,
                }
                request = urllib.request.Request(target, headers=headers, method=self.command)
                status = 502
                body = b""
                response_headers = []
                try:
                    with urllib.request.urlopen(request, timeout=30) as upstream:
                        status = upstream.status
                        body = upstream.read()
                        response_headers = list(upstream.headers.items())
                except urllib.error.HTTPError as exc:
                    status = exc.code
                    body = exc.read()
                    response_headers = list(exc.headers.items())
                except Exception as exc:  # noqa: BLE001 - reported as a proxy failure
                    body = f"proxy failure: {exc}".encode("utf-8")
                with proxy.lock:
                    proxy.seen.append({"path": self.path, "mapped": target,
                                       "prefix": headers["X-Forwarded-Prefix"],
                                       "status": status})
                self.send_response(status)
                for name, value in response_headers:
                    if name.lower() in {"connection", "transfer-encoding", "content-encoding",
                                        "content-length", "keep-alive"}:
                        continue
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            do_GET = _serve
            do_HEAD = _serve

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def port(self) -> int:
        return self.httpd.server_address[1]

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{PREFIX}{path}"


# ---------------------------------------------------------------------------
# Read-only data access


def _parse_start(period: str, frequency: str) -> date | None:
    if frequency == "A":
        if re.fullmatch(r"\d{4}", period):
            return date(int(period), 1, 1)
        return None
    if frequency == "M":
        match = re.fullmatch(r"(\d{4})-(\d{2})", period)
        if match:
            return date(int(match.group(1)), int(match.group(2)), 1)
        return None
    if frequency == "Q":
        match = re.fullmatch(r"(\d{4})-Q([1-4])", period)
        if match:
            return date(int(match.group(1)), (int(match.group(2)) - 1) * 3 + 1, 1)
        return None
    if frequency == "S":
        match = re.fullmatch(r"(\d{4})-S([12])", period)
        if match:
            return date(int(match.group(1)), 1 if match.group(2) == "1" else 7, 1)
        return None
    if frequency == "D":
        try:
            return date.fromisoformat(period[:10])
        except ValueError:
            return None
    return None


def _month_index(period: str) -> int | None:
    match = re.fullmatch(r"(\d{4})-(\d{2})", period)
    if not match or not 1 <= int(match.group(2)) <= 12:
        return None
    return int(match.group(1)) * 12 + int(match.group(2)) - 1


def _fmt_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." not in text:
        text += ".000000"
    return text


def _round_fraction(value: Fraction) -> str:
    """Half-even to six decimal places using exact integer arithmetic."""
    scaled = value * 1_000_000
    sign = -1 if scaled < 0 else 1
    numerator = abs(scaled.numerator)
    denominator = scaled.denominator
    quotient, remainder = divmod(numerator, denominator)
    if 2 * remainder > denominator or (2 * remainder == denominator and quotient % 2 == 1):
        quotient += 1
    whole, fraction = divmod(quotient, 1_000_000)
    text = f"{whole}.{fraction:06d}"
    return ("-" if sign < 0 and quotient else "") + text


def _mean(values: list[str]) -> Decimal:
    total = sum(Decimal(token) for token in values)
    return (total / Decimal(len(values))).quantize(Decimal("0.000001"),
                                                   rounding=ROUND_HALF_EVEN)


def _is_number(token: str) -> bool:
    try:
        Decimal(token)
        return True
    except Exception:  # noqa: BLE001 - any non-numeric token is not finite
        return False


class Data:
    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        self._cache: dict[str, dict] = {}

    def close(self) -> None:
        self.conn.close()

    def series(self, series_id: str) -> dict:
        if series_id in self._cache:
            return self._cache[series_id]
        meta = self.conn.execute(
            "SELECT id, frequency, unit, seasonal_adjustment FROM series WHERE id = ?",
            (series_id,)).fetchone()
        if meta is None:
            raise KeyError(f"unknown series {series_id}")
        rows = self.conn.execute(
            "SELECT period, value_text, status_flag, fetched_at, dataset_run_id "
            "FROM served_observation WHERE series_id = ? ORDER BY period",
            (series_id,)).fetchall()
        by_period = {row["period"]: dict(row) for row in rows}
        if len(by_period) != len(rows):
            raise AssertionError(f"served_observation has duplicate periods for {series_id}")
        starts = {}
        for period, row in by_period.items():
            start = _parse_start(period, meta["frequency"])
            if start is not None:
                starts[start] = (period, row)
        entry = {"meta": dict(meta), "rows": rows, "by_period": by_period,
                 "starts": starts}
        self._cache[series_id] = entry
        return entry

    def latest(self, series_id: str) -> tuple[str, dict]:
        rows = self.series(series_id)["rows"]
        if not rows:
            raise AssertionError(f"no served observations for {series_id}")
        row = rows[-1]
        return row["period"], dict(row)

    def complete_annual(self, series_id: str) -> dict[str, str]:
        """Complete annual outputs from the same family policies used in the cases.

        Native annual series use their stored token. Monthly HICP, unemployment and Euro
        area rates use the arithmetic mean of twelve finite months. The caller only asks
        this of those two reviewed families.
        """
        entry = self.series(series_id)
        frequency = entry["meta"]["frequency"]
        if frequency == "A":
            return {period: row["value_text"] for period, row in entry["by_period"].items()
                    if _is_number(row["value_text"])}
        if frequency != "M":
            raise AssertionError(f"no annual policy helper for {series_id} ({frequency})")
        months: dict[int, dict[int, str]] = {}
        for period, row in entry["by_period"].items():
            index = _month_index(period)
            if index is None or not _is_number(row["value_text"]):
                continue
            year, month = divmod(index, 12)
            months.setdefault(year, {})[month + 1] = row["value_text"]
        out = {}
        for year, values in months.items():
            if set(values) == set(range(1, 13)):
                out[str(year)] = _fmt_decimal(_mean([values[m] for m in range(1, 13)]))
        return out


def table_fingerprints(path: Path) -> dict:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        schema = conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall()
        schema_hash = hashlib.sha256(json.dumps(schema, ensure_ascii=False).encode()).hexdigest()
        tables = []
        for (name, sql) in conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
            digest = hashlib.sha256()
            digest.update((sql or "").encode("utf-8"))
            count = 0
            without_rowid = "WITHOUT ROWID" in (sql or "").upper()
            statement = f'SELECT * FROM "{name}"'
            if not without_rowid:
                statement += " ORDER BY rowid"
            try:
                rows = conn.execute(statement)
            except sqlite3.OperationalError:
                rows = conn.execute(f'SELECT * FROM "{name}"')
            for row in rows:
                digest.update(json.dumps(row, ensure_ascii=False, default=repr).encode("utf-8"))
                digest.update(b"\n")
                count += 1
            tables.append({"name": name, "rows": count, "sha256": digest.hexdigest()})
        overall = hashlib.sha256()
        for table in tables:
            overall.update(f"{table['name']}:{table['sha256']}\n".encode())
        return {
            "schema_sha256": schema_hash,
            "tables": tables,
            "table_count": len(tables),
            "row_count": sum(table["rows"] for table in tables),
            "overall_sha256": overall.hexdigest(),
            "integrity_check": [row[0] for row in conn.execute("PRAGMA integrity_check")],
            "foreign_key_violations": [list(row) for row in conn.execute("PRAGMA foreign_key_check")],
            "schema_migrations": [list(row) for row in conn.execute(
                "SELECT version, applied_at FROM schema_migration ORDER BY version")],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Browser helpers


def chromium_path() -> str:
    override = __import__("os").environ.get("PRUMO_CHROMIUM")
    if override:
        return override
    try:
        from tests.app.test_chart_layout import _chromium
        found = _chromium()
        if found:
            return found
    except Exception:  # noqa: BLE001 - fall through to Playwright's cache
        pass
    cache = Path.home() / ".cache" / "ms-playwright"
    candidates = sorted(cache.glob("chromium-*/chrome-linux*/chrome"))
    if candidates:
        return str(candidates[-1])
    which = shutil.which("chromium") or shutil.which("google-chrome")
    if which:
        return which
    raise RuntimeError("Chromium not found; set PRUMO_CHROMIUM")


def new_page(browser, width: int, *, touch: bool = False, java_script: bool = True,
             route_block: str | None = None):
    context = browser.new_context(
        viewport={"width": width, "height": VIEWPORT_HEIGHT},
        device_scale_factor=1,
        has_touch=touch,
        java_script_enabled=java_script,
    )
    if route_block:
        context.route(route_block, lambda route: route.abort())
    page = context.new_page()
    events = {"console_errors": [], "page_errors": [], "failed": [], "requests": []}

    def console(message):
        if message.type == "error":
            events["console_errors"].append({
                "text": message.text,
                "url": message.location.get("url") if message.location else None,
            })

    page.on("console", console)
    page.on("pageerror", lambda error: events["page_errors"].append(str(error)))
    page.on("requestfailed", lambda request: events["failed"].append({
        "url": request.url,
        "failure": request.failure,
    }))
    page.on("request", lambda request: events["requests"].append(request.url))
    return context, page, events


def goto(page, url: str):
    response = page.goto(url, wait_until="networkidle", timeout=45000)
    if response is None:
        raise AssertionError(f"no response for {url}")
    return response


def wait_enhanced(page, timeout: int = 6000) -> bool:
    try:
        page.wait_for_selector(".chart-shell.chart-enhanced", timeout=timeout)
        return True
    except Exception:  # noqa: BLE001 - absence is the finding
        return False


METRICS_JS = r"""
() => {
  const q = (selector) => document.querySelector(selector);
  const box = (element) => {
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
            width: rect.width, height: rect.height};
  };
  const canvas = q('.chart-canvas');
  const canvasNode = canvas ? canvas.querySelector('canvas') : null;
  let painted = null;
  let leftEdgeTextPixels = null;
  if (canvasNode) {
    try {
      const ctx = canvasNode.getContext('2d');
      const w = canvasNode.width, h = canvasNode.height;
      const seen = new Set();
      const stepX = Math.max(1, Math.floor(w / 18));
      const stepY = Math.max(1, Math.floor(h / 18));
      for (let x = 0; x < w; x += stepX) {
        for (let y = 0; y < h; y += stepY) {
          const d = ctx.getImageData(x, y, 1, 1).data;
          seen.add(d[0] + ',' + d[1] + ',' + d[2] + ',' + d[3]);
        }
      }
      painted = seen.size;
      const rect = canvasNode.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        const ratioX = w / rect.width, ratioY = h / rect.height;
        let edge = 0;
        const edgeX = Math.max(1, Math.ceil(3 * ratioX));
        const edgeY = Math.max(1, Math.ceil(25 * ratioY));
        for (let x = 0; x < edgeX; x += 1) {
          for (let y = 0; y < edgeY; y += 1) {
            const d = ctx.getImageData(x, y, 1, 1).data;
            if (d[3] > 20) edge += 1;
          }
        }
        leftEdgeTextPixels = edge;
      }
    } catch (error) {
      painted = -1;
      leftEdgeTextPixels = -1;
    }
  }
  const script = q('script.chart-data');
  let payload = null;
  if (script) {
    try {
      const data = JSON.parse(script.textContent);
      payload = {version: data.version, kind: data.kind,
                 periods: Array.isArray(data.periods) ? data.periods.length : null,
                 series: Array.isArray(data.series) ? data.series.length : null,
                 axes: Array.isArray(data.axes) ? data.axes.map((axis) => axis.unit) : []};
    } catch (error) {
      payload = {error: String(error)};
    }
  }
  const table = q('.notebook-workspace > .table-details');
  const bodyText = document.body.innerText || '';
  const bad = bodyText.match(/\b(null|undefined)\b/gi) || [];
  const readout = q('.chart-readout');
  const range = q('.chart-range');
  const settings = q('.notebook-chart-settings');
  const baseInput = settings ? settings.querySelector('input[name="base"]') : null;
  return {
    docWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body.scrollWidth,
    innerWidth: window.innerWidth,
    scrollY: window.scrollY,
    state: q('#grafico') ? q('#grafico').getAttribute('data-chart-state') : null,
    payload: payload,
    shell: q('.chart-shell') ? {enhanced: q('.chart-shell').classList.contains('chart-enhanced')} : null,
    canvas: canvas ? {display: getComputedStyle(canvas).display,
                      opacity: getComputedStyle(canvas).opacity,
                      rect: box(canvas), count: canvas.querySelectorAll('canvas').length,
                      painted: painted, leftEdgeTextPixels: leftEdgeTextPixels} : null,
    svg: (() => { const svg = q('.chart-wrap > svg');
      return svg ? {display: getComputedStyle(svg).display,
                    opacity: getComputedStyle(svg).opacity,
                    rect: box(svg),
                    text: svg.textContent.length} : null; })(),
    chartScroll: q('.chart-scroll') ? {scrollWidth: q('.chart-scroll').scrollWidth,
                                       clientWidth: q('.chart-scroll').clientWidth} : null,
    wrap: q('.chart-wrap') ? {rect: box(q('.chart-wrap')),
                             scrollWidth: q('.chart-wrap').scrollWidth,
                             clientWidth: q('.chart-wrap').clientWidth} : null,
    readout: readout ? {text: readout.textContent, font: getComputedStyle(readout).fontSize} : null,
    tickFont: q('.chart-tick') ? getComputedStyle(q('.chart-tick')).fontSize : null,
    axisTitleFont: q('.chart-axis-title') ? getComputedStyle(q('.chart-axis-title')).fontSize : null,
    bodyFont: getComputedStyle(document.body).fontSize,
    htmlFont: getComputedStyle(document.documentElement).fontSize,
    fonts: document.fonts ? document.fonts.status : null,
    stateLabel: q('.notebook-chart-state') ? q('.notebook-chart-state').textContent.trim() : null,
    reason: q('.empty-state') ? q('.empty-state').textContent.trim() : null,
    cards: document.querySelectorAll('.notebook-selection .card').length,
    cardChart: [...document.querySelectorAll('.card-chart')].map((element) => element.textContent.trim()),
    panelLabel: q('.notebook-chart-period-label') ? q('.notebook-chart-period-label').textContent.trim() : null,
    panelPeriod: q('.notebook-chart-period strong') ? q('.notebook-chart-period strong').textContent.trim() : null,
    range: range ? {hidden: range.hidden, value: range.value, min: range.min, max: range.max,
                    aria: range.getAttribute('aria-valuetext')} : null,
    table: table ? {rows: table.querySelectorAll('tbody tr').length,
                    first: [...table.querySelectorAll('tbody tr:first-child td')].map((cell) => cell.textContent.trim()),
                    last: [...table.querySelectorAll('tbody tr:last-child td')].map((cell) => cell.textContent.trim())} : null,
    calcCount: document.querySelectorAll('details.notebook-calculation').length,
    defsCount: document.querySelectorAll('details.notebook-definitions').length,
    provenanceCount: document.querySelectorAll('details.provenance-details').length,
    scriptSrc: q('script[src]') ? q('script[src]').getAttribute('src') : null,
    stylesheet: q('link[rel="stylesheet"]') ? q('link[rel="stylesheet"]').getAttribute('href') : null,
    settings: settings ? {open: settings.open, rect: box(settings),
                          base: baseInput ? {value: baseInput.value, font: getComputedStyle(baseInput).fontSize,
                                             rect: box(baseInput)} : null} : null,
    badWords: bad.slice(0, 8),
    badCount: bad.length,
  };
}
"""


def metrics(page) -> dict:
    return page.evaluate(METRICS_JS)


def axis_title_metrics(page, units: list[str]) -> dict | None:
    """Paint runs in the axis-name band, to catch clipped or merged unit titles."""
    if not units:
        return None
    return page.evaluate("""(units) => {
      const canvas = document.querySelector('.chart-canvas canvas');
      if (!canvas) return null;
      const ctx = canvas.getContext('2d');
      const width = canvas.width;
      const height = Math.min(30, canvas.height);
      let image;
      try {
        image = ctx.getImageData(0, 0, width, height);
      } catch (error) {
        return {error: String(error)};
      }
      const columns = [];
      for (let x = 0; x < width; x += 1) {
        let painted = 0;
        for (let y = 0; y < height; y += 1) {
          if (image.data[(y * width + x) * 4 + 3] > 20) painted += 1;
        }
        if (painted) columns.push(x);
      }
      const runs = [];
      let start = null, previous = null;
      for (const x of columns) {
        if (start === null) { start = x; previous = x; }
        else if (x - previous <= 6) { previous = x; }
        else { runs.push([start, previous]); start = x; previous = x; }
      }
      if (start !== null) runs.push([start, previous]);
      ctx.font = '19.8px ' + getComputedStyle(document.body).fontFamily;
      return {
        canvas_width: width,
        left_unit_width: ctx.measureText(units[0]).width,
        runs: runs,
        first_start: runs.length ? runs[0][0] : null,
        first_width: runs.length ? runs[0][1] - runs[0][0] + 1 : null,
      };
    }""", units)


def open_settings(page) -> dict:
    page.evaluate("() => { const element = document.querySelector('.notebook-chart-settings');"
                  " if (element) element.open = true; }")
    page.wait_for_timeout(80)
    value = page.evaluate("""() => {
      const element = document.querySelector('.notebook-chart-settings');
      if (!element) return null;
      const input = element.querySelector('input[name="base"]');
      const label = input ? input.closest('label') : null;
      const rect = input ? input.getBoundingClientRect() : null;
      const labelRect = label ? label.getBoundingClientRect() : null;
      return {
        open: element.open,
        base: input ? {value: input.value, font: getComputedStyle(input).fontSize,
                       left: rect.left, right: rect.right, width: rect.width, height: rect.height,
                       valueMissing: input.getAttribute('value')} : null,
        label: labelRect ? {left: labelRect.left, right: labelRect.right,
                            width: labelRect.width, height: labelRect.height,
                            text: label.textContent.trim()} : null,
      };
    }""")
    page.evaluate("() => { const element = document.querySelector('.notebook-chart-settings');"
                  " if (element) element.open = false; }")
    return value


def csp_ok(csp: str | None) -> tuple[bool, str]:
    """Strict script policy.

    A page without a chart bundle may omit script-src entirely and fall back to
    default-src 'none'. A page that loads the local bundle must name script-src 'self'
    and forbid inline script attributes. A style-only inline allowance is not a script
    failure.
    """
    if not csp:
        return False, "missing Content-Security-Policy"
    required = [CSP_BASE, "base-uri 'none'", "form-action 'self'", "frame-ancestors 'none'"]
    missing = [item for item in required if item not in csp]
    directives = [part.strip() for part in csp.split(";") if part.strip()]
    script = [part for part in directives
              if part == "script-src" or part.startswith("script-src ")]
    if script:
        if CSP_SCRIPT not in csp:
            missing.append(CSP_SCRIPT)
        if "script-src-attr 'none'" not in csp:
            missing.append("script-src-attr 'none'")
    forbidden = [item for item in ("unsafe-inline", "unsafe-eval")
                 if any(item in part for part in directives
                        if part.startswith("script-src"))
                 or any(item in part for part in directives
                        if part.startswith("script-src-attr"))]
    if missing or forbidden:
        return False, f"missing={missing} forbidden={forbidden} header={csp}"
    return True, csp


def external_requests(urls: list[str], origin: str) -> list[str]:
    return [url for url in urls
            if url.startswith(("http://", "https://")) and not url.startswith(origin)]


# ---------------------------------------------------------------------------
# Payload validation


def parse_periods(payload: dict) -> list[date]:
    return [datetime.strptime(period, "%d/%m/%Y").date() for period in payload["periods"]]


def expected_union(data: Data, side_ids: tuple[str, ...], window: str = "10a") -> list[date]:
    maps = []
    for series_id in side_ids:
        entry = data.series(series_id)
        maps.append({start: (period, row) for start, (period, row) in entry["starts"].items()})
    latest = max(max(mapping) for mapping in maps if mapping)
    if window == "max":
        start = date.min
    else:
        years = 10 if window == "10a" else 5
        try:
            start = latest.replace(year=latest.year - years)
        except ValueError:
            start = date(latest.year - years, 2, 28)
    dates = sorted({point for mapping in maps for point in mapping if point >= start})
    return dates


def expected_calendar_cells(data: Data, side_ids: tuple[str, ...], payload: dict,
                            window: str = "10a") -> tuple[list[dict], list[dict]]:
    """The exact per-side cells and the checks that must pass for them."""
    rows = []
    checks = []
    dates = parse_periods(payload)
    union = expected_union(data, side_ids, window)
    checks.append({"name": "union_window", "ok": dates == union,
                   "detail": {"payload": [str(item) for item in dates[:3]] +
                             [str(item) for item in dates[-3:]],
                             "expected": [str(item) for item in union[:3]] +
                             [str(item) for item in union[-3:]],
                             "payload_count": len(dates), "expected_count": len(union)}})
    for index, series_id in enumerate(side_ids):
        entry = data.series(series_id)
        frequency = entry["meta"]["frequency"]
        unit = base_unit_text("pt", entry["meta"]["unit"])
        present = 0
        for row_index, point in enumerate(dates):
            expected = entry["starts"].get(point)
            cell_period = payload["cell_periods"][row_index][index]
            display = payload["display"][row_index][index]
            value = payload["y"][row_index][index]
            if expected is None:
                ok = cell_period is None and display is None and value is None
                checks.append({"name": f"cell_null:{series_id}:{row_index}", "ok": ok,
                               "detail": None if ok else {
                                   "point": str(point), "cell_period": cell_period,
                                   "display": display, "value": value}})
                continue
            period, stored = expected
            present += 1
            expected_period = _format_period(period, frequency)
            expected_display = f"{format_value(stored['value_text'])} {unit}"
            ok = (cell_period == expected_period and display == expected_display
                  and isinstance(value, (int, float))
                  and math.isclose(float(value), float(stored["value_text"]),
                                   rel_tol=1e-12, abs_tol=1e-12))
            checks.append({"name": f"cell_value:{series_id}:{row_index}", "ok": ok,
                           "detail": None if ok else {
                               "point": str(point), "expected_period": expected_period,
                               "cell_period": cell_period,
                               "expected_display": expected_display, "display": display,
                               "expected_value": stored["value_text"], "value": value}})
        rows.append({"series": series_id, "frequency": frequency, "present": present})
        checks.append({"name": f"present_count:{series_id}", "ok": present > 0,
                       "detail": present})
        # A side's own native periods may contain real gaps. `breaks` names the first
        # present row after each missing native period; another series' null cells never
        # create a break for this side.
        present_rows = []
        for row_index, point in enumerate(dates):
            if point in entry["starts"]:
                present_rows.append((row_index, entry["starts"][point][0]))
        breaks = []
        for (previous_row, previous_period), (row, period) in zip(
                present_rows, present_rows[1:]):
            if frequency == "A":
                gap = int(period) - int(previous_period) > 1
            elif frequency == "M":
                left, right = _month_index(previous_period), _month_index(period)
                gap = left is not None and right is not None and right - left > 1
            else:
                gap = False
            if gap:
                breaks.append(row)
        payload_breaks = list(payload["series"][index].get("breaks", []))
        checks.append({"name": f"breaks:{series_id}", "ok": payload_breaks == breaks,
                       "detail": {"payload": payload_breaks, "expected": breaks}})
        # Month-only positions must never carry an annual value, and every annual cell
        # must sit on January 1 with its own year label.
        if frequency == "A":
            for row_index, point in enumerate(dates):
                value = payload["y"][row_index][index]
                if value is not None:
                    ok = point.month == 1 and point.day == 1 and payload["cell_periods"][row_index][index] == str(point.year)
                    checks.append({"name": f"annual_position:{series_id}:{row_index}", "ok": ok,
                                   "detail": None if ok else {"point": str(point),
                                                              "cell_period": payload["cell_periods"][row_index][index]}})
    return rows, checks


def _format_period(period: str, frequency: str) -> str:
    from app.formatting import format_period
    return format_period(period, frequency)


def expected_value_rows(data: Data, side_ids: tuple[str, ...], kind: str,
                        base_year: str | None = None) -> tuple[list[str], list[list[str]]]:
    annual = {series_id: data.complete_annual(series_id) for series_id in side_ids}
    common = set.intersection(*(set(values) for values in annual.values()))
    years = sorted(int(year) for year in common)
    if not years:
        return [], []
    latest = max(years)
    start = latest - 10
    years = [year for year in years if year >= start]
    rows = []
    for year in years:
        row = []
        for series_id in side_ids:
            values = annual[series_id]
            token = values[str(year)]
            if kind == "base100":
                base = values[base_year]
                exact = Fraction(token) * 100 / Fraction(base)
                text = _round_fraction(exact)
            else:
                exact = Fraction(token)
                text = _round_fraction(exact)
            row.append(text)
        rows.append(row)
    return [str(year) for year in years], rows


def annual_means(data: Data, side_ids: tuple[str, ...]) -> dict[str, dict[str, str]]:
    return {series_id: data.complete_annual(series_id) for series_id in side_ids}


def _exact_annual(data: Data, series_id: str, year: str) -> Fraction:
    entry = data.series(series_id)
    if entry["meta"]["frequency"] == "A":
        return Fraction(entry["by_period"][year]["value_text"])
    tokens = []
    for month in range(1, 13):
        row = entry["by_period"].get(f"{year}-{month:02d}")
        if row is None or not _is_number(row["value_text"]):
            raise AssertionError(f"incomplete month {year}-{month:02d} for {series_id}")
        tokens.append(Fraction(row["value_text"]))
    return Fraction(sum(tokens), 12)


def expected_pp_rows(data: Data, side_ids: tuple[str, ...], base_year: str) -> tuple[list[str], list[list[str]]]:
    annual = annual_means(data, side_ids)
    common = set.intersection(*(set(values) for values in annual.values()))
    years = sorted(int(year) for year in common)
    if not years:
        return [], []
    latest = max(years)
    years = [year for year in years if year >= latest - 10]
    rows = []
    for year in years:
        row = []
        for series_id in side_ids:
            exact = _exact_annual(data, series_id, str(year)) - _exact_annual(
                data, series_id, base_year)
            row.append(_round_fraction(exact))
        rows.append(row)
    return [str(year) for year in years], rows


def check_payload_rows(data: Data, payload: dict, side_ids: tuple[str, ...],
                       expected_years: list[str], expected: list[list[str]],
                       rec: "Recorder", prefix: str) -> None:
    rec.check(f"{prefix}:payload_periods", payload["periods"] == expected_years,
              {"payload": payload["periods"], "expected": expected_years})
    units = [payload["series"][index]["unit"] for index in range(len(side_ids))]
    for index, series_id in enumerate(side_ids):
        mismatches = []
        for row_index, year in enumerate(expected_years):
            display = payload["display"][row_index][index]
            value = payload["y"][row_index][index]
            expected_display = f"{format_value(expected[row_index][index])} {units[index]}"
            if display != expected_display or not math.isclose(
                    float(value), float(expected[row_index][index]), rel_tol=1e-12, abs_tol=1e-12):
                mismatches.append({"year": year, "display": display,
                                   "expected_display": expected_display,
                                   "value": value, "expected_value": expected[row_index][index]})
        rec.check(f"{prefix}:values:{series_id}", not mismatches,
                  {"rows": len(expected_years), "mismatches": mismatches[:4],
                   "mismatch_count": len(mismatches)})


# ---------------------------------------------------------------------------
# Recorder and checks


class Recorder:
    def __init__(self):
        self.checks: list[dict] = []
        self.failures: list[dict] = []
        self.assertions = 0
        self.pages_loaded = 0
        self.matrix: list[dict] = []
        self.matrix_assertions = 0
        self.screenshots: list[str] = []
        self.fallbacks: list[dict] = []
        self.cases: list[dict] = []
        self.observations: list[dict] = []

    def check(self, name: str, ok: bool, detail=None) -> bool:
        self.assertions += 1
        entry = {"name": name, "ok": bool(ok)}
        if detail is not None:
            entry["detail"] = detail
        self.checks.append(entry)
        if not ok:
            self.failures.append(entry)
        return bool(ok)

    def page(self) -> None:
        self.pages_loaded += 1

    def matrix_cell(self, cell: dict, conditions: list[tuple[bool, str]]) -> None:
        issues = [message for ok, message in conditions if not ok]
        self.matrix_assertions += len(conditions)
        cell["issues"] = issues
        self.matrix.append(cell)
        if issues:
            self.failures.append({"name": "matrix:" + cell["id"], "detail": cell})


def check_shell(rec: Recorder, page, response, events, *, prefix: str, width: int,
                expected: dict, touch: bool = False) -> dict:
    csp = response.headers.get("content-security-policy")
    csp_good, csp_detail = csp_ok(csp)
    origin = urllib.parse.urlsplit(page.url).scheme + "://" + urllib.parse.urlsplit(page.url).netloc
    external = external_requests(events["requests"], origin)
    rec.check(f"csp:{prefix}:{width}", csp_good, csp_detail)
    rec.check(f"offorigin:{prefix}:{width}", not external, external[:6])
    rec.check(f"pageerrors:{prefix}:{width}", not events["page_errors"],
              events["page_errors"][:4])
    rec.check(f"consoleerrors:{prefix}:{width}", not events["console_errors"],
              events["console_errors"][:4])
    return {"csp": csp_good, "external": external,
            "page_errors": events["page_errors"],
            "console_errors": events["console_errors"],
            "csp_header": csp}


def check_mixed_payload(rec: Recorder, data: Data, payload_text: str, case: dict,
                        prefix: str) -> dict:
    payload = json.loads(payload_text)
    side_ids = (HICP, WORLD_GDP) if case["id"] == "mixed_ihpc_worldbank" else (HICP, EURO_GDP)
    rec.check(f"{prefix}:version", payload["version"] == 2, payload["version"])
    rec.check(f"{prefix}:kind", payload["kind"] == "calendar", payload["kind"])
    rec.check(f"{prefix}:series_count", len(payload["series"]) == 2, len(payload["series"]))
    rows, checks = expected_calendar_cells(data, side_ids, payload)
    for item in checks:
        if item["name"].startswith("cell_value") or item["name"].startswith("cell_null"):
            continue
        rec.check(f"{prefix}:{item['name']}", item["ok"], item["detail"])
    cell_failures = [item for item in checks
                     if item["name"].startswith("cell_") and not item["ok"]]
    rec.check(f"{prefix}:all_cells", not cell_failures,
              {"cells_checked": len(payload["periods"]) * 2,
               "failures": cell_failures[:4], "failure_count": len(cell_failures)})
    annual_index = 1 if side_ids[1] in (WORLD_GDP, EURO_GDP) else 0
    present_rows = [index for index, row in enumerate(payload["y"])
                    if row[annual_index] is not None]
    month_only_rows = [index for index, row in enumerate(payload["y"])
                       if row[annual_index] is None]
    rec.check(f"{prefix}:annual_not_fabricated",
              all(parse_periods(payload)[index].month == 1
                  and payload["cell_periods"][index][annual_index] == str(parse_periods(payload)[index].year)
                  for index in present_rows),
              {"annual_present_rows": len(present_rows),
               "month_only_rows": len(month_only_rows)})
    rec.check(f"{prefix}:native_gaps",
              all(not payload["series"][index].get("breaks") for index in range(2)),
              [payload["series"][index].get("breaks") for index in range(2)])
    ticks = payload.get("x_ticks", [])
    domain = payload.get("x_max", 0) - payload.get("x_min", 0)
    span = max((tick["x"] for tick in ticks), default=0) - min(
        (tick["x"] for tick in ticks), default=0)
    tick_years = [int(str(tick["text"])[:4]) for tick in ticks
                  if str(tick["text"])[:4].isdigit()]
    dates = parse_periods(payload)
    coverage_ok = (bool(ticks) and domain > 0 and span >= 0.6 * domain
                   and bool(tick_years)
                   and tick_years[0] <= dates[0].year + 1
                   and tick_years[-1] >= dates[-1].year - 1)
    rec.check(f"{prefix}:x_axis_coverage", coverage_ok,
              {"ticks": len(ticks), "span_days": round(span, 1),
               "domain_days": round(domain, 1),
               "span_ratio": round(span / domain, 3) if domain else None,
               "first_tick": ticks[0]["text"] if ticks else None,
               "last_tick": ticks[-1]["text"] if ticks else None,
               "first_period": payload["periods"][0],
               "last_period": payload["periods"][-1]})
    return payload


def check_main_table(rec: Recorder, page, payload: dict, side_ids: tuple[str, ...],
                     prefix: str, missing: str) -> None:
    table = page.evaluate("""() => {
      const details = document.querySelector('.notebook-workspace > .table-details');
      if (!details) return null;
      details.open = true;
      const rows = [...details.querySelectorAll('tbody tr')];
      return {
        head: [...details.querySelectorAll('thead th')].map((cell) => cell.textContent.trim()),
        rows: rows.map((row) => [...row.querySelectorAll('td')].map((cell) => cell.textContent.trim())),
      };
    }""")
    rec.check(f"{prefix}:table_present", table is not None, None)
    if table is None:
        return
    rec.check(f"{prefix}:table_row_count", len(table["rows"]) == len(payload["periods"]),
              {"rows": len(table["rows"]), "periods": len(payload["periods"])})
    rec.check(f"{prefix}:table_headers",
              len(table["head"]) == len(side_ids) + 1
              and all(side in " ".join(table["head"]) for side in
                      [payload["series"][index]["title"].split(" - ")[0]
                       for index in range(len(side_ids))]),
              table["head"])
    mismatches = []
    for position, row in enumerate(table["rows"]):
        payload_index = len(payload["periods"]) - 1 - position
        if not row or row[0] != payload["periods"][payload_index]:
            mismatches.append({"row": position, "period": row[0] if row else None,
                               "expected": payload["periods"][payload_index]})
            continue
        for index in range(len(side_ids)):
            display = payload["display"][payload_index][index]
            cell = row[index + 1] if index + 1 < len(row) else ""
            if display is None:
                if missing not in cell:
                    mismatches.append({"row": position, "side": index,
                                       "cell": cell, "expected": missing})
                continue
            value_part = display.split(" ", 1)[0]
            if not cell.startswith(value_part):
                mismatches.append({"row": position, "side": index, "cell": cell,
                                   "expected_prefix": value_part})
            if any(word in cell.lower() for word in ("null", "undefined")):
                mismatches.append({"row": position, "side": index, "cell": cell,
                                   "bad_word": True})
    rec.check(f"{prefix}:table_cells", not mismatches,
              {"rows_checked": len(table["rows"]), "mismatches": mismatches[:4],
               "mismatch_count": len(mismatches)})
    rec.check(f"{prefix}:table_exact_edges",
              table["rows"] and table["rows"][0][0] == payload["periods"][-1]
              and table["rows"][-1][0] == payload["periods"][0],
              {"first": table["rows"][0] if table["rows"] else None,
               "last": table["rows"][-1] if table["rows"] else None})


def check_provenance(rec: Recorder, page, data: Data, side_ids: tuple[str, ...],
                     prefix: str, panel_label: str, panel_period: str) -> None:
    text = page.evaluate("""() => {
      const details = document.querySelector('details.provenance-details');
      return details ? details.textContent : null;
    }""")
    rec.check(f"{prefix}:provenance_present", text is not None, None)
    rec.check(f"{prefix}:own_period_label", panel_label is not None, panel_label)
    rec.check(f"{prefix}:own_period_value", panel_period is not None, panel_period)
    if text is None:
        return
    failures = []
    for series_id in side_ids:
        period, row = data.latest(series_id)
        entry = data.series(series_id)
        period_text = _format_period(period, entry["meta"]["frequency"])
        fetched = datetime.fromisoformat(row["fetched_at"]).strftime("%d/%m/%Y, %H:%M UTC")
        sha = None
        if "sha256" in row:
            sha = row["sha256"]
        if period_text not in text:
            failures.append({"series": series_id, "missing_period": period_text})
        if fetched not in text:
            failures.append({"series": series_id, "missing_fetched": fetched})
        if f"#{row['dataset_run_id']}" not in text:
            failures.append({"series": series_id, "missing_run": row["dataset_run_id"]})
    rec.check(f"{prefix}:provenance_values", not failures, failures[:6])
    rec.check(f"{prefix}:provenance_no_bad_words",
              "null" not in text.lower() and "undefined" not in text.lower(), None)


def check_cards(rec: Recorder, page, prefix: str, expected: list[str]) -> list[str]:
    texts = page.eval_on_selector_all(".card-chart", "els => els.map((e) => e.textContent.trim())")
    missing = [item for item in expected if not any(item in text for text in texts)]
    rec.check(f"{prefix}:cards_own_period", not missing,
              {"cards": texts, "missing": missing})
    return texts


def readout_expected(payload: dict, point: int, data: Data, side_ids: tuple[str, ...],
                     series_titles: list[str], missing: str) -> str:
    parts = []
    date_value = parse_periods(payload)[point]
    for index, series_id in enumerate(side_ids):
        entry = data.series(series_id)
        frequency = entry["meta"]["frequency"]
        expected = entry["starts"].get(date_value)
        if expected is None:
            parts.append(f"{series_titles[index]} - {missing}")
        else:
            period, row = expected
            unit = base_unit_text("pt", entry["meta"]["unit"])
            parts.append(f"{series_titles[index]} - {_format_period(period, frequency)}: "
                         f"{format_value(row['value_text'])} {unit}")
    return payload["periods"][point] + " - " + "; ".join(parts)


def find_point_pixel(page, payload: dict, index: int, dual: bool = True) -> tuple[float, float]:
    """Find a real pixel inside the plot that selects a specific union row.

    ECharts applies containLabel padding on top of the adapter grid constants. Scanning
    inward from the adapter's nominal boundary finds the true plot edge without reading
    ECharts internals.
    """
    page.eval_on_selector(".chart-wrap", """element => {
      element.scrollIntoView({block: 'center', inline: 'nearest'});
    }""")
    page.wait_for_timeout(80)
    rect = page.eval_on_selector(".chart-canvas", """element => {
      const rect = element.getBoundingClientRect();
      return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
    }""")
    scale = rect["width"] / 880
    left = rect["x"] + 97 * scale
    right = rect["x"] + rect["width"] - (172 if dual else 33) * scale
    if index == 0:
        candidates = range(int(left), int(min(right, left + 180)) + 1, 2)
    elif index >= len(payload["periods"]) - 1:
        candidates = range(int(right), int(max(left, right - 180)) - 1, -2)
    else:
        middle = (left + right) / 2
        offsets = [0]
        for distance in range(4, 240, 4):
            offsets.extend((distance, -distance))
        candidates = [middle + offset for offset in offsets
                      if left <= middle + offset <= right]
    y = rect["y"] + rect["height"] / 2
    for x in candidates:
        page.mouse.move(x, y)
        page.wait_for_timeout(30)
        readout = page.locator(".chart-readout").inner_text()
        if readout.startswith(payload["periods"][index]):
            tooltip = page.locator(".chart-tooltip")
            if tooltip.count():
                tip_text = tooltip.inner_text()
                if (tooltip.evaluate("element => element.getBoundingClientRect().height > 0")
                        and payload["periods"][index] in _normalise_tip(tip_text)):
                    return x, y
    return (left + right) / 2, y


def _normalise_tip(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(" - ", " ").replace(";", " ")).strip()


def check_keyboard(rec: Recorder, page, payload: dict, expected: list[str], prefix: str) -> None:
    from playwright.sync_api import expect

    page.eval_on_selector(".chart-range", "element => element.focus()")
    sequence = [("Home", 0), ("ArrowRight", 1), ("End", len(expected) - 1),
                ("ArrowLeft", len(expected) - 2)]
    failures = []
    for key, point in sequence:
        page.keyboard.press(key)
        # The native range updates synchronously; ECharts paints its tooltip on a later frame.
        # Await the actual target text before comparing complete strings, not a fixed 80ms sleep.
        expect(page.locator(".chart-readout")).to_have_text(expected[point], timeout=3000)
        expect(page.locator(".chart-tooltip")).to_contain_text(
            payload["periods"][point], timeout=3000)
        readout = page.locator(".chart-readout").inner_text()
        aria = page.eval_on_selector(".chart-range", "element => element.getAttribute('aria-valuetext')")
        tip = page.locator(".chart-tooltip")
        tip_text = tip.inner_text().replace("\n", " ") if tip.count() else ""
        if (readout != expected[point] or aria != payload["periods"][point]
                or _normalise_tip(expected[point]) not in _normalise_tip(tip_text)):
            failures.append({"key": key, "point": point, "readout": readout,
                             "aria": aria, "tip": tip_text[:200]})
    rec.check(f"{prefix}:keyboard_tooltips", not failures, failures[:4])


def check_pointer(rec: Recorder, page, payload: dict, expected: list[str],
                  prefix: str, dual: bool) -> None:
    points = [0, len(expected) // 2, len(expected) - 1]
    failures = []
    for point in points:
        x, y = find_point_pixel(page, payload, point, dual=dual)
        page.mouse.move(x, y)
        page.wait_for_timeout(120)
        readout = page.locator(".chart-readout").inner_text()
        tip = page.locator(".chart-tooltip")
        tip_text = tip.inner_text().replace("\n", " ") if tip.count() else ""
        visible = tip.count() and tip.evaluate(
            "element => element.getBoundingClientRect().height > 0")
        if (readout != expected[point] or not visible
                or _normalise_tip(expected[point]) not in _normalise_tip(tip_text)):
            failures.append({"point": point, "readout": readout,
                             "visible": bool(visible), "tip": tip_text[:200]})
    rec.check(f"{prefix}:pointer_tooltips", not failures, failures[:3])


def find_touch_pixel(page, payload: dict, index: int, dual: bool = True) -> tuple[float, float]:
    """A pixel on the side's actual edge point, selected by the union-row readout."""
    page.eval_on_selector(".chart-wrap", """element => {
      element.scrollIntoView({block: 'center', inline: 'nearest'});
    }""")
    page.wait_for_timeout(80)
    rect = page.eval_on_selector(".chart-canvas", """element => {
      const rect = element.getBoundingClientRect();
      return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
    }""")
    scale = rect["width"] / 880
    left = rect["x"] + 97 * scale
    right = rect["x"] + rect["width"] - (172 if dual else 33) * scale
    y = rect["y"] + rect["height"] / 2
    target = payload["periods"][index]
    if index == 0:
        candidates = range(int(left), int(min(right, left + 160)) + 1, 2)
        previous = None
        for x in candidates:
            page.mouse.move(x, y)
            page.wait_for_timeout(20)
            if page.locator(".chart-readout").inner_text().startswith(target):
                previous = x
            elif previous is not None:
                return previous, y
        return (previous if previous is not None else left), y
    if index >= len(payload["periods"]) - 1:
        candidates = range(int(right), int(max(left, right - 160)) - 1, -2)
        previous = None
        for x in candidates:
            page.mouse.move(x, y)
            page.wait_for_timeout(20)
            if page.locator(".chart-readout").inner_text().startswith(target):
                previous = x
            elif previous is not None:
                return previous, y
        return (previous if previous is not None else right), y
    return (left + right) / 2, y


def check_touch(rec: Recorder, page, payload: dict, expected: list[str], prefix: str,
                dual: bool) -> None:
    failures = []
    for point in (len(expected) - 1, 0):
        x, y = find_touch_pixel(page, payload, point, dual=dual)
        # The hover tooltip must not sit over the touch point at hit-test time.
        page.mouse.move(5, 5)
        page.wait_for_timeout(50)
        page.touchscreen.tap(x, y)
        page.wait_for_timeout(25)
        readout = page.locator(".chart-readout").inner_text()
        sample = page.evaluate("""() => {
          const tip = document.querySelector('.chart-tooltip');
          if (!tip) return null;
          const style = getComputedStyle(tip);
          return {text: tip.innerText, visibility: style.visibility,
                  opacity: style.opacity, height: tip.getBoundingClientRect().height};
        }""")
        tip_text = (sample["text"] if sample else "").replace("\n", " ")
        visible = bool(sample and sample["visibility"] == "visible"
                       and float(sample["opacity"]) > 0 and sample["height"] > 0)
        hidden_after = None
        if sample:
            for elapsed in range(25, 401, 25):
                page.wait_for_timeout(25)
                hidden = page.evaluate("""() => {
                  const tip = document.querySelector('.chart-tooltip');
                  if (!tip) return true;
                  const style = getComputedStyle(tip);
                  return style.visibility === 'hidden' || Number(style.opacity) === 0;
                }""")
                if hidden:
                    hidden_after = elapsed
                    break
        if (readout != expected[point] or not visible
                or _normalise_tip(expected[point]) not in _normalise_tip(tip_text)):
            failures.append({"point": point, "readout": readout,
                             "visible_immediately": visible,
                             "hidden_after_ms": hidden_after,
                             "tip": tip_text[:200]})
        else:
            rec.check(f"{prefix}:touch_tooltip_content:{point}", True,
                      {"visible_immediately": True, "hidden_after_ms": hidden_after})
            rec.observations.append({"kind": "touch_tooltip", "point": point,
                                     "visible_immediately": True,
                                     "hidden_after_ms": hidden_after})
    # A touch that starts on a different point must not change the readout until release.
    page.eval_on_selector(".chart-range", "element => element.focus()")
    page.keyboard.press("Home")
    page.eval_on_selector(".chart-wrap", """element => {
      element.scrollIntoView({block: 'center', inline: 'nearest'});
    }""")
    page.wait_for_timeout(80)
    rect = page.eval_on_selector(".chart-canvas", """element => {
      const rect = element.getBoundingClientRect();
      return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
    }""")
    x = rect["x"] + rect["width"] / 2
    y = rect["y"] + rect["height"] / 2
    before = page.locator(".chart-readout").inner_text()
    page.evaluate("""([x, y]) => {
      const stage = document.querySelector('.chart-canvas');
      stage.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'touch',
        clientX: x, clientY: y, bubbles: true}));
    }""", [x, y])
    page.wait_for_timeout(80)
    during = page.locator(".chart-readout").inner_text()
    page.evaluate("""([x, y]) => {
      const stage = document.querySelector('.chart-canvas');
      stage.dispatchEvent(new PointerEvent('pointerup', {pointerType: 'touch',
        clientX: x, clientY: y, bubbles: true}));
    }""", [x, y])
    page.wait_for_timeout(120)
    after = page.locator(".chart-readout").inner_text()
    rec.check(f"{prefix}:touch_release", during == before and after != before,
              {"before": before, "during": during, "after": after})
    rec.check(f"{prefix}:touch_tooltips", not failures, failures[:2])


# ---------------------------------------------------------------------------
# Evidence checks


def _display_output(data: Data, series_id: str, year: str, transform: str,
                    base_year: str | None) -> str:
    annual = data.complete_annual(series_id)
    if transform == "base100":
        assert base_year is not None
        exact = Fraction(annual[year]) * 100 / Fraction(annual[base_year])
        return format_value(_round_fraction(exact))
    if transform == "pp":
        assert base_year is not None
        exact = _exact_annual(data, series_id, year) - _exact_annual(
            data, series_id, base_year)
        return format_value(_round_fraction(exact))
    return format_value(annual[year])


def check_evidence(rec: Recorder, page, data: Data, side_ids: tuple[str, ...],
                   prefix: str, transform: str, base_year: str | None = None) -> None:
    page.evaluate("""() => {
      document.querySelectorAll('details.notebook-calculation, details.provenance-details,'
        + ' details.notebook-definitions, details.table-details')
        .forEach((element) => { element.open = true; });
    }""")
    page.wait_for_timeout(100)
    sections = page.eval_on_selector_all(".notebook-calculation-side", """elements => elements.map((section) => {
      const tables = [...section.querySelectorAll('table.analysis-inputs')].map((table) => ({
        head: [...table.querySelectorAll('thead th')].map((cell) => cell.textContent.trim()),
        rows: [...table.querySelectorAll('tbody tr')].map((row) =>
          [...row.querySelectorAll('td')].map((cell) => cell.textContent.trim())),
      }));
      const link = section.querySelector('a[href]');
      const linkRect = link ? link.getBoundingClientRect() : null;
      return {
        heading: section.querySelector('h4') ? section.querySelector('h4').textContent.trim() : '',
        definition: section.querySelector('dl') ? section.querySelector('dl').textContent.trim() : '',
        note: [...section.querySelectorAll('p.note')].map((p) => p.textContent.trim()),
        tables: tables,
        link: link ? link.getAttribute('href') : null,
        linkVisible: Boolean(linkRect && linkRect.width > 0 && linkRect.height > 0),
      };
    })""")
    rec.check(f"{prefix}:evidence_sides", len(sections) == len(side_ids),
              {"sections": len(sections), "expected": len(side_ids)})
    if len(sections) != len(side_ids):
        return
    for index, series_id in enumerate(side_ids):
        section = sections[index]
        entry = data.series(series_id)
        annual = data.complete_annual(series_id)
        latest_year = max(annual)
        failures = []
        if series_id not in (section["link"] or ""):
            failures.append({"missing_link": series_id, "link": section["link"]})
        if not section["linkVisible"]:
            failures.append({"link_not_visible": section["link"]})
        expected_method = ("média aritmética de doze valores mensais"
                           if entry["meta"]["frequency"] == "M" else "valor anual original")
        if expected_method not in section["definition"]:
            failures.append({"missing_method": expected_method,
                             "definition": section["definition"][:300]})
        if transform == "base100":
            if "100 × valor ÷ valor do ano de base" not in section["definition"]:
                failures.append({"missing_formula": "base100",
                                 "definition": section["definition"][:300]})
            if base_year and f"{base_year} (explícito)" not in section["definition"]:
                failures.append({"missing_base": base_year})
        if transform == "pp":
            if "valor − valor do ano de base" not in section["definition"]:
                failures.append({"missing_formula": "pp",
                                 "definition": section["definition"][:300]})
            if base_year and f"{base_year} (explícito)" not in section["definition"]:
                failures.append({"missing_base": base_year})
        if len(section["tables"]) < (2 if (entry["meta"]["frequency"] == "M"
                                           or transform in ("base100", "pp")) else 1):
            failures.append({"tables": len(section["tables"])})
            rec.check(f"{prefix}:evidence:{series_id}", False, failures)
            continue
        latest_table = section["tables"][0]
        expected_inputs = 12 if entry["meta"]["frequency"] == "M" else 1
        if len(latest_table["rows"]) != expected_inputs:
            failures.append({"latest_inputs": len(latest_table["rows"]),
                             "expected": expected_inputs})
        if latest_table["rows"]:
            first = latest_table["rows"][0]
            expected_value = _display_output(data, series_id, latest_year,
                                             transform, base_year)
            expected_output = f"{latest_year} · {expected_value}"
            if not first[0].startswith(expected_output):
                failures.append({"latest_output": first[0], "expected": expected_output})
            if entry["meta"]["frequency"] == "M":
                for month, row in enumerate(latest_table["rows"], start=1):
                    source_row = entry["by_period"][f"{latest_year}-{month:02d}"]
                    token = source_row["value_text"]
                    expected_fetched = datetime.fromisoformat(
                        source_row["fetched_at"]).strftime("%d/%m/%Y, %H:%M UTC")
                    if row[2] != format_value(token):
                        failures.append({"input_month": month, "cell": row[2],
                                         "expected": format_value(token)})
                    if row[4] != expected_fetched:
                        failures.append({"input_month": month, "fetched": row[4],
                                         "expected": expected_fetched})
                    if row[5] != f"#{source_row['dataset_run_id']}":
                        failures.append({"input_month": month, "run": row[5],
                                         "expected": f"#{source_row['dataset_run_id']}"})
            else:
                source_row = entry["by_period"][latest_year]
                expected_fetched = datetime.fromisoformat(
                    source_row["fetched_at"]).strftime("%d/%m/%Y, %H:%M UTC")
                if latest_table["rows"][0][4] != expected_fetched:
                    failures.append({"latest_fetched": latest_table["rows"][0][4],
                                     "expected": expected_fetched})
                if latest_table["rows"][0][5] != f"#{source_row['dataset_run_id']}":
                    failures.append({"latest_run": latest_table["rows"][0][5],
                                     "expected": f"#{source_row['dataset_run_id']}"})
        if transform in ("base100", "pp"):
            base_table = section["tables"][1]
            if not base_table["rows"]:
                failures.append({"missing_base_table": True})
            else:
                assert base_year is not None
                expected_base = f"{base_year} · {_display_output(data, series_id, base_year, transform, base_year)}"
                if not base_table["rows"][0][0].startswith(expected_base):
                    failures.append({"base_output": base_table["rows"][0][0],
                                     "expected": expected_base})
                expected_rows = 12 if entry["meta"]["frequency"] == "M" else 1
                if len(base_table["rows"]) != expected_rows:
                    failures.append({"base_inputs": len(base_table["rows"]),
                                     "expected": expected_rows})
        rec.check(f"{prefix}:evidence:{series_id}", not failures, failures[:6])


def check_print(rec: Recorder, page, data: Data, side_ids: tuple[str, ...],
                prefix: str, pdf_path: Path) -> None:
    page.emulate_media(media="print")
    page.wait_for_timeout(100)
    measured = page.evaluate("""() => {
      const q = (selector) => document.querySelector(selector);
      const canvas = q('.chart-canvas');
      const svg = q('.chart-wrap > svg');
      const calc = q('details.notebook-calculation');
      const link = calc ? calc.querySelector('a[href]') : null;
      const table = q('.notebook-workspace > .table-details');
      const rect = link ? link.getBoundingClientRect() : null;
      return {
        canvasDisplay: canvas ? getComputedStyle(canvas).display : null,
        svgOpacity: svg ? getComputedStyle(svg).opacity : null,
        svgVisible: Boolean(svg && svg.getBoundingClientRect().height > 0),
        calcDisplay: calc ? getComputedStyle(calc).display : null,
        calcContent: calc ? getComputedStyle(calc).contentVisibility : null,
        linkVisible: Boolean(rect && rect.width > 0 && rect.height > 0),
        tableDisplay: table ? getComputedStyle(table).display : null,
        tableVisible: Boolean(table && table.getBoundingClientRect().height > 0),
        settingsDisplay: q('.notebook-chart-settings') ? getComputedStyle(q('.notebook-chart-settings')).display : null,
        svgText: svg ? svg.textContent : '',
      };
    }""")
    failures = []
    if measured["canvasDisplay"] != "none":
        failures.append({"canvas": measured["canvasDisplay"]})
    if measured["svgOpacity"] != "1" or not measured["svgVisible"]:
        failures.append({"svg": measured["svgOpacity"], "visible": measured["svgVisible"]})
    if measured["calcDisplay"] != "block" or not measured["linkVisible"]:
        failures.append({"calc": measured["calcDisplay"], "link": measured["linkVisible"]})
    if measured["tableVisible"] is not True:
        failures.append({"table": measured["tableDisplay"]})
    if measured["settingsDisplay"] != "none":
        failures.append({"settings": measured["settingsDisplay"]})
    if not measured["svgText"]:
        failures.append({"svg_text": 0})
    page.pdf(path=str(pdf_path), format="A4", print_background=True)
    rec.check(f"{prefix}:print_svg_evidence", not failures,
              {"failures": failures, "pdf": str(pdf_path),
               "pdf_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0})


def check_fallbacks(rec: Recorder, browser, base: str, data: Data) -> None:
    expected_rows = len(expected_union(data, (HICP, WORLD_GDP)))
    # No JavaScript: the server SVG and native disclosures are the reading path.
    context, page, events = new_page(browser, 1440, java_script=False)
    try:
        response = goto(page, base + MIXED_WB)
        rec.page()
        measured = metrics(page)
        table = page.evaluate("""() => {
          const details = document.querySelector('.notebook-workspace > .table-details');
          if (!details) return null;
          details.open = true;
          return {rows: details.querySelectorAll('tbody tr').length,
                  text: details.textContent.slice(0, 200)};
        }""")
        svg_text = page.eval_on_selector(".chart-wrap > svg", "element => element.textContent")
        svg_ticks = page.eval_on_selector_all(".chart-wrap > svg text.chart-tick", """elements => {
          const ticks = elements.map((element) => ({
            x: Number(element.getAttribute('x')),
            y: Number(element.getAttribute('y')),
            text: element.textContent,
          }));
          if (!ticks.length) return [];
          const bottom = Math.max(...ticks.map((tick) => tick.y));
          return ticks.filter((tick) => tick.y === bottom);
        }""")
        failures = []
        if response.status != 200:
            failures.append({"status": response.status})
        if measured["shell"] and measured["shell"]["enhanced"]:
            failures.append({"enhanced": True})
        if measured["svg"] is None or measured["svg"]["opacity"] != "1":
            failures.append({"svg": measured["svg"]})
        if measured["canvas"] and measured["canvas"]["opacity"] != "0":
            failures.append({"canvas": measured["canvas"]})
        if table is None or table["rows"] != expected_rows:
            failures.append({"table": table, "expected_rows": expected_rows})
        if "3,9 %" not in svg_text or "1,1 %" not in svg_text:
            failures.append({"svg_values": False})
        if svg_ticks:
            span = max(tick["x"] for tick in svg_ticks) - min(tick["x"] for tick in svg_ticks)
            years = [tick["text"] for tick in svg_ticks if tick["text"][:4].isdigit()]
            if span < 0.6 * 880 or not years or int(years[-1]) < 2025:
                failures.append({"svg_x_axis": {"span": span, "years": years}})
        else:
            failures.append({"svg_x_axis": "no x ticks"})
        if not check_shell(rec, page, response, events, prefix="nojs", width=1440,
                           expected={"state": "ready"})["csp"]:
            failures.append({"csp": True})
        rec.check("fallback:nojs", not failures, failures)
        rec.fallbacks.append({"id": "nojs", "ok": not failures, "failures": failures})
    finally:
        context.close()

    # Failed bundle: no enhancement, no blank chart, no exception.
    context, page, events = new_page(browser, 1440, route_block="**/prumo-charts.min.js*")
    try:
        response = goto(page, base + MIXED_WB)
        rec.page()
        measured = metrics(page)
        failures = []
        if measured["shell"] and measured["shell"]["enhanced"]:
            failures.append({"enhanced": True})
        if measured["svg"] is None or measured["svg"]["opacity"] != "1":
            failures.append({"svg": measured["svg"]})
        if measured["canvas"] and measured["canvas"]["opacity"] != "0":
            failures.append({"canvas": measured["canvas"]})
        if measured["table"] is None or measured["table"]["rows"] != expected_rows:
            failures.append({"table": measured["table"], "expected_rows": expected_rows})
        if any("prumo-charts" not in item["url"] for item in events["failed"]):
            failures.append({"unexpected_failed": events["failed"]})
        if events["page_errors"]:
            failures.append({"page_errors": events["page_errors"]})
        rec.check("fallback:blocked_bundle", not failures, failures)
        rec.fallbacks.append({"id": "blocked_bundle", "ok": not failures, "failures": failures})
    finally:
        context.close()


# ---------------------------------------------------------------------------
# Asset and legacy checks


def asset_receipt(base: str, proxy: "_PrefixProxy | None") -> dict:
    manifest_path = REPO / "static" / "js" / "prumo-charts.manifest.json"
    bundle_path = REPO / "static" / "js" / "prumo-charts.min.js"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    bundle_bytes = bundle_path.read_bytes()
    actual_sha = hashlib.sha256(bundle_bytes).hexdigest()
    result = {
        "manifest_path": str(manifest_path),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest_bytes": len(manifest_bytes),
        "declared_asset": manifest.get("asset"),
        "declared_sha256": manifest.get("sha256"),
        "declared_bytes": manifest.get("bytes"),
        "actual_sha256": actual_sha,
        "actual_bytes": len(bundle_bytes),
        "match": actual_sha == manifest.get("sha256") and len(bundle_bytes) == manifest.get("bytes"),
        "served": {},
    }
    for label, url in (("direct", base + "/static/js/prumo-charts.min.js"),
                       ("proxy", proxy.url("/static/js/prumo-charts.min.js") if proxy else None)):
        if not url:
            continue
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read()
            result["served"][label] = {
                "status": response.status,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "content_type": response.headers.get("content-type"),
                "match": hashlib.sha256(body).hexdigest() == manifest.get("sha256"),
            }
    return result


def check_legacy(rec: Recorder, browser, base: str) -> None:
    cases = (
        ("samefreq_notebook", "/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT", 1, "comparison"),
        ("series_detail", "/series/ine.hicp_yoy.PT", 1, "line"),
        ("curated_country", "/comparar/paises/pib-por-habitante", 1, "group"),
    )
    for case_id, path, version, kind in cases:
        context, page, events = new_page(browser, 1440)
        try:
            response = goto(page, base + path)
            rec.page()
            wait_enhanced(page)
            measured = metrics(page)
            failures = []
            if response.status != 200:
                failures.append({"status": response.status})
            if not measured["shell"] or not measured["shell"]["enhanced"]:
                failures.append({"enhanced": False})
            if measured["payload"] is None:
                failures.append({"payload": None})
            else:
                if measured["payload"].get("version") != version:
                    failures.append({"version": measured["payload"].get("version")})
                if measured["payload"].get("kind") != kind:
                    failures.append({"kind": measured["payload"].get("kind")})
            if measured["canvas"] is None or measured["canvas"]["opacity"] != "1":
                failures.append({"canvas": measured["canvas"]})
            if measured["badCount"]:
                failures.append({"badWords": measured["badWords"]})
            if events["page_errors"]:
                failures.append({"page_errors": events["page_errors"]})
            rec.check(f"legacy:{case_id}", not failures, failures)
        finally:
            context.close()


# ---------------------------------------------------------------------------
# Matrix and functional run


def run_matrix(rec: Recorder, browser, base: str, proxy: "_PrefixProxy | None",
               data: Data) -> None:
    prefixes = [("direct", base)]
    if proxy:
        prefixes.append(("proxy", proxy.url("")))
    for prefix, root in prefixes:
        for width in WIDTHS:
            print(f"matrix: {prefix} {width}", flush=True)
            context = browser.new_context(
                viewport={"width": width, "height": VIEWPORT_HEIGHT},
                device_scale_factor=1, has_touch=width <= 390,
            )
            try:
                for case in CASES:
                    page = context.new_page()
                    rec.page()
                    events = {"console_errors": [], "page_errors": [], "failed": [], "requests": []}
                    page.on("console", lambda message, ev=events: ev["console_errors"].append(
                        {"text": message.text, "url": message.location.get("url") if message.location else None})
                        if message.type == "error" else None)
                    page.on("pageerror", lambda error, ev=events: ev["page_errors"].append(str(error)))
                    page.on("requestfailed", lambda request, ev=events: ev["failed"].append(
                        {"url": request.url, "failure": request.failure}))
                    page.on("request", lambda request, ev=events: ev["requests"].append(request.url))
                    try:
                        response = goto(page, root + case["path"])
                        if case["state"] == "ready":
                            wait_enhanced(page)
                        measured = metrics(page)
                        title_layout = None
                        if case["state"] == "ready" and measured["payload"]:
                            title_layout = axis_title_metrics(
                                page, measured["payload"].get("axes", []))
                        settings = open_settings(page)
                        origin = urllib.parse.urlsplit(page.url).scheme + "://" + urllib.parse.urlsplit(page.url).netloc
                        external = external_requests(events["requests"], origin)
                        csp = response.headers.get("content-security-policy")
                        csp_good, _ = csp_ok(csp)
                        ready = case["state"] == "ready"
                        conditions = [
                            (response.status == 200, f"status={response.status}"),
                            (measured["state"] == case["state"],
                             f"state={measured['state']} expected={case['state']}"),
                            (measured["docWidth"] <= measured["innerWidth"] + 1,
                             f"document width {measured['docWidth']} > {measured['innerWidth']}"),
                            (measured["bodyWidth"] <= measured["innerWidth"] + 1,
                             f"body width {measured['bodyWidth']} > {measured['innerWidth']}"),
                            (measured["badCount"] == 0, f"null/undefined visible: {measured['badWords']}"),
                            (measured["cards"] == case["cards"],
                             f"cards={measured['cards']} expected={case['cards']}"),
                            (csp_good, "strict CSP missing or relaxed"),
                            (not external, f"off-origin requests={external[:4]}"),
                            (not events["page_errors"], f"page errors={events['page_errors'][:2]}"),
                            (not events["console_errors"], f"console errors={events['console_errors'][:2]}"),
                            (not events["failed"], f"failed requests={events['failed'][:2]}"),
                        ]
                        if ready:
                            payload = measured["payload"] or {}
                            conditions += [
                                (measured["shell"] is not None and measured["shell"]["enhanced"],
                                 "chart shell is not enhanced"),
                                (payload.get("version") == case["version"],
                                 f"payload version={payload.get('version')}"),
                                (payload.get("kind") == case["kind"],
                                 f"payload kind={payload.get('kind')}"),
                                (measured["canvas"] is not None and measured["canvas"]["opacity"] == "1",
                                 f"canvas={measured['canvas']}"),
                                (measured["canvas"] is not None and (measured["canvas"]["painted"] or 0) > 2,
                                 f"painted colors={measured['canvas']['painted'] if measured['canvas'] else None}"),
                                (title_layout is not None
                                 and title_layout.get("first_start") is not None
                                 and title_layout["first_start"] > 2
                                 and title_layout["first_width"]
                                 <= title_layout["left_unit_width"] + 12,
                                 f"axis title layout={title_layout}"),
                                (measured["wrap"] is not None and measured["wrap"]["rect"]["height"] >= 200,
                                 f"plot height={measured['wrap']['rect']['height'] if measured['wrap'] else None}"),
                                (measured["wrap"] is not None
                                 and 0 <= measured["wrap"]["rect"]["top"] < VIEWPORT_HEIGHT,
                                 f"plot top={measured['wrap']['rect']['top'] if measured['wrap'] else None}"),
                                (measured["chartScroll"] is not None
                                 and measured["chartScroll"]["scrollWidth"] <= measured["chartScroll"]["clientWidth"] + 1,
                                 f"chart scroll={measured['chartScroll']}"),
                                (measured["readout"] is not None
                                 and float(measured["readout"]["font"].replace("px", "")) >= 20,
                                 f"readout font={measured['readout']['font'] if measured['readout'] else None}"),
                                (measured["tickFont"] is not None
                                 and float(measured["tickFont"].replace("px", "")) >= 18,
                                 f"tick font={measured['tickFont']}"),
                                (measured["table"] is not None
                                 and measured["table"]["rows"] == (payload.get("periods") or 0),
                                 f"table rows={measured['table']['rows'] if measured['table'] else None}"),
                                (measured["settings"] is not None
                                 and measured["wrap"] is not None
                                 and measured["settings"]["rect"]["top"] > measured["wrap"]["rect"]["top"],
                                 "settings appear before the plot"),
                                (settings is not None and settings["base"] is not None
                                 and float(settings["base"]["font"].replace("px", "")) >= 18,
                                 f"base font={settings['base']['font'] if settings and settings['base'] else None}"),
                                (settings is not None and settings["base"] is not None
                                 and settings["base"]["right"] <= measured["innerWidth"] + 1
                                 and settings["base"]["width"] > 0,
                                 f"base rect={settings['base'] if settings and settings['base'] else None}"),
                                (settings is not None and settings["label"] is not None
                                 and "Ano de base" in settings["label"]["text"]
                                 and settings["label"]["right"] <= measured["innerWidth"] + 1,
                                 f"base label={settings['label'] if settings else None}"),
                            ]
                            if case["id"].startswith("base100"):
                                conditions.append((settings is not None
                                                   and settings["base"] is not None
                                                   and settings["base"]["value"] == "2015",
                                                   f"base value={settings['base']['value'] if settings and settings['base'] else None}"))
                            if case["evidence"]:
                                conditions.append((measured["calcCount"] == 1,
                                                   f"calculation disclosures={measured['calcCount']}"))
                        else:
                            conditions += [
                                (measured["canvas"] is None, "canvas on unavailable chart"),
                                (measured["payload"] is None, f"payload={measured['payload']}"),
                                (case.get("reason", "") in (measured["reason"] or ""),
                                 f"reason={measured['reason']}"),
                            ]
                        stylesheet_prefix = f"{PREFIX}/static/" if prefix == "proxy" else "/static/"
                        conditions.append((measured["stylesheet"] is not None
                                           and measured["stylesheet"].startswith(stylesheet_prefix),
                                           f"stylesheet={measured['stylesheet']}"))
                        if ready:
                            script_prefix = f"{PREFIX}/static/" if prefix == "proxy" else "/static/"
                            conditions.append((measured["scriptSrc"] is not None
                                               and measured["scriptSrc"].startswith(script_prefix),
                                               f"script={measured['scriptSrc']}"))
                        if prefix == "proxy" and proxy is not None:
                            conditions.append((any(item["prefix"] == PREFIX for item in proxy.seen),
                                               "proxy did not forward X-Forwarded-Prefix"))
                        cell = {
                            "id": case["id"], "width": width, "prefix": prefix,
                            "state": measured["state"], "payload": measured["payload"],
                            "plot_top": measured["wrap"]["rect"]["top"] if measured["wrap"] else None,
                            "plot_height": measured["wrap"]["rect"]["height"] if measured["wrap"] else None,
                            "doc_width": measured["docWidth"], "inner_width": measured["innerWidth"],
                            "readout_font": measured["readout"]["font"] if measured["readout"] else None,
                            "tick_font": measured["tickFont"],
                            "base_font": settings["base"]["font"] if settings and settings["base"] else None,
                            "axis_title": title_layout,
                            "csp": csp_good, "external": external,
                            "page_errors": events["page_errors"],
                            "console_errors": events["console_errors"],
                        }
                        rec.matrix_cell(cell, conditions)
                    except Exception as exc:  # noqa: BLE001 - keep the matrix moving
                        rec.matrix_cell({"id": case["id"], "width": width, "prefix": prefix,
                                         "error": repr(exc)}, [(False, repr(exc))])
                    finally:
                        page.close()
            finally:
                context.close()


def screenshot(browser, base: str, path: str, width: int, filename: str,
               rec: Recorder) -> None:
    context, page, _events = new_page(browser, width)
    try:
        rec.page()
        goto(page, base + path)
        wait_enhanced(page)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(250)
        scroll = page.evaluate("window.scrollY")
        target = REPORT_DIR / filename
        page.screenshot(path=str(target), full_page=False, animations="disabled")
        rec.screenshots.append(filename)
        rec.check(f"screenshot:{filename}", scroll == 0 and target.exists()
                  and target.stat().st_size > 0,
                  {"scrollY": scroll, "bytes": target.stat().st_size if target.exists() else 0})
    finally:
        context.close()


def run_functional(rec: Recorder, browser, base: str, data: Data) -> None:
    # Mixed native pair: exact cells, table, own-period provenance, keyboard, pointer.
    print("functional: mixed_wb", flush=True)
    context, page, events = new_page(browser, 1440)
    try:
        response = goto(page, base + MIXED_WB)
        rec.page()
        wait_enhanced(page)
        shell = check_shell(rec, page, response, events, prefix="mixed_wb", width=1440,
                            expected={"state": "ready"})
        payload_text = page.eval_on_selector("script.chart-data", "element => element.textContent")
        payload = check_mixed_payload(rec, data, payload_text, CASES[0], "mixed_wb")
        side_ids = (HICP, WORLD_GDP)
        check_main_table(rec, page, payload, side_ids, "mixed_wb", payload["missing"])
        expected_readouts = [readout_expected(payload, index, data, side_ids,
                                              [payload["series"][0]["title"],
                                               payload["series"][1]["title"]],
                                              payload["missing"])
                             for index in range(len(payload["periods"]))]
        check_keyboard(rec, page, payload, expected_readouts, "mixed_wb")
        check_pointer(rec, page, payload, expected_readouts, "mixed_wb", dual=True)
        mixed_periods = [_format_period(data.latest(series_id)[0],
                                        data.series(series_id)["meta"]["frequency"])
                         for series_id in side_ids]
        check_provenance(rec, page, data, side_ids, "mixed_wb",
                         "Últimos períodos por série", " · ".join(mixed_periods))
        check_cards(rec, page, "mixed_wb", mixed_periods)
    finally:
        context.close()
    print("functional: mixed_euro", flush=True)

    # The Eurostat variant uses the same calendar contract with euro units.
    context, page, events = new_page(browser, 1440)
    try:
        response = goto(page, base + MIXED_EURO)
        rec.page()
        wait_enhanced(page)
        check_shell(rec, page, response, events, prefix="mixed_euro", width=1440,
                    expected={"state": "ready"})
        payload_text = page.eval_on_selector("script.chart-data", "element => element.textContent")
        payload = check_mixed_payload(rec, data, payload_text, CASES[1], "mixed_euro")
        check_main_table(rec, page, payload, (HICP, EURO_GDP), "mixed_euro", payload["missing"])
        mixed_periods = [_format_period(data.latest(series_id)[0],
                                        data.series(series_id)["meta"]["frequency"])
                         for series_id in (HICP, EURO_GDP)]
        check_provenance(rec, page, data, (HICP, EURO_GDP), "mixed_euro",
                         "Últimos períodos por série", " · ".join(mixed_periods))
    finally:
        context.close()
    print("functional: touch", flush=True)

    # Mobile touch path over the mounted prefix.
    proxy = getattr(run_functional, "proxy", None)
    if proxy is not None:
        context, page, events = new_page(browser, 390, touch=True)
        try:
            response = goto(page, proxy.url(MIXED_WB))
            rec.page()
            wait_enhanced(page)
            check_shell(rec, page, response, events, prefix="mixed_touch", width=390,
                        expected={"state": "ready"})
            payload_text = page.eval_on_selector("script.chart-data", "element => element.textContent")
            payload = check_mixed_payload(rec, data, payload_text, CASES[0], "mixed_touch")
            expected_readouts = [readout_expected(payload, index, data, (HICP, WORLD_GDP),
                                                  [payload["series"][0]["title"],
                                                   payload["series"][1]["title"]],
                                                  payload["missing"])
                                 for index in range(len(payload["periods"]))]
            check_keyboard(rec, page, payload, expected_readouts, "mixed_touch")
            check_touch(rec, page, payload, expected_readouts, "mixed_touch", dual=True)
        finally:
            context.close()
    print("functional: annual", flush=True)

    # Annual calculated view.
    context, page, events = new_page(browser, 1440)
    try:
        response = goto(page, base + ANNUAL)
        rec.page()
        wait_enhanced(page)
        check_shell(rec, page, response, events, prefix="annual", width=1440,
                    expected={"state": "ready"})
        payload_text = page.eval_on_selector("script.chart-data", "element => element.textContent")
        payload = json.loads(payload_text)
        rec.check("annual:version", payload["version"] == 1, payload["version"])
        rec.check("annual:kind", payload["kind"] == "comparison", payload["kind"])
        side_ids = (HICP, EURO_GDP)
        annual_maps = {series_id: data.complete_annual(series_id) for series_id in side_ids}
        common_years = set.intersection(*(set(values) for values in annual_maps.values()))
        expected_years = sorted(common_years)
        latest_year = max(int(year) for year in expected_years)
        expected_years = [year for year in expected_years if int(year) >= latest_year - 10]
        expected_rows = []
        for year in expected_years:
            expected_rows.append([annual_maps[side_ids[0]][year],
                                  annual_maps[side_ids[1]][year]])
        rec.check("annual:years", payload["periods"] == expected_years,
                  {"payload": payload["periods"], "expected": expected_years})
        check_payload_rows(data, payload, side_ids, expected_years, expected_rows,
                           rec, "annual")
        rec.check("annual:official_inflation_note",
                  page.evaluate("() => document.body.innerText.includes("
                                "'não é a taxa de inflação anual oficial')"), None)
        rec.check("annual:calculated_badge",
                  payload["series"][0]["badge"] == "calculado"
                  and payload["series"][1]["badge"] == "",
                  [entry.get("badge") for entry in payload["series"]])
        rec.check("annual:dual_axes", len(payload["axes"]) == 2,
                  [axis["unit"] for axis in payload["axes"]])
        check_main_table(rec, page, payload, side_ids, "annual",
                         "sem observação nesta posição temporal")
        print("annual: evidence", flush=True)
        check_evidence(rec, page, data, side_ids, "annual", "annual")
        print("annual: print", flush=True)
        check_print(rec, page, data, side_ids, "annual", REPORT_DIR / "annual-print.pdf")
        print("annual: panel", flush=True)
        panel = metrics(page)
        rec.check("annual:own_period",
                  panel["panelLabel"] == "Último período anual"
                  and panel["panelPeriod"] == str(latest_year),
                  {"label": panel["panelLabel"], "period": panel["panelPeriod"]})
        check_cards(rec, page, "annual", [str(latest_year)])
    finally:
        context.close()
    print("functional: base100", flush=True)

    # Base 100 pair.
    context, page, events = new_page(browser, 1440)
    try:
        response = goto(page, base + BASE100)
        rec.page()
        wait_enhanced(page)
        check_shell(rec, page, response, events, prefix="base100", width=1440,
                    expected={"state": "ready"})
        payload = json.loads(page.eval_on_selector("script.chart-data",
                                                   "element => element.textContent"))
        side_ids = (EURO_GDP, EURO_GDP_ES)
        years, rows = expected_value_rows(data, side_ids, "base100", "2015")
        rec.check("base100:version", payload["version"] == 1, payload["version"])
        rec.check("base100:kind", payload["kind"] == "comparison", payload["kind"])
        rec.check("base100:periods", payload["periods"] == years,
                  {"payload": payload["periods"], "expected": years})
        check_payload_rows(data, payload, side_ids, years, rows, rec, "base100")
        rec.check("base100:common_axis", len(payload["axes"]) == 1,
                  [axis["unit"] for axis in payload["axes"]])
        rec.check("base100:base_year",
                  bool(rows) and rows[0] == ["100.000000", "100.000000"]
                  and years[0] == "2015",
                  {"first_year": years[0], "first_row": rows[0] if rows else None})
        check_main_table(rec, page, payload, side_ids, "base100",
                         "sem observação nesta posição temporal")
        check_evidence(rec, page, data, side_ids, "base100", "base100",
                       base_year="2015")
        panel = metrics(page)
        rec.check("base100:own_period",
                  panel["panelLabel"] == "Último período anual" and panel["panelPeriod"] == years[-1],
                  {"label": panel["panelLabel"], "period": panel["panelPeriod"]})
        check_print(rec, page, data, side_ids, "base100", REPORT_DIR / "base100-print.pdf")
    finally:
        context.close()
    print("functional: base100_six", flush=True)

    # Base 100 group with six GDP sides.
    context, page, events = new_page(browser, 1440)
    try:
        response = goto(page, base + BASE100_SIX)
        rec.page()
        wait_enhanced(page)
        check_shell(rec, page, response, events, prefix="base100_six", width=1440,
                    expected={"state": "ready"})
        payload = json.loads(page.eval_on_selector("script.chart-data",
                                                   "element => element.textContent"))
        years, rows = expected_value_rows(data, SIX_GDP, "base100", "2015")
        rec.check("base100_six:version", payload["version"] == 1, payload["version"])
        rec.check("base100_six:kind", payload["kind"] == "group", payload["kind"])
        rec.check("base100_six:periods", payload["periods"] == years,
                  {"payload": payload["periods"], "expected": years})
        rec.check("base100_six:series_count", len(payload["series"]) == 6,
                  len(payload["series"]))
        check_payload_rows(data, payload, SIX_GDP, years, rows, rec, "base100_six")
        rec.check("base100_six:common_axis", len(payload["axes"]) == 1,
                  len(payload["axes"]))
        check_main_table(rec, page, payload, SIX_GDP, "base100_six",
                         "sem observação nesta posição temporal")
        check_evidence(rec, page, data, SIX_GDP, "base100_six", "base100", base_year="2015")
    finally:
        context.close()
    print("functional: pp", flush=True)

    # Percentage points.
    context, page, events = new_page(browser, 1440)
    try:
        response = goto(page, base + PP)
        rec.page()
        wait_enhanced(page)
        check_shell(rec, page, response, events, prefix="pp", width=1440,
                    expected={"state": "ready"})
        payload = json.loads(page.eval_on_selector("script.chart-data",
                                                   "element => element.textContent"))
        side_ids = (HICP, UNEMP)
        years, rows = expected_pp_rows(data, side_ids, "2015")
        rec.check("pp:version", payload["version"] == 1, payload["version"])
        rec.check("pp:kind", payload["kind"] == "comparison", payload["kind"])
        rec.check("pp:periods", payload["periods"] == years,
                  {"payload": payload["periods"], "expected": years})
        check_payload_rows(data, payload, side_ids, years, rows, rec, "pp")
        rec.check("pp:common_axis", len(payload["axes"]) == 1,
                  [axis["unit"] for axis in payload["axes"]])
        rec.check("pp:zero_base",
                  all(row == "0.000000" for row in rows[0]),
                  {"year": years[0], "row": rows[0]})
        check_main_table(rec, page, payload, side_ids, "pp",
                         "sem observação nesta posição temporal")
        check_evidence(rec, page, data, side_ids, "pp", "pp", base_year="2015")
        body_text = page.inner_text("body")
        rec.check("pp:official_inflation_note",
                  "não é a taxa de inflação anual oficial" in body_text, None)
        rec.check("pp:unemployment_unweighted_note",
                  "não ponderada" in body_text and "estimativa anual oficial" in body_text,
                  None)
        check_print(rec, page, data, side_ids, "pp", REPORT_DIR / "pp-print.pdf")
    finally:
        context.close()

    # Incompatible and off states are 200 pages with cards, no script and a reason.
    for case in CASES:
        if case["state"] == "ready":
            continue
        context, page, events = new_page(browser, 1440)
        try:
            response = goto(page, base + case["path"])
            rec.page()
            measured = metrics(page)
            failures = []
            if response.status != 200:
                failures.append({"status": response.status})
            if measured["state"] != case["state"]:
                failures.append({"state": measured["state"]})
            if measured["payload"] is not None:
                failures.append({"payload": measured["payload"]})
            if case.get("reason", "") not in (measured["reason"] or ""):
                failures.append({"reason": measured["reason"]})
            if measured["cards"] != case["cards"]:
                failures.append({"cards": measured["cards"]})
            if measured["badCount"]:
                failures.append({"badWords": measured["badWords"]})
            if events["page_errors"]:
                failures.append({"page_errors": events["page_errors"]})
            rec.check(f"state:{case['id']}", not failures, failures)
        finally:
            context.close()


# ---------------------------------------------------------------------------
# Report


def write_receipt(rec: Recorder, args, data: Data, before: dict, after: dict,
                  assets: dict, environment: dict, fatal: str | None) -> None:
    failures = rec.failures
    passed = not failures and fatal is None
    ready_cells = [cell for cell in rec.matrix
                   if cell.get("payload") and not cell.get("error")]
    matrix_summary = {
        "min_plot_height": min((cell["plot_height"] for cell in ready_cells
                                if cell.get("plot_height") is not None), default=None),
        "min_plot_top": min((cell["plot_top"] for cell in ready_cells
                             if cell.get("plot_top") is not None), default=None),
        "max_plot_top": max((cell["plot_top"] for cell in ready_cells
                             if cell.get("plot_top") is not None), default=None),
        "max_horizontal_overflow": max((cell["doc_width"] - cell["inner_width"]
                                        for cell in rec.matrix), default=None),
        "min_readout_font": min((float(cell["readout_font"].replace("px", ""))
                                 for cell in ready_cells if cell.get("readout_font")),
                                default=None),
        "min_tick_font": min((float(cell["tick_font"].replace("px", ""))
                              for cell in ready_cells if cell.get("tick_font")),
                             default=None),
        "min_base_font": min((float(cell["base_font"].replace("px", ""))
                              for cell in ready_cells if cell.get("base_font")),
                             default=None),
    }
    payload = {
        "kind": "prumo-notebook-time-transformations-browser-acceptance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": args.base,
        "proxy": environment.get("proxy"),
        "db_path": str(args.db),
        "head": environment.get("head"),
        "dirty": environment.get("dirty"),
        "result": "PASS" if passed else "FAIL",
        "fatal": fatal,
        "counts": {
            "pages_loaded": rec.pages_loaded,
            "matrix_cells": len(rec.matrix),
            "matrix_assertions": rec.matrix_assertions,
            "matrix_cells_failed": sum(1 for cell in rec.matrix if cell.get("issues")),
            "functional_checks": len(rec.checks),
            "functional_assertions": rec.assertions,
            "functional_failures": len(rec.checks) - sum(1 for check in rec.checks if check["ok"]),
            "screenshots": len(rec.screenshots),
            "db_tables": before.get("table_count"),
            "db_rows": before.get("row_count"),
        },
        "failures": failures,
        "cases": rec.cases,
        "matrix": rec.matrix,
        "matrix_summary": matrix_summary,
        "observations": rec.observations,
        "fallbacks": rec.fallbacks,
        "screenshots": rec.screenshots,
        "assets": assets,
        "db": {
            "before": before,
            "after": after,
            "equal": before.get("overall_sha256") == after.get("overall_sha256"),
            "tables_equal": {table["name"]: next(
                (other["sha256"] == table["sha256"] for other in after.get("tables", [])
                 if other["name"] == table["name"]), False)
                for table in before.get("tables", [])},
        },
        "environment": environment,
        "limitations": [
            "Shared edge, Authelia and production host configuration were not exercised locally.",
            "Human screen-reader acceptance remains a separate manual gate.",
            "The visual clipping review is recorded in visual-review.md.",
        ],
    }
    (REPORT_DIR / "receipt.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Notebook time transformations - real-copy browser acceptance",
        "",
        f"- Result: **{payload['result']}**",
        f"- Generated: {payload['generated_at']}",
        f"- Base: `{args.base}`",
        f"- Proxy: `{payload['proxy'] or 'not used'}`",
        f"- Database: `{args.db}`",
        f"- HEAD: `{environment.get('head')}`",
        f"- Asset manifest: `{assets.get('manifest_sha256')}` "
        f"({assets.get('manifest_bytes')} bytes)",
        f"- Bundle: `{assets.get('actual_sha256')}` ({assets.get('actual_bytes')} bytes), "
        f"declared match={assets.get('match')}",
        "",
        "## Actual counts",
        "",
        f"- Pages loaded: {rec.pages_loaded}",
        f"- Matrix cells: {len(rec.matrix)} ({rec.matrix_assertions} assertions), "
        f"failed cells: {sum(1 for cell in rec.matrix if cell.get('issues'))}",
        f"- Functional checks: {len(rec.checks)} ({rec.assertions} assertions), "
        f"failures: {len(rec.checks) - sum(1 for check in rec.checks if check['ok'])}",
        f"- Screenshots: {len(rec.screenshots)}",
        f"- Database tables fingerprinted: {before.get('table_count')}, "
        f"rows hashed: {before.get('row_count')}",
        f"- Table fingerprints equal before/after: {payload['db']['equal']}",
        f"- Integrity check: {before.get('integrity_check')}",
        f"- Foreign key violations: {len(before.get('foreign_key_violations', []))}",
        f"- Matrix plot heights: min {matrix_summary['min_plot_height']} px, "
        f"plot top {matrix_summary['min_plot_top']} to {matrix_summary['max_plot_top']} px",
        f"- Matrix horizontal overflow maximum: {matrix_summary['max_horizontal_overflow']} px",
        f"- Matrix fonts: readout min {matrix_summary['min_readout_font']} px, "
        f"ticks min {matrix_summary['min_tick_font']} px, "
        f"base control min {matrix_summary['min_base_font']} px",
        "",
        "## Cases",
        "",
        "| Case | State | Payload | Periods | Matrix cells | Failed cells |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in CASES:
        cells = [cell for cell in rec.matrix if cell["id"] == case["id"]]
        failed = sum(1 for cell in cells if cell.get("issues"))
        periods = sorted({cell["payload"]["periods"] for cell in cells
                          if cell.get("payload") and cell["payload"].get("periods") is not None})
        version = sorted({f"v{cell['payload']['version']}/{cell['payload']['kind']}"
                          for cell in cells if cell.get("payload")})
        lines.append(f"| {case['id']} | {case['state']} | {', '.join(version) or '-'} | "
                     f"{', '.join(str(item) for item in periods) or '-'} | {len(cells)} | {failed} |")
    lines += [
        "",
        "## Blockers",
        "",
    ]
    blockers = []
    if any("x_axis_coverage" in str(failure.get("name")) for failure in failures):
        blockers.append("Calendar x-axis labels do not cover the plotted history "
                        "(6 ticks spanning 304 of 3652 days, last tick 2017 for 2016-2026).")
    clipped = [cell for cell in rec.matrix
               if any(str(issue).startswith("axis title layout")
                      for issue in cell.get("issues", []))]
    if clipped:
        blockers.append(f"Canvas y-axis unit text is clipped or merged at the top edge in "
                        f"{len(clipped)} matrix cells (base100 pair and six sides at all "
                        f"widths; mixed and annual charts at 320 and 390).")
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Failure details",
        "",
    ]
    matrix_failures = [failure for failure in failures
                       if str(failure.get("name")).startswith("matrix:")]
    other_failures = [failure for failure in failures
                      if not str(failure.get("name")).startswith("matrix:")]
    if matrix_failures:
        grouped: dict[str, list[dict]] = {}
        for failure in matrix_failures:
            detail = failure.get("detail") or {}
            key = str(detail.get("id", "unknown"))
            grouped.setdefault(key, []).append(detail)
        for case_id, cells in sorted(grouped.items()):
            widths = sorted({int(cell["width"]) for cell in cells
                             if cell.get("width") is not None})
            prefixes = sorted({str(cell["prefix"]) for cell in cells
                               if cell.get("prefix") is not None})
            issues = sorted({issue for cell in cells for issue in cell.get("issues", [])})
            lines.append(f"- `{case_id}`: {len(cells)} failed cells at widths {widths} "
                         f"on {prefixes}; {issues}")
    for failure in other_failures[:20]:
        lines.append(f"- `{failure.get('name')}`: "
                     f"{json.dumps(failure.get('detail'), ensure_ascii=False)[:500]}")
    if len(other_failures) > 20:
        lines.append(f"- ... {len(other_failures) - 20} more in receipt.json")
    lines += [
        "",
        "## Screenshots",
        "",
    ]
    for name in rec.screenshots:
        lines.append(f"- `{name}`")
    lines += [
        "",
        "## Observations",
        "",
    ]
    if rec.observations:
        for item in rec.observations:
            lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Limits",
        "",
    ]
    for item in payload["limitations"]:
        lines.append(f"- {item}")
    (REPORT_DIR / "receipt.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8197",
                        help="origin serving the public app, without the /dados prefix")
    parser.add_argument("--db", default=str(Path.home() / ".hermes" / "cache" / "scratch" /
                                            "prumo-time-transformations" / "acceptance.sqlite3"),
                        help="read-only SQLite copy used for exact value checks")
    parser.add_argument("--no-proxy", action="store_true",
                        help="skip the local X-Forwarded-Prefix proxy half of the matrix")
    parser.add_argument("--chromium", default=None, help="explicit Chromium executable")
    args = parser.parse_args()
    args.base = args.base.rstrip("/")
    args.db = Path(args.db)
    if args.chromium:
        __import__("os").environ["PRUMO_CHROMIUM"] = args.chromium
    if not args.db.exists():
        raise SystemExit(f"database not found: {args.db}")

    rec = Recorder()
    fatal = None
    before = table_fingerprints(args.db)
    data = Data(args.db)
    proxy = None
    after = before
    assets = {}
    environment = {}
    browser = None
    playwright = None
    try:
        from playwright.sync_api import sync_playwright
        executable = chromium_path()
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=True, executable_path=executable, args=["--no-sandbox"])
        environment = {
            "python": sys.version.split()[0],
            "playwright": getattr(__import__("playwright"), "__version__", "unknown"),
            "chromium": executable,
            "head": subprocess.check_output(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            "dirty": subprocess.check_output(
                ["git", "-C", str(REPO), "status", "--porcelain"], text=True).strip().splitlines(),
            "viewport_height": VIEWPORT_HEIGHT,
            "widths": list(WIDTHS),
            "proxy": None,
        }
        if not args.no_proxy:
            proxy = _PrefixProxy(args.base)
            proxy.start()
            environment["proxy"] = proxy.url("")
            run_functional.proxy = proxy
        assets = asset_receipt(args.base, proxy)

        print("phase: matrix", flush=True)
        run_matrix(rec, browser, args.base, proxy, data)
        print("phase: functional", flush=True)
        run_functional(rec, browser, args.base, data)
        print("phase: fallbacks", flush=True)
        check_fallbacks(rec, browser, args.base, data)
        print("phase: legacy", flush=True)
        check_legacy(rec, browser, args.base)
        print("phase: screenshots", flush=True)
        for case in CASES:
            if case.get("screenshot"):
                for width in (1440, 390):
                    screenshot(browser, args.base, case["path"], width,
                               f"{case['screenshot']}-{width}.png", rec)
        screenshot(browser, args.base, BASE100_SIX, 1440, "base100-six-sides-1440.png", rec)
    except Exception as exc:  # noqa: BLE001 - a broken run still leaves a receipt
        fatal = repr(exc)
    finally:
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()
        if proxy is not None:
            proxy.stop()
        data.close()
        after = table_fingerprints(args.db)
        write_receipt(rec, args, data, before, after, assets, environment, fatal)

    if fatal:
        print(f"FAIL: {fatal}")
        return 1
    failed = rec.failures
    print(f"{'PASS' if not failed else 'FAIL'}: {len(rec.matrix)} matrix cells, "
          f"{rec.assertions} functional assertions, {len(failed)} failures")
    for failure in failed[:20]:
        print(f"- {failure.get('name')}: {json.dumps(failure.get('detail'), ensure_ascii=False)[:300]}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
