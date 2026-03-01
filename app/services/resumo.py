from ..database import get_db
from ..constants import CATALOG, UNIT_OVERRIDES
from .helpers import compute_yoy, compute_trend, spark_data


def resumo_kpi(kpi_id, label, source, indicator, detail_filter=None, invert_sentiment=False, scale_factor=1.0, unit_override=None):
    """Build a single KPI card for /api/resumo.
    scale_factor: multiply stored value by this (e.g. 100 for ratio→% conversion).
    unit_override: force a unit string regardless of what DB returns.
    """
    try:
        conn = get_db(source)
        try:
            sql = "SELECT period, value, unit FROM indicators WHERE source=? AND indicator=? ORDER BY period"
            params = [source, indicator]
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        finally:
            conn.close()

        if detail_filter:
            # Re-query with detail filter
            conn = get_db(source)
            try:
                sql = "SELECT period, value, unit FROM indicators WHERE source=? AND indicator=? AND detail LIKE ? ORDER BY period"
                params = [source, indicator, f"%{detail_filter}%"]
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
            finally:
                conn.close()

        if not rows:
            return {"id": kpi_id, "label": label, "error": "no data"}

        series = [{"period": r[0], "value": r[1], "unit": r[2]} for r in rows]
        latest = series[-1]

        # Saldo/index/rate indicators — show absolute pp change, not % change
        # Applies to: confidence (saldo), cli (OECD index ~100), order_books (saldo)
        #             euribor_* (interest rates in % — pp delta is the meaningful metric)
        _PP_INDICATORS = ("confidence", "cli", "order_books", "euribor_3m", "euribor_6m", "euribor_12m")
        if kpi_id in _PP_INDICATORS:
            yoy = None
            if len(series) >= 13:
                try:
                    yr, mo = latest["period"].split("-")
                    target = f"{int(yr)-1}-{mo}"
                    for pt in series:
                        if pt["period"] == target and pt["value"] is not None:
                            yoy = round(latest["value"] - pt["value"], 2)  # absolute pp
                            break
                except:
                    pass
        else:
            yoy = compute_yoy(series)

        # Detect stale annual data: period is year-only AND strictly before current year
        # (e.g. "2023" is stale; "2026" is current year's annual tariff — not stale)
        _period_str = latest["period"] or ""
        try:
            from datetime import datetime as _dt
            is_annual_period = len(_period_str) == 4 and int(_period_str) < _dt.now().year
        except:
            is_annual_period = False

        trend_dir, trend_months = compute_trend(series)
        spark = spark_data(series)

        # Apply scale factor (e.g. ratio→% conversion: 0.63 → 63)
        display_value = latest["value"]
        display_spark = spark
        if scale_factor != 1.0 and display_value is not None:
            display_value = round(display_value * scale_factor, 2)
            display_spark = [round(v * scale_factor, 2) if v is not None else None for v in spark]

        # Round excessively precise floats to 2 decimal places for display
        if display_value is not None and isinstance(display_value, float):
            display_value = round(display_value, 2)
        display_spark = [round(v, 2) if isinstance(v, float) else v for v in display_spark]

        # Bug 3: apply human-readable unit overrides; then caller's unit_override takes precedence
        raw_unit = latest["unit"] or ""
        unit = unit_override if unit_override is not None else UNIT_OVERRIDES.get(raw_unit, raw_unit)

        # Determine sentiment (good/bad)
        if yoy is not None:
            if invert_sentiment:
                sentiment = "negative" if yoy > 0 else ("positive" if yoy < 0 else "neutral")
            else:
                sentiment = "positive" if yoy > 0 else ("negative" if yoy < 0 else "neutral")
        else:
            sentiment = "neutral"

        # Build context phrase
        context = ""
        if is_annual_period:
            # Annual data: suppress misleading "X.º mês consecutivo" — show data vintage
            context = f"Dados de {latest['period']} (última actualização disponível)"
        elif kpi_id == "industrial_production" and latest["value"] is not None:
            vs_base = round(latest["value"] - 100, 1)
            direction = "abaixo" if vs_base < 0 else "acima"
            context = f"{abs(vs_base):.1f}% {direction} do nível base (2021=100)"
        elif kpi_id in ("confidence", "order_books"):
            # Saldo indicators: show pp change + note if still negative
            if yoy is not None:
                sign = "+" if yoy >= 0 else ""
                context = f"{sign}{yoy:.1f} pp face ao ano anterior"
                if latest["value"] is not None and latest["value"] < 0:
                    context += " (ainda negativo)"
        elif kpi_id == "cli":
            if yoy is not None:
                sign = "+" if yoy >= 0 else ""
                context = f"{sign}{yoy:.1f} pp face ao ano anterior"
        elif kpi_id in ("euribor_3m", "euribor_6m", "euribor_12m"):
            # Rate indicators: show pp change with month reference (e.g. "descida de 0.97 pp desde dezembro 2024")
            if yoy is not None:
                try:
                    from datetime import datetime as _dt
                    import calendar
                    yr_prev = int(latest["period"][:4]) - 1
                    mo_prev = int(latest["period"][5:7])
                    month_names_pt = ["janeiro","fevereiro","março","abril","maio","junho",
                                      "julho","agosto","setembro","outubro","novembro","dezembro"]
                    month_name = month_names_pt[mo_prev - 1]
                    direction = "descida" if yoy < 0 else "subida"
                    context = f"{direction} de {abs(yoy):.2f} pp desde {month_name} {yr_prev}"
                except:
                    sign = "+" if yoy >= 0 else ""
                    context = f"{sign}{yoy:.2f} pp face ao ano anterior"
        elif invert_sentiment and trend_dir == "up" and yoy is not None and yoy < 0 and trend_months >= 3:
            # Conflict: trend going up (bad) but YoY is down (good for invert indicators)
            # Show YoY to avoid confusing "em subida" with green sentiment
            context = f"Desceu {abs(yoy):.1f}% face ao ano anterior (tendência recente: subida)"
        elif trend_months >= 3:
            verb = "subida" if trend_dir == "up" else "queda" if trend_dir == "down" else "estável"
            context = f"{trend_months}.º mês consecutivo em {verb}"
        elif yoy is not None:
            context = f"{'Subiu' if yoy > 0 else 'Desceu'} {abs(yoy):.1f}% face ao ano anterior"

        # Saldo/index/rate indicators display yoy in pp
        _PP_DISPLAY = ("confidence", "cli", "order_books", "euribor_3m", "euribor_6m", "euribor_12m")
        yoy_display_unit = "pp" if kpi_id in _PP_DISPLAY else None

        return {
            "id": kpi_id,
            "label": label,
            "value": display_value,
            "unit": unit,
            "period": latest["period"],
            "yoy": yoy,
            "yoy_unit": yoy_display_unit,
            "trend": trend_dir,
            "trend_months": trend_months,
            "sentiment": sentiment,
            "context": context,
            "spark": display_spark,
        }
    except Exception as e:
        return {"id": kpi_id, "label": label, "error": str(e)}


