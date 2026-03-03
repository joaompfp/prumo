from ..constants import CATALOG, FRED_SERIES, WB_CODES


def compute_yoy(series):
    """Given a sorted list of {period, value}, compute YoY change for latest point.
    Handles both YYYY-MM (monthly) and YYYY (annual) period formats.
    For monthly: tries annual entry of prev year first (handles mixed ERSE series),
      then exact same month prev year, then +/-5 months fallback.
    For annual: looks for prev year annual entry directly."""
    if not series:
        return None
    latest = series[-1]
    if latest["value"] is None:
        return None
    try:
        period = latest["period"]
        period_map = {pt["period"]: pt for pt in series if pt["value"] is not None}

        if "-" not in period:
            # Annual period (YYYY) — strictly look for YYYY-1 entry only.
            # If the predecessor is YYYY-2 or older (data gap/lag), return None to avoid
            # misleading multi-year variation presented as YoY.
            prev_key = str(int(period) - 1)
            if prev_key in period_map:
                prev_val = period_map[prev_key]["value"]
                if prev_val and prev_val != 0:
                    return round((latest["value"] - prev_val) / abs(prev_val) * 100, 1)
            # Predecessor not found at YYYY-1 → data has a gap (e.g. lag of 2+ years).
            # Do NOT fall back to YYYY-2 or older — that would be a biennual variation.
            return None

        # Monthly period (YYYY-MM)
        yr, mo = period.split("-")
        yr, mo = int(yr), int(mo)
        prev_yr = yr - 1

        # B5 FIX: for mixed YYYY / YYYY-MM series (e.g. ERSE semi-annual tariff revisions),
        # try the annual entry of prev year FIRST — gives the correct year-over-year reference
        # (e.g. '2024-06' compares to '2023' annual, not to '2023-07' mid-year revision).
        # Safe for pure monthly series (INE, BPORTUGAL, OECD): they have no YYYY entries
        # in period_map, so the lookup fails and falls through to the monthly search.
        prev_annual = str(prev_yr)
        if prev_annual in period_map:
            prev_val = period_map[prev_annual]["value"]
            if prev_val and prev_val != 0:
                return round((latest["value"] - prev_val) / abs(prev_val) * 100, 1)

        # Build month candidates: exact, then adjacent months.
        # FIX 2: limit fallback to ±2 months to avoid comparing periods >14 months apart
        # (which would be biennual/multi-month, not true YoY). ±5 months was too permissive.
        month_candidates = [mo]
        for delta in range(1, 3):  # try up to +/-2 months only (10–14 month window)
            m_plus  = mo + delta
            m_minus = mo - delta
            if 1 <= m_plus  <= 12: month_candidates.append(m_plus)
            if 1 <= m_minus <= 12: month_candidates.append(m_minus)

        for m in month_candidates:
            target = f"{prev_yr}-{m:02d}"
            if target in period_map:
                prev_val = period_map[target]["value"]
                if prev_val and prev_val != 0:
                    return round((latest["value"] - prev_val) / abs(prev_val) * 100, 1)
    except:
        pass
    return None


def compute_trend(series, n=6):
    """Count consecutive months of increase/decrease at tail of series."""
    if len(series) < 2:
        return "flat", 0
    direction = None
    count = 0
    for i in range(len(series)-1, 0, -1):
        curr = series[i]["value"]
        prev = series[i-1]["value"]
        if curr is None or prev is None:
            break
        d = "up" if curr > prev else ("down" if curr < prev else "flat")
        if direction is None:
            direction = d
        if d == direction:
            count += 1
        else:
            break
        if count >= n:
            break
    return direction or "flat", count


def spark_data(series, n=12):
    """Return last n data points as {period, value} dicts for sparklines."""
    return [{"period": pt["period"], "value": pt["value"]}
            for pt in series[-n:] if pt["value"] is not None]


def trend_text(label, desc, last_val, prev_val, unit):
    if prev_val is None or prev_val == 0:
        return {"label": label, "text": f"{desc}: {last_val:.2f} {unit}.", "trend": "flat"}
    pct = (last_val - prev_val) / abs(prev_val) * 100
    direction = "subiu" if pct > 0 else "desceu"
    trend = "up" if pct > 0 else "down"
    abs_pct = abs(pct)
    return {
        "label": label,
        "text": f"{desc} {direction} {abs_pct:.1f}% face ao mês anterior ({last_val:.2f} vs {prev_val:.2f} {unit}).",
        "trend": trend
    }


def shift_period(period, months):
    """Shift YYYY-MM period by `months` months."""
    try:
        y, m = int(period[:4]), int(period[5:7])
        total = y * 12 + m - 1 + months
        ny, nm = divmod(total, 12)
        return f"{ny:04d}-{nm+1:02d}"
    except Exception:
        return period


def find_period(rows, target_period):
    """Find row with period == target, or None."""
    for r in reversed(rows):
        if r["period"] == target_period:
            return r
    return None


def label_for(source, indicator):
    return CATALOG.get(source, {}).get("indicators", {}).get(indicator, {}).get("label", indicator)


def unit_for(source, indicator):
    return CATALOG.get(source, {}).get("indicators", {}).get(indicator, {}).get("unit", "")


def source_url_for(source: str, indicator: str) -> str:
    """Return the best URL for a given source+indicator pair."""
    if source == "EUROSTAT":
        return "https://ec.europa.eu/eurostat/databrowser/"
    elif source == "INE":
        return "https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_BD_tema"
    elif source == "FRED":
        series = FRED_SERIES.get(indicator)
        if series:
            return f"https://fred.stlouisfed.org/series/{series}"
        return f"https://fred.stlouisfed.org/series/{indicator.upper()}"
    elif source == "WORLDBANK":
        code = WB_CODES.get(indicator)
        if code:
            return f"https://data.worldbank.org/indicator/{code}"
        return "https://data.worldbank.org/"
    elif source == "BPORTUGAL":
        return "https://www.bportugal.pt/estatisticas/dados"
    elif source == "OECD":
        return "https://stats.oecd.org/"
    elif source == "REN":
        return "https://datahub.ren.pt/app/pt/producao/"
    elif source == "ERSE":
        return "https://www.erse.pt/"
    elif source == "DGEG":
        return "https://www.dgeg.gov.pt/media/"
    return ""
