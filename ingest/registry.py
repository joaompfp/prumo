"""Indicator registry: YAML -> validated SeriesSpec list -> DB sync."""
from collections import Counter
from pathlib import Path

import yaml

from ingest.db import Db
from ingest.models import DerivedSpec, SeriesSpec, SourceSpec, normalize_period


def load_registry(path: Path) -> list[SeriesSpec]:
    doc = yaml.safe_load(Path(path).read_text()) or {}
    sources = {name: SourceSpec(name=name, **(body or {}))
               for name, body in (doc.get("sources") or {}).items()}
    specs = []
    for row in doc.get("series") or []:
        row = dict(row)
        name = row.pop("source", None)
        if name not in sources:
            raise ValueError(f"series {row.get('id')!r}: unknown source {name!r}")
        specs.append(SeriesSpec(source=sources[name], **row))
    _validate(specs)
    return specs


def load_derived(path: Path, specs: list[SeriesSpec]) -> list[DerivedSpec]:
    """The top-level `derived:` list, validated against the loaded series (absent -> [])."""
    doc = yaml.safe_load(Path(path).read_text()) or {}
    by_id = {s.id: s for s in specs}
    derived, seen = [], set()
    for row in doc.get("derived") or []:
        d = DerivedSpec(**row)
        if d.key in seen:
            raise ValueError(f"derived {d.key!r}: duplicate key")
        seen.add(d.key)
        if not d.key.startswith("derived."):
            raise ValueError(f"derived {d.key!r}: key must start with 'derived.'")
        if d.key in by_id:
            raise ValueError(f"derived {d.key!r}: key equals a series id")
        base = by_id.get(d.base)
        if base is None:
            raise ValueError(f"derived {d.key!r}: unknown base {d.base!r}")
        if d.active and not base.active:
            raise ValueError(f"derived {d.key!r}: active entry on inactive base {d.base!r}")
        if base.frequency not in ("M", "Q", "A"):
            raise ValueError(f"derived {d.key!r}: base frequency {base.frequency!r} unsupported (M/Q/A only)")
        if base.decimal != ".":
            raise ValueError(f"derived {d.key!r}: base decimal separator {base.decimal!r} unsupported")
        _validate_params(d, base.frequency)
        derived.append(d)
    return derived


def _validate_params(d: DerivedSpec, frequency: str) -> None:
    if d.formula != "rebase_100":
        if d.params:
            raise ValueError(f"derived {d.key!r}: formula {d.formula!r} takes no params")
        return
    if set(d.params) != {"base_period"}:
        raise ValueError(f"derived {d.key!r}: rebase_100 needs exactly params {{base_period}}")
    period = d.params["base_period"]
    try:
        ok = normalize_period(period, frequency) == period
    except ValueError:
        ok = False
    if not ok:
        raise ValueError(f"derived {d.key!r}: base_period {period!r} is not a canonical {frequency} period")


def _validate(specs: list[SeriesSpec]) -> None:
    dup = [i for i, n in Counter(s.id for s in specs).items() if n > 1]
    if dup:
        raise ValueError(f"duplicate series id: {dup}")
    # One active series per (source, native_code): several adapters map rows by spec, so two
    # active specs pinning one code would silently receive identical rows (final review C-M6).
    codes = Counter((s.source.name, s.native_code) for s in specs
                    if s.active and s.native_code is not None)
    shared = sorted(k for k, n in codes.items() if n > 1)
    if shared:
        raise ValueError(f"active series share a native_code within a source: {shared}")
    primaries = Counter(s.indicator_key for s in specs if s.role == "primary")
    for key in {s.indicator_key for s in specs}:
        if primaries[key] != 1:
            raise ValueError(f"indicator {key!r} needs exactly one primary series, has {primaries[key]}")


def sync_registry(db: Db, specs: list[SeriesSpec]) -> None:
    db.upsert_source_and_series(
        [s.source.model_dump() for s in {s.source.name: s for s in specs}.values()],
        [{**s.model_dump(exclude={"source", "schedule", "throttle_rps"}), "source_name": s.source.name}
         for s in specs],
    )