def build_resumo():
    """Build /api/resumo response with 8 KPIs."""
    kpis = [
        # Bug 5: use sector-specific indicator (complete data)
        resumo_kpi("industrial_production", "Produção Industrial",
                     "INE", "ipi_seasonal_cae_TOT"),
        resumo_kpi("unemployment", "Desemprego",
                     "OECD", "unemp_m", invert_sentiment=True),
        resumo_kpi("inflation", "Inflação",
                     "INE", "hicp_yoy", invert_sentiment=True),
        resumo_kpi("energy_cost", "Custo Energia",
                     "REN", "electricity_price_mibel", invert_sentiment=True),
        resumo_kpi("industrial_employment", "Emprego Industrial",
                     "INE", "emp_industry_cae", detail_filter='"dim_3": "C"'),
        resumo_kpi("confidence", "Confiança Industrial",
                     "INE", "conf_manufacturing"),
        resumo_kpi("euribor_12m", "Euribor 12 meses",
                     "BPORTUGAL", "euribor_12m", invert_sentiment=True),
        resumo_kpi("diesel", "Gasóleo",
                     "DGEG", "price_diesel", invert_sentiment=True),
    ]
    # Find most recent period across all KPIs
    periods = [k.get("period", "") for k in kpis if k.get("period")]
    updated = max(periods) if periods else ""
    return {"updated": updated, "kpis": kpis}
