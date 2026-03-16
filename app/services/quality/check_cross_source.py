"""Check 8: cross-source consistency — compare overlapping indicators across sources."""

_CROSS_SOURCE_PAIRS = [
    # (src_a, ind_a, src_b, ind_b, label, max_divergence)
    ("EUROSTAT", "unemployment", "OECD", "unemp_m", "unemployment rate", 2.0),
]


def _check_cross_source(conn) -> list:
    """Compare overlapping indicators across sources — flag divergences."""
    issues = []
    for src_a, ind_a, src_b, ind_b, label, max_div in _CROSS_SOURCE_PAIRS:
        try:
            rows_a = conn.execute(
                "SELECT period, value FROM indicators "
                "WHERE source=? AND indicator=? AND region='PT' "
                "ORDER BY period DESC LIMIT 6",
                [src_a, ind_a]
            ).fetchall()
            rows_b = conn.execute(
                "SELECT period, value FROM indicators "
                "WHERE source=? AND indicator=? AND region='PT' "
                "ORDER BY period DESC LIMIT 6",
                [src_b, ind_b]
            ).fetchall()
        except Exception:
            continue
        map_b = {r[0]: r[1] for r in rows_b}
        for period, val_a in rows_a:
            val_b = map_b.get(period)
            if val_a is not None and val_b is not None:
                diff = abs(val_a - val_b)
                if diff > max_div:
                    issues.append({
                        "source": f"{src_a}+{src_b}", "indicator": label,
                        "severity": "warning", "check": "cross_source",
                        "msg": f"period {period}: {src_a}={val_a}, {src_b}={val_b}, diff={diff:.1f}pp",
                    })
                break  # Only check most recent overlapping period
    return issues
