"""Check 6: spike detection — month-over-month spikes >3σ from rolling mean."""

from ...constants import CATALOG


def _check_spikes(conn) -> list:
    """Detect month-over-month spikes >3σ from rolling mean in monthly PT series."""
    issues = []
    for src, src_info in CATALOG.items():
        for ind, meta in src_info.get("indicators", {}).items():
            if meta.get("frequency") != "monthly":
                continue
            try:
                rows = conn.execute(
                    "SELECT period, value FROM indicators "
                    "WHERE source=? AND indicator=? AND region='PT' "
                    "ORDER BY period",
                    [src, ind]
                ).fetchall()
            except Exception:
                continue
            vals = [r[1] for r in rows if r[1] is not None]
            if len(vals) < 12:
                continue
            # Rolling mean and std over last 12 values
            window = vals[-12:]
            mean = sum(window) / len(window)
            std = (sum((v - mean) ** 2 for v in window) / len(window)) ** 0.5
            if std == 0:
                continue
            # Check last 3 values for spikes
            for r in rows[-3:]:
                if r[1] is None:
                    continue
                z = abs(r[1] - mean) / std
                if z > 3:
                    issues.append({
                        "source": src, "indicator": ind,
                        "severity": "warning", "check": "spike",
                        "msg": f"period {r[0]}: value {r[1]} is {z:.1f}σ from 12m mean {mean:.2f}",
                    })
    return issues
