import csv
import io
import json

import duckdb
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..constants import CHART_EVENTS, CATALOG
from ..database import get_db, fetch_series
from ..services.resumo import build_resumo
from ..services.painel import build_painel
from ..services.industria import build_industria
from ..services.energia import build_energia
from ..services.emprego import build_emprego
from ..services.macro import build_macro
from ..services.fosso import build_fosso
from ..services.produtividade import build_produtividade
from ..services.explorador import build_explorador_catalog
from ..services.series import query_series, query_compare
from ..services.mundo import get_mundo_data, MUNDO_INDICATORS, COUNTRY_GROUPS_MUNDO
from ..services.briefing import build_briefing, build_summary

router = APIRouter(prefix="/api")


# ── Active endpoints ─────────────────────────────────────────────────


@router.get("/resumo")
def api_resumo():
    return build_resumo()


@router.get("/painel")
def api_painel():
    """KPIs organized into 5 thematic sections (Custo de Vida, Emprego, Conjuntura, Energia, Externo)."""
    return build_painel()


@router.get("/series")
def api_series(
    source: str = Query(None, alias="source"),
    sources: str = Query(None),
    indicator: str = Query(None, alias="indicator"),
    indicators: str = Query(None),
    from_period: str = Query(None, alias="from"),
    to_period: str = Query(None, alias="to"),
):
    src_list = []
    ind_list = []
    if source:
        src_list = [source]
    elif sources:
        src_list = [s.strip() for s in sources.split(",")]
    if indicator:
        ind_list = [indicator]
    elif indicators:
        ind_list = [i.strip() for i in indicators.split(",")]
    if not src_list or not ind_list:
        return JSONResponse(status_code=400, content={"error": "source and indicator are required"})
    return query_series(src_list, ind_list, from_period, to_period)


@router.get("/compare")
def api_compare(
    dataset: str = Query("manufacturing"),
    countries: str = Query("PT,ES,DE,FR,EU27"),
    months: int = Query(24),
    indicator: str = Query(None),
    source: str = Query("EUROSTAT"),
    since: str = Query(None),
):
    return query_compare(dataset, countries, months, indicator, source, since)



@router.get("/mundo")
def api_mundo(
    indicator: str = Query("unemployment"),
    source: str = Query("EUROSTAT"),
    countries: str = Query("PT,ES,GR,CZ,HU,PL,RO,SK"),
    since: str = Query(None),
    to: str = Query(None),
):
    """PT vs Mundo comparison endpoint. Uses same DB backend as /api/compare."""
    return get_mundo_data(indicator, source, countries, since, to)


@router.get("/mundo/meta")
def api_mundo_meta():
    """Return available indicators and country groups for mundo section."""
    return {
        "indicators": MUNDO_INDICATORS,
        "country_groups": COUNTRY_GROUPS_MUNDO,
    }


@router.post("/interpret")
async def interpret_endpoint(request: Request):
    """Call Claude Haiku (with web search) to interpret chart series data."""
    from ..services.interpret import interpret_chart
    body = await request.json()
    result = interpret_chart(body.get("series", []), body.get("from", ""), body.get("to", ""))
    if not result:
        return {"text": None, "links": [], "model": None}
    if isinstance(result, str):  # backward compat
        return {"text": result, "links": [], "model": "claude-haiku-4-5-20251001"}
    return {"text": result.get("text"), "links": result.get("links", []), "model": "claude-haiku-4-5-20251001"}


@router.get("/painel-analysis")
async def painel_analysis_endpoint(request: Request):
    """Sonnet one-shot analysis of all Painel KPIs. Disk-cached per data period."""
    from ..services.painel import build_painel
    from ..services.painel_analysis import get_painel_analysis
    force = request.query_params.get("force") == "1"
    data = build_painel()
    sections = data.get("sections", [])
    updated = data.get("updated", "")
    return get_painel_analysis(sections, updated, force=force)


@router.get("/compare-catalog")
def api_compare_catalog(request: Request):
    """
    Return the multi-country indicator catalog for PT vs Europa or PT vs Mundo.
    Entries not present in the DB are silently filtered out.
    Query param: section=europa (default) | mundo
    """
    from ..constants.compare_catalog import EUROPA_CATALOG, MUNDO_CATALOG
    section = request.query_params.get("section", "europa")
    catalog = EUROPA_CATALOG if section == "europa" else MUNDO_CATALOG

    try:
        conn = get_db()
        present = set(conn.execute(
            "SELECT DISTINCT source, indicator FROM indicators"
        ).fetchall())
    except Exception:
        present = None  # DB unavailable — return full catalog

    result = []
    for entry in catalog:
        mode = entry.get("mode", "db")
        if mode == "legacy":
            result.append(entry)  # legacy entries not in DB — always include
        elif present is None or (entry.get("source"), entry.get("indicator")) in present:
            result.append(entry)

    return result


