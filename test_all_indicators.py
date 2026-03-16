#!/usr/bin/env python3
"""
Prumo — Exhaustive Indicator Audit via Browser (Análise tab)

Tests ALL 372 indicators individually + common pairs/trios.
For each test: selects indicator(s), waits for chart render + AI analysis,
logs result, takes screenshot on failure.

Pre-populates the server-side interpret cache (30-day TTL).

Usage:
    source venv/bin/activate
    python test_all_indicators.py [--resume N] [--headless]

Progress:  tail -f /tmp/prumo-audit.log
Results:   /tmp/prumo-audit-results.json
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
LOG_FILE = "/tmp/prumo-audit.log"
RESULTS_FILE = "/tmp/prumo-audit-results.json"
SCREENSHOTS_DIR = "/tmp/prumo-audit-screenshots"
MAX_AI_WAIT = 120  # seconds to wait for AI analysis
MAX_CHART_WAIT = 45  # seconds to wait for chart render
# Match the frontend default (5-year window) so that the AI interpret cache
# built during the audit is reused when real users open the same indicators.
_now = datetime.now()
DEFAULT_FROM = f"{_now.year - 5}-{_now.month:02d}"
DEFAULT_TO = f"{_now.year}-{_now.month:02d}"

# Common pairs/trios that users would likely explore together
COMMON_COMBOS = [
    # Custo de Vida
    {"name": "Inflação + Euribor 12m", "indicators": [
        ("INE", "hicp_yoy"), ("BPORTUGAL", "euribor_12m")]},
    {"name": "Gasóleo + Gasolina", "indicators": [
        ("DGEG", "price_diesel_pvp"), ("DGEG", "price_gasoline_95_pvp")]},
    {"name": "Inflação + Salários + Emprego", "indicators": [
        ("INE", "hicp_yoy"), ("INE", "wages_industry_cae"), ("INE", "emp_industry_cae")]},
    {"name": "Euribor 3m + 6m + 12m", "indicators": [
        ("BPORTUGAL", "euribor_3m"), ("BPORTUGAL", "euribor_6m"), ("BPORTUGAL", "euribor_12m")]},
    {"name": "BTN Simples + Inflação + Euribor", "indicators": [
        ("ERSE", "btn_simple"), ("INE", "hicp_yoy"), ("BPORTUGAL", "euribor_12m")]},
    # Energia
    {"name": "Eólica + Solar + Hídrica", "indicators": [
        ("REN", "electricity_wind"), ("REN", "electricity_solar"), ("REN", "electricity_hydro")]},
    {"name": "MIBEL + Brent + Gás Natural", "indicators": [
        ("REN", "electricity_price_mibel"), ("FRED", "brent_oil"), ("FRED", "natural_gas")]},
    {"name": "Renovável % + Dependência Energética", "indicators": [
        ("DGEG", "pct_renewable_real"), ("DGEG", "energy_dependence")]},
    {"name": "Produção Total + Consumo + Importações", "indicators": [
        ("REN", "electricity_production_total"), ("REN", "electricity_consumption"), ("REN", "electricity_net_imports")]},
    # Indústria
    {"name": "IPI Total + Emprego Indústria", "indicators": [
        ("INE", "ipi_seasonal_cae_TOT"), ("INE", "emp_industry_cae")]},
    {"name": "IPI Automóvel + IPI Química + IPI Metalurgia", "indicators": [
        ("INE", "ipi_seasonal_cae_29"), ("INE", "ipi_seasonal_cae_20"), ("INE", "ipi_seasonal_cae_24")]},
    {"name": "Cobre + Alumínio + IPI Metalurgia", "indicators": [
        ("FRED", "copper"), ("FRED", "aluminum"), ("INE", "ipi_seasonal_cae_24")]},
    {"name": "IPI PT (INE) vs IPI PT (Eurostat)", "indicators": [
        ("INE", "ipi_seasonal_cae_TOT"), ("EUROSTAT", "ipi_total")]},
    # Conjuntura
    {"name": "CLI + Confiança + Carteira Encomendas", "indicators": [
        ("OECD", "cli"), ("INE", "conf_manufacturing"), ("OECD", "order_books")]},
    {"name": "Desemprego + PIB Trimestral", "indicators": [
        ("EUROSTAT", "unemployment"), ("EUROSTAT", "gdp_quarterly")]},
    {"name": "Spread PT-DE + Dívida Pública + Défice", "indicators": [
        ("BPORTUGAL", "spread_pt_de"), ("EUROSTAT", "gov_debt_pct_gdp"), ("EUROSTAT", "gov_deficit_pct_gdp")]},
    # Internacional
    {"name": "PIB per capita PT vs Emprego vs I&D", "indicators": [
        ("WORLDBANK", "gdp_per_capita_ppp"), ("WORLDBANK", "employment_rate"), ("WORLDBANK", "rnd_pct_gdp")]},
    {"name": "Brent + EUR/USD + Spread", "indicators": [
        ("FRED", "brent_oil"), ("BPORTUGAL", "eur_usd"), ("BPORTUGAL", "spread_pt_de")]},
    # Commodities
    {"name": "Ouro + Cobre + Trigo", "indicators": [
        ("FRED", "commodity_iron_ore"), ("FRED", "copper"), ("FRED", "wheat")]},
    {"name": "Brent + Gás Natural + Carvão", "indicators": [
        ("FRED", "brent_oil"), ("FRED", "natural_gas"), ("DGEG", "consumption_coal")]},
    # Tarifas
    {"name": "Tarifa MT Ponta + AT Ponta + MAT Ponta", "indicators": [
        ("ERSE", "tariff_mt_peak"), ("ERSE", "tariff_at_peak"), ("ERSE", "tariff_mat_peak")]},
]


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_catalog():
    """Fetch indicator catalog from internal API."""
    with urllib.request.urlopen(f"{INTERNAL_API}/api/catalog") as r:
        return json.load(r)


def build_indicator_list(catalog):
    """Build flat list of all indicators."""
    indicators = []
    for src, info in catalog.items():
        for ind_id, meta in info.get("indicators", {}).items():
            indicators.append({
                "source": src,
                "id": ind_id,
                "label": meta.get("label", ""),
                "frequency": meta.get("frequency", ""),
                "unit": meta.get("unit", ""),
            })
    return indicators


def load_results():
    """Load previous results for resume support."""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return {"individual": {}, "combos": {}, "summary": {}}


def save_results(results):
    """Save results to disk."""
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def _wait_for_chart_or_error(page, timeout_s=30):
    """
    Wait for the Explorador to finish loading.
    Returns: ("chart", None) | ("error", "message") | ("timeout", None)

    The SPA has 3 terminal states after selecting an indicator:
      1. Chart rendered  → canvas element exists inside #explorador-chart
      2. Error           → .error-state div with message
      3. Empty           → .explorador-empty-state div (no data / no selection)
    While loading:
      → .loading-state div with "A carregar séries…"
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        state = page.evaluate("""() => {
            // IMPORTANT: scope all queries to #explorador section to avoid
            // picking up loading-state from other sections (e.g. #painel)
            const scope = document.getElementById('explorador') || document;

            // Check for error state first (e.g. "Erro HTTP 404 for …")
            const err = scope.querySelector('.error-state');
            if (err) return { state: 'error', msg: err.textContent.trim() };

            // Check for empty state
            const empty = scope.querySelector('.explorador-empty-state');
            if (empty) return { state: 'empty', msg: empty.textContent.trim() };

            // Check for chart canvas — chart renders inside #exp-chart-wrap > #exp-chart > canvas
            const c = scope.querySelector('#exp-chart-wrap canvas, #exp-chart canvas');
            if (c && c.width > 0 && c.height > 0) return { state: 'chart', msg: null };

            // Fallback: any canvas within explorador
            const anyCanvas = scope.querySelector('canvas');
            if (anyCanvas && anyCanvas.width > 0 && anyCanvas.height > 0) return { state: 'chart', msg: null };

            // Still loading
            return { state: 'loading', msg: null };
        }""")
        if state["state"] == "chart":
            return ("chart", None)
        if state["state"] == "error":
            return ("error", state["msg"])
        if state["state"] == "empty":
            # "Selecciona indicadores" means the hash didn't trigger selection
            if "Selecciona" in (state["msg"] or ""):
                return ("error", "Hash did not trigger indicator selection")
            return ("error", state["msg"] or "empty state")
        time.sleep(0.5)
    return ("timeout", None)


