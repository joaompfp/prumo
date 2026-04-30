"""Check 5: region_coverage — key regions present for comparativos indicators."""

_KEY_REGIONS = {
    "EUROSTAT":  ["PT", "DE", "FR", "ES", "EU27"],
    "WORLDBANK": ["PT", "US", "BR", "DE"],
}

# EU27 and EU27_2020 are different Eurostat codes for the same aggregate
_EU27_EQUIV = frozenset(["EU27", "EU27_2020"])


def _region_present(region: str, available: set) -> bool:
    """Check presence, treating EU27 and EU27_2020 as equivalent."""
    if region in available:
        return True
    if region in _EU27_EQUIV:
        return bool(available & _EU27_EQUIV)
    return False


def _check_region_coverage(conn) -> list:
    """For comparativos indicators, verify key regions are present in DB."""
    from ...constants.compare_catalog import COMPARATIVOS_CATALOG

    issues = []
    region_cache: dict[tuple, set] = {}

    for entry in COMPARATIVOS_CATALOG:
        src = entry.get("source")
        ind = entry.get("indicator")
        if not src or not ind or entry.get("mode") == "legacy":
            continue
        if src not in _KEY_REGIONS:
            continue

        key = (src, ind)
        if key not in region_cache:
            try:
                rows = conn.execute(
                    "SELECT DISTINCT region FROM indicators WHERE source=? AND indicator=?",
                    [src, ind]
                ).fetchall()
                region_cache[key] = {r[0] for r in rows}
            except Exception:
                region_cache[key] = set()

        available = region_cache[key]
        missing = [r for r in _KEY_REGIONS[src] if not _region_present(r, available)]
        if missing:
            issues.append({
                "source": src, "indicator": ind,
                "severity": "warning", "check": "region_coverage",
                "msg": f"missing key regions: {', '.join(missing)}",
            })

    return issues