@router.get("/comparativos/catalog")
def api_comparativos_catalog():
    """Return the full Comparativos indicator catalog.
    All COMPOSITE entries always included. EUROSTAT/WORLDBANK entries filtered
    to those actually present in the DB.
    """
    from ..constants.compare_catalog import COMPARATIVOS_CATALOG
    from ..services.series import COMPOSITE_INDICATORS

    try:
        conn = get_db()
        present = set(conn.execute(
            "SELECT DISTINCT source, indicator FROM indicators"
        ).fetchall())
        conn.close()
    except Exception:
        present = None

    result = []
    for entry in COMPARATIVOS_CATALOG:
        src = entry.get("source")
        ind = entry.get("indicator")
        if src == "COMPOSITE":
            if ind in COMPOSITE_INDICATORS:
                result.append(entry)
        elif src is None or entry.get("mode") == "legacy":
            result.append(entry)
        elif present is None or (src, ind) in present:
            result.append(entry)

    return result


@router.get("/comparativos/countries")
def api_comparativos_countries(source: str = Query("EUROSTAT"), indicator: str = Query("unemployment")):
    """Return list of country codes that have data for the given indicator.
    For COMPOSITE indicators, returns the union of EU27 (Eurostat) + WorldBank countries.
    """
    from ..services.series import COMPOSITE_INDICATORS, EU27_CODES, EU_AGGREGATES

    try:
        conn = get_db()
        if source == "COMPOSITE":
            comp = COMPOSITE_INDICATORS.get(indicator, {})
            eu_src, eu_ind = comp.get("eu", (None, None))
            w_src, w_ind   = comp.get("world", (None, None))
            countries = set()
            if eu_src:
                rows = conn.execute(
                    "SELECT DISTINCT region FROM indicators WHERE source=? AND indicator=?",
                    [eu_src, eu_ind]
                ).fetchall()
                countries.update(r[0] for r in rows)
            if w_src:
                rows = conn.execute(
                    "SELECT DISTINCT region FROM indicators WHERE source=? AND indicator=?",
                    [w_src, w_ind]
                ).fetchall()
                countries.update(r[0] for r in rows)
        else:
            rows = conn.execute(
                "SELECT DISTINCT region FROM indicators WHERE source=? AND indicator=?",
                [source, indicator]
            ).fetchall()
            countries = {r[0] for r in rows}
        conn.close()
    except Exception:
        countries = set()

    return sorted(countries)


@router.get("/comparativos/data")
def api_comparativos_data(
    source: str = Query("COMPOSITE"),
    indicator: str = Query("unemployment"),
    countries: str = Query("PT,ES,DE"),
    since: str = Query(None),
):
    """Comparison data endpoint supporting COMPOSITE, EUROSTAT, and WORLDBANK sources."""
    from ..services.series import query_composite, COMPOSITE_INDICATORS

    if source == "COMPOSITE":
        if indicator not in COMPOSITE_INDICATORS:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=400, content={"error": f"Unknown composite: {indicator}"})
        return query_composite(indicator, countries, since)

    # Regular single-source: delegate to existing query_compare
    return query_compare(None, countries, 0, indicator=indicator, source=source, since_yr=since)


@router.get("/catalog")
def api_catalog():
    try:
        conn = get_db()
        try:
            db_stats = {}
            rows = conn.execute("""
                SELECT source, indicator, COUNT(DISTINCT region) as regions,
                       MIN(period) as since, MAX(period) as until, COUNT(*) as rows
                FROM indicators GROUP BY source, indicator
            """).fetchall()
            for src, ind, regions, since, until, cnt in rows:
                db_stats.setdefault(src, {})[ind] = {
                    "region_count": regions, "since": since, "until": until, "rows": cnt
                }
        finally:
            conn.close()
        enriched = {}
        for src, src_info in CATALOG.items():
            enriched[src] = dict(src_info)
            enriched[src]["indicators"] = {}
            for ind, ind_info in src_info.get("indicators", {}).items():
                merged = dict(ind_info)
                if src in db_stats and ind in db_stats[src]:
                    merged.update(db_stats[src][ind])
                enriched[src]["indicators"][ind] = merged
        return enriched
    except Exception:
        return CATALOG