def _wait_for_ai(page, timeout_s=120):
    """
    Wait for AI analysis to complete.
    Returns: ("ready", False) | ("ready", True=cached) | ("timeout", False) | ("hidden", False)
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        ai_state = page.evaluate("""() => {
            // Scope to #explorador section
            const scope = document.getElementById('explorador') || document;
            const text = scope.textContent || '';
            if (text.includes('A gerar análise IA')) return 'loading';
            if (text.includes('Análise gerada:')) return 'ready';
            // Check for substantial AI content
            const aiPanel = scope.querySelector('[id*="ai-panel"]');
            if (aiPanel && aiPanel.textContent.trim().length > 100) return 'ready';
            return 'waiting';
        }""")
        if ai_state == "ready":
            return ("ready", False)
        if ai_state == "cached":
            return ("ready", True)
        if ai_state == "hidden":
            return ("hidden", False)
        time.sleep(1)
    return ("timeout", False)


MAX_RETRIES = 3  # Retry on transient Traefik 404s (router flapping during reconfig)


def _test_indicator_once(context, source, ind_id, label):
    """Single attempt to test an indicator. Returns result dict."""
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
        "chart": False,
        "ai_analysis": False,
        "ai_cached": False,
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    page = context.new_page()
    try:
        page.goto(hash_url, wait_until="networkidle", timeout=45000)

        # Wait for chip to appear (indicator loaded from hash)
        try:
            page.wait_for_selector(".indicator-chip", timeout=15000)
        except Exception:
            result["error"] = "Chip not loaded via hash"

        # Wait for chart or error
        chart_state, chart_msg = _wait_for_chart_or_error(page, timeout_s=MAX_CHART_WAIT)

        if chart_state == "chart":
            result["chart"] = True
        else:
            result["chart"] = False
            result["error"] = chart_msg or f"Chart did not render ({chart_state})"

        # Wait for AI analysis (only if chart rendered)
        if result["chart"]:
            ai_result, ai_cached = _wait_for_ai(page, timeout_s=MAX_AI_WAIT)
            if ai_result == "ready":
                result["ai_analysis"] = True
                result["ai_cached"] = ai_cached
            else:
                result["ai_analysis"] = False
                result["error"] = (result.get("error") or "") + f" AI: {ai_result}"

        # Determine final status
        if result["chart"] and result["ai_analysis"]:
            result["status"] = "OK"
        elif result["chart"] and not result["ai_analysis"]:
            result["status"] = "CHART_ONLY"
        else:
            result["status"] = "FAIL"

        # Screenshot on failure
        if result["status"] != "OK":
            safe_name = f"{source}_{ind_id}".replace("/", "_").replace("€", "EUR")
            ss_path = os.path.join(SCREENSHOTS_DIR, f"{safe_name}.png")
            try:
                page.screenshot(path=ss_path, full_page=True)
                result["screenshot"] = ss_path
            except Exception:
                pass

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:200]
    finally:
        page.close()

    return result


def test_indicator(context, source, ind_id, label, test_name=None):
    """
    Test an indicator with retries for transient Traefik 404s.
    Traefik's Docker provider flaps routers during reconfiguration triggered
    by healthcheck events, causing intermittent 404s routed to Hugo.
    """
    for attempt in range(MAX_RETRIES + 1):
        result = _test_indicator_once(context, source, ind_id, label)
        # Retry only on HTTP 404 errors (Traefik flapping), not on timeouts
        if result["status"] != "FAIL" or "HTTP 404" not in (result.get("error") or ""):
            break
        if attempt < MAX_RETRIES:
            log(f"  ↻ Retry {attempt+1}/{MAX_RETRIES} (transient 404)")
            time.sleep(3)  # Wait for Traefik reconfig to settle
    if test_name:
        result["test_name"] = test_name
    return result


def _test_combo_once(context, combo):
    """Single attempt to test a combo. Returns result dict."""
    indicators = combo["indicators"]
    name = combo["name"]
    s_param = ",".join(
        urllib.parse.quote(f"{src}/{ind}") for src, ind in indicators
    )
    hash_url = f"{APP_URL}#explorador?s={s_param}&from={DEFAULT_FROM}&to={DEFAULT_TO}"

    result = {
        "name": name,
        "indicators": [f"{s}/{i}" for s, i in indicators],
        "status": "UNKNOWN",
        "chart": False,
        "ai_analysis": False,
        "ai_cached": False,
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    page = context.new_page()
    try:
        page.goto(hash_url, wait_until="networkidle", timeout=45000)
        time.sleep(0.5)

        # Wait for chips
        try:
            page.wait_for_selector(".indicator-chip", timeout=10000)
        except Exception:
            result["error"] = "Chips not loaded"

        # Wait for chart or error
        chart_state, chart_msg = _wait_for_chart_or_error(page, timeout_s=MAX_CHART_WAIT)
        result["chart"] = chart_state == "chart"
        if not result["chart"]:
            result["error"] = chart_msg or f"Chart did not render ({chart_state})"

        # Wait for AI
        if result["chart"]:
            ai_result, ai_cached = _wait_for_ai(page, timeout_s=MAX_AI_WAIT)
            result["ai_analysis"] = ai_result == "ready"
            result["ai_cached"] = ai_cached
            if not result["ai_analysis"]:
                result["error"] = (result.get("error") or "") + f" AI: {ai_result}"

        result["status"] = "OK" if result["chart"] and result["ai_analysis"] else (
            "CHART_ONLY" if result["chart"] else "FAIL"
        )

        if result["status"] != "OK":
            safe_name = name.replace(" ", "_").replace("/", "_")[:60]
            ss_path = os.path.join(SCREENSHOTS_DIR, f"combo_{safe_name}.png")
            try:
                page.screenshot(path=ss_path, full_page=True)
                result["screenshot"] = ss_path
            except Exception:
                pass

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:200]
    finally:
        page.close()

    return result


def test_combo(context, combo):
    """Test a combo with retries for transient Traefik 404s."""
    for attempt in range(MAX_RETRIES + 1):
        result = _test_combo_once(context, combo)
        if result["status"] != "FAIL" or "HTTP 404" not in (result.get("error") or ""):
            break
        if attempt < MAX_RETRIES:
            log(f"  ↻ Retry {attempt+1}/{MAX_RETRIES} (transient 404)")
            time.sleep(3)
    return result


def main():
    parser = argparse.ArgumentParser(description="Prumo exhaustive indicator audit")
    parser.add_argument("--resume", type=int, default=0,
                        help="Resume from indicator index N (0-based)")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode")
    parser.add_argument("--skip-combos", action="store_true",
                        help="Skip combination tests")
    parser.add_argument("--only-combos", action="store_true",
                        help="Only run combination tests")
    args = parser.parse_args()

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # Clear log on fresh start
    if args.resume == 0 and not args.only_combos:
        with open(LOG_FILE, "w") as f:
            f.write("")

    log("=" * 60)
    log("PRUMO INDICATOR AUDIT — STARTING")
    log(f"Headless: {args.headless} | Resume from: {args.resume}")
    log("=" * 60)

    # Load catalog
    catalog = load_catalog()
    indicators = build_indicator_list(catalog)
    log(f"Loaded {len(indicators)} indicators from {len(catalog)} sources")
    log(f"Will also test {len(COMMON_COMBOS)} common pairs/trios")

    # Load previous results
    results = load_results()
    if "individual" not in results:
        results["individual"] = {}
    if "combos" not in results:
        results["combos"] = {}

    # Launch browser
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # Disable QUIC/HTTP3 — Traefik has intermittent router flapping
        # during Docker provider reconfigurations, and HTTP/3 connections are
        # disproportionately affected (67% fail rate vs 4% on HTTP/2).
        browser = p.chromium.launch(
            headless=args.headless,
            args=["--disable-quic"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="pt-PT",
        )
        # Each test_indicator/test_combo creates and closes its own page
        # to avoid SPA state leaks between indicators.

        # ── Phase 1: Individual indicators ──────────────────────────
        if not args.only_combos:
            total = len(indicators)
            ok = fail = chart_only = error = skipped = 0

            for i, ind in enumerate(indicators):
                if i < args.resume:
                    skipped += 1
                    continue

                key = f"{ind['source']}/{ind['id']}"

                # Skip if already tested successfully
                if key in results["individual"] and results["individual"][key].get("status") == "OK":
                    log(f"[{i+1}/{total}] SKIP (cached OK): {key}")
                    ok += 1
                    continue

                log(f"[{i+1}/{total}] Testing: {key} — {ind['label']}")

                r = test_indicator(context, ind["source"], ind["id"], ind["label"])
                results["individual"][key] = r

                if r["status"] == "OK":
                    ok += 1
                    cached_str = " (AI cached)" if r.get("ai_cached") else ""
                    log(f"[{i+1}/{total}] OK{cached_str}: {key}")
                elif r["status"] == "CHART_ONLY":
                    chart_only += 1
                    log(f"[{i+1}/{total}] CHART_ONLY (no AI): {key} — {r.get('error', '')}", "WARN")
                elif r["status"] == "FAIL":
                    fail += 1
                    log(f"[{i+1}/{total}] FAIL: {key} — {r.get('error', '')}", "ERROR")
                else:
                    error += 1
                    log(f"[{i+1}/{total}] ERROR: {key} — {r.get('error', '')}", "ERROR")

                # Save results every 10 indicators
                if (i + 1) % 10 == 0:
                    save_results(results)
                    log(f"── Progress: {i+1}/{total} | OK={ok} CHART_ONLY={chart_only} FAIL={fail} ERROR={error} ──")

            save_results(results)
            log("=" * 60)
            log(f"PHASE 1 COMPLETE — Individual indicators")
            log(f"Total={total} OK={ok} CHART_ONLY={chart_only} FAIL={fail} ERROR={error} SKIPPED={skipped}")
            log("=" * 60)

        # ── Phase 2: Common combinations ────────────────────────────
        if not args.skip_combos:
            total_combos = len(COMMON_COMBOS)
            combo_ok = combo_fail = 0

            for j, combo in enumerate(COMMON_COMBOS):
                name = combo["name"]

                # Skip if already tested OK
                if name in results["combos"] and results["combos"][name].get("status") == "OK":
                    log(f"[COMBO {j+1}/{total_combos}] SKIP (cached OK): {name}")
                    combo_ok += 1
                    continue

                log(f"[COMBO {j+1}/{total_combos}] Testing: {name}")
                log(f"  Indicators: {', '.join(f'{s}/{i}' for s,i in combo['indicators'])}")

                r = test_combo(context, combo)
                results["combos"][name] = r

                if r["status"] == "OK":
                    combo_ok += 1
                    log(f"[COMBO {j+1}/{total_combos}] OK: {name}")
                else:
                    combo_fail += 1
                    log(f"[COMBO {j+1}/{total_combos}] {r['status']}: {name} — {r.get('error', '')}", "WARN")

                save_results(results)

            log("=" * 60)
            log(f"PHASE 2 COMPLETE — Combinations")
            log(f"Total={total_combos} OK={combo_ok} FAIL={combo_fail}")
            log("=" * 60)

        # ── Summary ─────────────────────────────────────────────────
        ind_results = results.get("individual", {})
        combo_results = results.get("combos", {})

        summary = {
            "timestamp": datetime.now().isoformat(),
            "individual": {
                "total": len(ind_results),
                "ok": sum(1 for v in ind_results.values() if v["status"] == "OK"),
                "chart_only": sum(1 for v in ind_results.values() if v["status"] == "CHART_ONLY"),
                "fail": sum(1 for v in ind_results.values() if v["status"] == "FAIL"),
                "error": sum(1 for v in ind_results.values() if v["status"] == "ERROR"),
            },
            "combos": {
                "total": len(combo_results),
                "ok": sum(1 for v in combo_results.values() if v["status"] == "OK"),
                "fail": sum(1 for v in combo_results.values() if v["status"] != "OK"),
            },
            "failures": [
                {"key": k, "status": v["status"], "error": v.get("error")}
                for k, v in ind_results.items()
                if v["status"] not in ("OK",)
            ],
        }
        results["summary"] = summary
        save_results(results)

        log("=" * 60)
        log("FINAL SUMMARY")
        log(f"Individual: {summary['individual']}")
        log(f"Combos: {summary['combos']}")
        if summary["failures"]:
            log(f"Failures ({len(summary['failures'])}):")
            for f in summary["failures"]:
                log(f"  {f['key']}: {f['status']} — {f.get('error', '')}")
        log("=" * 60)

        browser.close()

    log("AUDIT COMPLETE")


if __name__ == "__main__":
    main()
