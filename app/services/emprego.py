from ..database import get_db, fetch_series
from ..constants import COMPARE_COUNTRIES
from .helpers import compute_yoy


def build_emprego():
    """Build /api/emprego response.

    v5 additions:
    - employment_rate multi-country (EUROSTAT) for PT, EU27_2020, DE, ES, FR, PL
    - employment_rate WorldBank multi-country
    - female_labor_participation WorldBank
    - consumer_confidence / CCI EUROSTAT EU27
    - productivity_gap = employment_rate PT / unemployment_rate PT  x gdp_per_capita ratio
    """
    result = {}

    # 1. Industrial employment (INE)
    rows = fetch_series("INE", "emp_industry_cae")
    if rows:
        series = [{"period": r["period"], "value": r["value"]} for r in rows]
        result["industrial_employment"] = {
            "data": series,
            "latest": series[-1]["value"] if series else None,
            "yoy": compute_yoy(series),
        }

    # 2. Unemployment PT (OECD — monthly, best coverage) — stored for later countries merge
    _pt_unemp_rows = fetch_series("OECD", "unemp_m")
    _pt_unemp_series = (
        [{"period": r["period"], "value": r["value"]} for r in _pt_unemp_rows]
        if _pt_unemp_rows else []
    )

    # 3. Wages (INE)
    rows = fetch_series("INE", "wages_industry_cae")
    if rows:
        wage_series = [{"period": r["period"], "value": r["value"]} for r in rows]
        result["wages"] = {
            "data": wage_series,
            "latest": wage_series[-1]["value"] if wage_series else None,
            "yoy": compute_yoy(wage_series),
        }

    # 4. Inflation (for real wages calc)
    rows = fetch_series("INE", "hicp_yoy")
    if rows:
        result["inflation"] = [{"period": r["period"], "value": r["value"]} for r in rows]

    # 5. Confidence (INE manufacturing)
    rows = fetch_series("INE", "conf_manufacturing")
    if rows:
        series = [{"period": r["period"], "value": r["value"]} for r in rows]
        result["confidence"] = {
            "data": series,
            "latest": series[-1]["value"] if series else None,
        }

    # 6. OECD employment indicator
    rows = fetch_series("OECD", "employment")
    if rows:
        result["oecd_employment"] = [{"period": r["period"], "value": r["value"]} for r in rows]

    # ── V5: Employment rate multi-country (EUROSTAT) ──────────────────────────
    EMPREGO_PEERS = ["PT", "EU27_2020", "DE", "ES", "FR", "PL"]
    conn = get_db()
    try:
        # Employment rate — EUROSTAT, annual, multi-country
        emp_rows = conn.execute("""
            SELECT region, period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='employment_rate'
            AND region IN ('PT','EU27_2020','DE','ES','FR','PL')
            ORDER BY region, period
        """).fetchall()

        # EU27 unemployment monthly % — region='EU27' (312 rows 2000-2025, % format)
        unemp_eu27_m_rows = conn.execute("""
            SELECT period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='unemployment'
              AND region='EU27'
            ORDER BY period
        """).fetchall()

        # Unemployment rate — EUROSTAT, multi-country (for productivity gap calc)
        unemp_eu_rows = conn.execute("""
            SELECT region, period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='unemployment'
            AND region IN ('PT','EU27_2020','DE','ES','FR','PL')
            ORDER BY region, period
        """).fetchall()

        # GDP per capita EUR — EUROSTAT, for productivity gap
        gdp_pc_rows = conn.execute("""
            SELECT region, period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator='gdp_per_capita_eur'
            AND region IN ('PT','EU27_2020','EU27')
            ORDER BY region, period
        """).fetchall()

        # WorldBank employment rate (employment to population ratio)
        wb_emp_rows = conn.execute("""
            SELECT region, period, value FROM indicators
            WHERE source='WORLDBANK' AND indicator='employment_rate'
            AND region IN ('PT','DE','ES','FR','PL','EU')
            ORDER BY region, period
        """).fetchall()

        # WorldBank female labor participation
        female_rows = conn.execute("""
            SELECT region, period, value FROM indicators
            WHERE source='WORLDBANK' AND indicator='female_labor_participation'
            AND region IN ('PT','DE','ES','FR','PL','EU')
            ORDER BY region, period
        """).fetchall()

        # Consumer confidence — EUROSTAT (CCI / consumer_confidence)
        cci_rows = conn.execute("""
            SELECT region, period, value FROM indicators
            WHERE source='EUROSTAT' AND indicator IN ('consumer_confidence','cci')
            AND region IN ('PT','EU27_2020','EU27')
            ORDER BY region, period
        """).fetchall()
    finally:
        conn.close()

    # Group employment_rate by region
    emp_by_region: dict = {}
    for region, period, value in emp_rows:
        emp_by_region.setdefault(region, []).append({"period": period, "value": value})

    result["employment_rate"] = {
        "label": "Taxa de Emprego (20-64 anos, %)",
        "unit": "%",
        "source": "EUROSTAT",
        "frequency": "anual",
        "countries": {
            r: {
                "label": COMPARE_COUNTRIES.get(r, r),
                "data": emp_by_region.get(r, []),
                "latest": emp_by_region[r][-1]["value"] if emp_by_region.get(r) else None,
                "yoy": compute_yoy(emp_by_region[r]) if emp_by_region.get(r) else None,
            }
            for r in EMPREGO_PEERS
        }
    }

    # Group EUROSTAT unemployment by region
    unemp_by_region: dict = {}
    for region, period, value in unemp_eu_rows:
        unemp_by_region.setdefault(region, []).append({"period": period, "value": value})

    result["unemployment_eu"] = {
        "label": "Taxa de Desemprego (%)",
        "unit": "%",
        "source": "EUROSTAT",
        "countries": {
            r: {
                "label": COMPARE_COUNTRIES.get(r, r),
                "data": unemp_by_region.get(r, []),
                "latest": unemp_by_region[r][-1]["value"] if unemp_by_region.get(r) else None,
            }
            for r in EMPREGO_PEERS if r in unemp_by_region
        }
    }

    # Unemployment — countries structure: PT (OECD monthly %) + EU27_2020 (EUROSTAT monthly %)
    # Prefer unemployment_m (312 monthly rows 2000-2025); fall back to annual (16 rows)
    if unemp_eu27_m_rows:
        _eu27_unemp_series = [{"period": p, "value": v} for p, v in unemp_eu27_m_rows]
    else:
        _eu27_unemp_series = unemp_by_region.get("EU27_2020", [])
    result["unemployment"] = {
        "label": "Taxa de Desemprego (%)",
        "unit": "%",
        "countries": {
            "PT": {
                "data": _pt_unemp_series,
                "latest": _pt_unemp_series[-1]["value"] if _pt_unemp_series else None,
            },
            "EU27_2020": {
                "data": _eu27_unemp_series,
                "latest": _eu27_unemp_series[-1]["value"] if _eu27_unemp_series else None,
            },
        },
    }

    # WorldBank employment rate
    wb_emp_by_region: dict = {}
    for region, period, value in wb_emp_rows:
        wb_emp_by_region.setdefault(region, []).append({"period": period, "value": value})
    if wb_emp_by_region:
        result["employment_rate_wb"] = {
            "label": "Taxa de Emprego — World Bank (%)",
            "unit": "%",
            "source": "WORLDBANK",
            "countries": {
                r: {"label": COMPARE_COUNTRIES.get(r, r), "data": wb_emp_by_region[r]}
                for r in wb_emp_by_region
            }
        }

    # Female labor participation
    female_by_region: dict = {}
    for region, period, value in female_rows:
        female_by_region.setdefault(region, []).append({"period": period, "value": value})
    if female_by_region:
        result["female_labor_participation"] = {
            "label": "Taxa de Participação Feminina no Mercado de Trabalho (%)",
            "unit": "%",
            "source": "WORLDBANK",
            "countries": {
                r: {"label": COMPARE_COUNTRIES.get(r, r), "data": female_by_region[r]}
                for r in female_by_region
            }
        }

    # Consumer confidence EU27 (CCI)
    cci_by_region: dict = {}
    for region, period, value in cci_rows:
        cci_by_region.setdefault(region, []).append({"period": period, "value": value})
    if cci_by_region:
        result["consumer_confidence_eu"] = {
            "label": "Confiança dos Consumidores — UE (saldo)",
            "unit": "saldo",
            "source": "EUROSTAT",
            "countries": {
                r: {"label": COMPARE_COUNTRIES.get(r, r), "data": cci_by_region[r]}
                for r in cci_by_region
            }
        }

    # ── Productivity Gap (Paradoxo) ───────────────────────────────────────────
    # productivity_gap = PT employment_rate / PT unemployment_rate correlated with GDP per capita ratio PT/EU27
    try:
        pt_emp_series  = emp_by_region.get("PT", [])
        pt_unemp_series = unemp_by_region.get("PT", [])

        # GDP per capita ratio PT / EU27
        gdp_by_region: dict = {}
        for region, period, value in gdp_pc_rows:
            gdp_by_region.setdefault(region, {})[period] = value

        gdp_pt  = gdp_by_region.get("PT", {})
        gdp_eu  = gdp_by_region.get("EU27_2020", gdp_by_region.get("EU27", {}))

        # Align periods for all three series
        pt_unemp_map = {r["period"][:4]: r["value"] for r in pt_unemp_series if r["value"]}
        pt_emp_map   = {r["period"][:4]: r["value"] for r in pt_emp_series   if r["value"]}

        gap_data = []
        for year in sorted(set(pt_emp_map) & set(pt_unemp_map) & set(gdp_pt) & set(gdp_eu)):
            emp_val   = pt_emp_map[year]
            unemp_val = pt_unemp_map[year]
            gdp_ratio = (gdp_pt[year] / gdp_eu[year] * 100) if gdp_eu.get(year) else None
            # Ratio: employment_rate / unemployment_rate — high = good employment structure
            emp_unemp_ratio = round(emp_val / unemp_val, 2) if unemp_val else None
            gap_data.append({
                "period":           year,
                "employment_rate":  emp_val,
                "unemployment_rate":unemp_val,
                "emp_unemp_ratio":  emp_unemp_ratio,
                "gdp_pc_ratio_eu":  round(gdp_ratio, 1) if gdp_ratio else None,
            })

        result["productivity_gap"] = {
            "label": "Paradoxo Emprego-Produtividade PT",
            "description": (
                "Portugal tem emprego elevado face ao desemprego "
                "(ratio emp/unemp > UE média), mas GDP per capita "
                "permanece 25-30% abaixo da média UE27 — "
                "indiciando baixa produtividade estrutural."
            ),
            "data": gap_data,
            "latest": gap_data[-1] if gap_data else None,
        }
    except Exception as e:
        result["productivity_gap"] = {"error": str(e)}

    return result