@router.get("/quality")
def api_quality():
    """Data quality report: catalog drift, orphan indicators, freshness, flatlines, region coverage."""
    from ..services.quality import run_quality_checks
    return run_quality_checks()


@router.get("/explorador")
def api_explorador():
    return build_explorador_catalog()


@router.get("/events")
def api_events():
    return CHART_EVENTS


@router.get("/data")
def api_data():
    try:
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT source, indicator, period, value, unit
                FROM indicators
                WHERE source NOT IN ('DGEG', 'ERSE')
                ORDER BY source, indicator, period
            """).fetchall()
            result = {}
            for source, indicator, period, value, unit in rows:
                result.setdefault(source, {}).setdefault(indicator, []).append(
                    {"period": period, "value": value, "unit": unit}
                )
        finally:
            conn.close()
        return result
    except duckdb.Error as e:
        return JSONResponse(status_code=503, content={"error": f"database error: {e}"})


@router.get("/kpis")
def api_kpis():
    try:
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT source, indicator, value, unit, period, MAX(period)
                FROM indicators
                WHERE source NOT IN ('DGEG', 'ERSE')
                GROUP BY source, indicator
            """).fetchall()
            result = {}
            for source, indicator, value, unit, period, _ in rows:
                result.setdefault(source, {})[indicator] = {
                    "value": value, "unit": unit, "period": period,
                }
        finally:
            conn.close()
        return result
    except duckdb.Error as e:
        return JSONResponse(status_code=503, content={"error": f"database error: {e}"})


# ── New v7 endpoints ─────────────────────────────────────────────────


@router.post("/track")
async def api_track(request: Request):
    """Track embed loads and other events."""
    try:
        body = await request.json()
        from ..analytics import log_event
        log_event(
            event=body.get("event", "unknown"),
            host=body.get("host", request.headers.get("origin", "")),
            path=body.get("path", ""),
            extra=json.dumps(body.get("extra")) if body.get("extra") else None,
        )
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.get("/stats")
def api_stats(
    event_type: str = Query(None),
    since: float = Query(None),
    limit: int = Query(100),
    mode: str = Query("count"),
):
    """Query analytics data. mode=count returns event counts, mode=list returns events."""
    from ..analytics import query_stats, count_stats
    if mode == "list":
        return query_stats(event_type, since, limit)
    return count_stats(event_type, since)


@router.get("/export")
def api_export(
    sources: str = Query(...),
    indicators: str = Query(...),
    from_period: str = Query(None, alias="from"),
    to_period: str = Query(None, alias="to"),
):
    """Export time series data as CSV."""
    src_list = [s.strip() for s in sources.split(",")]
    ind_list = [i.strip() for i in indicators.split(",")]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["source", "indicator", "period", "value", "unit"])

    for src in src_list:
        for ind in ind_list:
            rows = fetch_series(src, ind, from_period, to_period)
            for r in rows:
                writer.writerow([src, ind, r["period"], r["value"], r["unit"]])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cae-export.csv"},
    )


# ── Deprecated endpoints (OpenClaw backward compat) ──────────────────
# These add X-CAE-Deprecated header to signal deprecation


def _deprecated(data):
    """Wrap response with deprecation header."""
    resp = JSONResponse(content=data)
    resp.headers["X-CAE-Deprecated"] = "true"
    return resp


@router.get("/industria")
def api_industria(period: int = Query(5)):
    return _deprecated(build_industria(period))


@router.get("/europa")
def api_europa(
    dataset: str = Query("manufacturing"),
    countries: str = Query("PT,ES,DE,FR,EU27"),
    months: int = Query(24),
    indicator: str = Query(None),
    source: str = Query("EUROSTAT"),
    since: str = Query(None),
):
    return _deprecated(query_compare(dataset, countries, months, indicator, source, since))


@router.get("/energia")
def api_energia():
    return _deprecated(build_energia())


@router.get("/emprego")
def api_emprego():
    return _deprecated(build_emprego())


@router.get("/macro")
def api_macro():
    return _deprecated(build_macro())


@router.get("/fosso")
def api_fosso():
    return _deprecated(build_fosso())


@router.get("/produtividade")
def api_produtividade():
    return _deprecated(build_produtividade())


@router.get("/briefing")
def api_briefing():
    return _deprecated(build_briefing())


@router.get("/summary")
def api_summary():
    return _deprecated(build_summary())
