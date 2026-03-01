from datetime import datetime

from ..database import fetch_series
from ..constants import CATALOG, BRIEFING_INDICATORS, SUMMARY_INDICATORS
from .helpers import label_for, unit_for, shift_period, find_period, trend_text


def build_briefing():
    items = []
    for source, indicator in BRIEFING_INDICATORS:
        try:
            rows = fetch_series(source, indicator)
            if len(rows) < 2:
                continue
            # filter out None/NaN values
            rows = [r for r in rows if r["value"] is not None]
            if len(rows) < 2:
                continue

            current = rows[-1]
            previous = rows[-2]
            cur_val  = float(current["value"])
            prev_val = float(previous["value"])

            mom_pct = ((cur_val - prev_val) / abs(prev_val) * 100) if prev_val != 0 else 0.0

            # YoY: find row closest to 12 months ago
            cur_period = current["period"]
            yoy_period = shift_period(cur_period, -12)
            yoy_row = find_period(rows, yoy_period)
            yoy_pct = None
            if yoy_row:
                yoy_val = float(yoy_row["value"])
                if yoy_val != 0:
                    yoy_pct = (cur_val - yoy_val) / abs(yoy_val) * 100

            label = label_for(source, indicator)
            unit  = unit_for(source, indicator)

            # Last 12 months sparkline data
            spark = [{"period": r["period"], "value": float(r["value"])} for r in rows[-13:]]

            # Simple historical context
            mom_abs = abs(mom_pct)
            historical_max = max(abs((float(rows[i]["value"]) - float(rows[i-1]["value"])) / abs(float(rows[i-1]["value"])) * 100)
                                 for i in range(1, len(rows)-1) if float(rows[i-1]["value"]) != 0) if len(rows) > 2 else 0
            context = None
            if mom_abs > 0 and len(rows) > 24:
                if mom_abs > historical_max * 0.9:
                    context = f"Maior variação mensal dos últimos {len(rows)} meses"
                elif mom_abs > historical_max * 0.5:
                    context = f"Variação acima da mediana histórica"

            items.append({
                "source": source,
                "indicator": indicator,
                "label": label,
                "current_value": cur_val,
                "previous_value": prev_val,
                "mom_pct": round(mom_pct, 2),
                "yoy_pct": round(yoy_pct, 2) if yoy_pct is not None else None,
                "unit": unit,
                "period": current["period"],
                "trend": "up" if mom_pct > 0 else ("down" if mom_pct < 0 else "flat"),
                "context": context,
                "spark": spark,
            })
        except Exception:
            continue

    # Sort by |MoM| desc
    items.sort(key=lambda x: abs(x["mom_pct"]), reverse=True)

    # Counter-trends: MoM and YoY point opposite directions
    counter = [
        it for it in items
        if it["yoy_pct"] is not None
        and it["mom_pct"] != 0
        and it["yoy_pct"] != 0
        and (it["mom_pct"] > 0) != (it["yoy_pct"] > 0)
    ][:3]

    highlights = [it for it in items if it not in counter][:5]

    # Latest period
    latest = items[0]["period"] if items else "N/A"

    return {
        "period": latest,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "highlights": highlights,
        "counter_trends": counter,
    }


def build_summary():
    items = []
    latest_period = None

    for source, indicator, label, desc in SUMMARY_INDICATORS:
        try:
            rows = fetch_series(source, indicator)
            if len(rows) < 1:
                continue
            last = rows[-1]
            prev = rows[-2] if len(rows) >= 2 else None
            if latest_period is None:
                latest_period = last["period"]

            meta = CATALOG.get(source, {}).get("indicators", {}).get(indicator, {})
            unit = meta.get("unit", last.get("unit", ""))

            item = trend_text(
                label, desc,
                float(last["value"]),
                float(prev["value"]) if prev else None,
                unit
            )
            items.append(item)
        except Exception:
            continue

    return {"period": latest_period or "N/A", "items": items}
