"""One-off import of the legacy `indicators` export (CSV, Ruling U) as `legacy-unverified` rows.

Every CSV row lands in exactly one bucket: imported, quarantined (reason from `ingest.validate`,
or `missing_unit` when an otherwise valid row has a blank unit), or skipped as `not_in_registry`. Legacy rows go to one synthetic `verified` run per source
(dataset_key `legacy:<source>`) and are never served unless the `legacy_served` setting is '1'.
Re-running is a no-op: rows already present in that run are not written again (Ruling E).
"""
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ingest.db import Db
from ingest.models import SeriesSpec
from ingest.registry import load_registry, sync_registry
from ingest.validate import RawRow, Rejection, validate

DEFAULT_REGISTRY = Path(__file__).parents[1] / "registry" / "core.yaml"
NOT_IN_REGISTRY = "not_in_registry"
# Legacy-only reason (Ruling V): a blank legacy unit is never replaced by the registry unit, since
# unitless legacy rows can be another base-year vintage. The live pipeline's validate() still treats
# a blank unit as "the source did not say".
MISSING_UNIT = "missing_unit"

# Legacy-only reason (Task 10 review, finding I3): the legacy store's INE exports/imports rows for
# 2005-01..2024-12 are in MILLION euros filed under unit 'EUR' — live INE publishes EUR, and the
# registry unit 'EUR' is correct for the live data. Multiplying legacy cells by 10^6 would be
# fabricating data, so those rows are quarantined instead (and never served, like every legacy
# row). Generic table: series id -> (first period, last period, quarantine reason), endpoints
# INCLUSIVE, compared on normalized periods. ids are keyed exactly like the registry.
SUSPECT_UNIT_SCALE = "suspect_unit_scale"
LEGACY_SUSPECT_SCALE = {
    "ine.exports_monthly.PT": ("2005-01", "2024-12", SUSPECT_UNIT_SCALE),
    "ine.imports_monthly.PT": ("2005-01", "2024-12", SUSPECT_UNIT_SCALE),
}

# The legacy store filed the same geography under several labels.
_REGION_ALIASES = {"Portugal": "PT", "GLOBAL": "WORLD"}


def legacy_geography(source: str, region: str) -> str:
    """Registry geography of a legacy (source, region)."""
    if source == "FRED":
        # Every legacy FRED row is a global commodity price, filed under PT, GLOBAL or WORLD.
        return "WORLD"
    return _REGION_ALIASES.get(region, region)


def legacy_series_id(source: str, indicator: str, region: str) -> str:
    """Registry series id of a legacy (source, indicator, region) key."""
    return f"{source.lower()}.{indicator}.{legacy_geography(source, region)}"


@dataclass(frozen=True)
class LegacyImportReport:
    """What this call did: rows newly imported, rows newly quarantined by reason, and rows
    skipped as `not_in_registry` (counted on every call; nothing is written for them)."""
    n_imported: int
    n_quarantined_by_reason: dict[str, int] = field(default_factory=dict)


def fetched_at_utc(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    # Naive legacy timestamps were written by the collectors on f0nix in UTC.
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def import_legacy(db: Db, csv_path: Path, registry: list[SeriesSpec] | None = None) -> LegacyImportReport:
    specs = load_registry(DEFAULT_REGISTRY) if registry is None else registry
    by_id = {s.id: s for s in specs}
    sync_registry(db, specs)

    counts: Counter = Counter()
    pending: dict[str, list[tuple[datetime, SeriesSpec, RawRow]]] = defaultdict(list)
    with Path(csv_path).open(newline="") as f:
        for r in csv.DictReader(f):
            spec = by_id.get(legacy_series_id(r["source"], r["indicator"], r["region"]))
            if spec is None:
                counts[NOT_IN_REGISTRY] += 1
                continue
            pending[spec.source.name].append(
                (fetched_at_utc(r["fetched_at"]), spec, RawRow(r["period"], r["value"], r["unit"])))

    now = _iso_z(datetime.now(timezone.utc))
    n_imported = 0
    with db.transaction():
        for source in sorted(pending):
            run_id = db.legacy_run(source, f"legacy:{source}", now)
            have_obs = db.legacy_observation_keys(run_id)
            have_q = db.quarantine_keys(run_id)
            new_obs, new_q = [], defaultdict(list)
            # Oldest fetch first: the latest vintage of a (series, period) gets the highest id.
            for fetched, spec, raw in sorted(pending[source], key=lambda t: t[0]):
                fetched_at = _iso_z(fetched)
                accepted, rejected = validate(spec, [raw])
                scale = LEGACY_SUSPECT_SCALE.get(spec.id)
                if scale and accepted and scale[0] <= accepted[0].period <= scale[1]:
                    accepted, rejected = [], [Rejection(raw.period_raw, raw.value_raw, scale[2])]
                elif accepted and not raw.unit_raw.strip():
                    accepted, rejected = [], [Rejection(raw.period_raw, raw.value_raw, MISSING_UNIT)]
                for o in accepted:
                    key = (o.series_id, o.period, o.value_text, fetched_at)
                    if key not in have_obs:
                        have_obs.add(key)
                        new_obs.append((o, fetched_at))
                for rej in rejected:
                    # Compared with what earlier calls wrote only: the quarantine table has no
                    # fetched_at, so identical rows from two legacy fetches are both kept.
                    if (spec.id, rej.period_raw, rej.value_raw, rej.reason) not in have_q:
                        new_q[spec.id].append(rej)
                        counts[rej.reason] += 1
            db.write_legacy_observations(run_id, new_obs)
            for series_id, rejections in new_q.items():
                db.write_quarantine(run_id, series_id, rejections, now)
            n_imported += len(new_obs)
    return LegacyImportReport(n_imported, dict(counts))
