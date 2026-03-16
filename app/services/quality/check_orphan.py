"""Check 2: orphan_db — indicators in DB with no catalog entry."""

from ...constants import CATALOG

# Legacy Eurostat dataset codes that are intentionally un-cataloged
_LEGACY_PREFIXES = ("STS_INPR_M_",)
# Sources that are entirely multi-region and don't need catalog entries per-indicator
_SKIP_ORPHAN_SOURCES: set[str] = set()


def _check_orphan_db(db_stats_all: dict) -> list:
    """Find indicators in DB that have no catalog entry — they show raw codes in Ficha."""
    catalog_keys = {
        (src, ind)
        for src, src_info in CATALOG.items()
        for ind in src_info.get("indicators", {})
    }
    issues = []
    for (src, ind), stats in sorted(db_stats_all.items()):
        if (src, ind) in catalog_keys:
            continue
        if src in _SKIP_ORPHAN_SOURCES:
            continue
        if any(ind.startswith(p) for p in _LEGACY_PREFIXES):
            continue
        issues.append({
            "source": src, "indicator": ind,
            "severity": "warning", "check": "orphan_db",
            "msg": (
                f"{stats['cnt']} rows, {stats['n_regions']} region(s), "
                f"{stats['since']}–{stats['until']} — no catalog entry, shows raw code in Ficha"
            ),
        })
    return issues
