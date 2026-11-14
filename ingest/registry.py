"""Indicator registry: YAML -> validated SeriesSpec list -> DB sync."""
import json
from collections import Counter
from pathlib import Path

import yaml
from pydantic import ValidationError

from ingest.db import Db
from ingest.derive import formula_label_pt
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
    rows = doc.get("derived") or []
    if not isinstance(rows, list):
        raise ValueError("derived: section must be a list")
    derived, seen = [], set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"derived[{i}]: entry must be a mapping")
        try:
            d = DerivedSpec(**row)
        except (ValidationError, TypeError) as e:
            raise ValueError(f"{row.get('key', f'derived[{i}]')}: invalid entry: {e}") from e
        if d.key in seen:
            raise ValueError(f"{d.key}: duplicate key")
        seen.add(d.key)
        if not d.key.startswith("derived.") or d.key == "derived.":
            raise ValueError(f"{d.key}: key must start with 'derived.' plus a name")
        if d.key in by_id:
            raise ValueError(f"{d.key}: key equals a series id")
        base = by_id.get(d.base)
        if base is None:
            raise ValueError(f"{d.key}: unknown base {d.base!r}")
        if d.active and not base.active:
            raise ValueError(f"{d.key}: active entry on inactive base {d.base!r}")
        if base.frequency not in ("M", "Q", "A"):
            raise ValueError(f"{d.key}: base frequency {base.frequency!r} unsupported (M/Q/A only)")
        if base.decimal != ".":
            raise ValueError(f"{d.key}: base decimal separator {base.decimal!r} unsupported")
        _validate_params(d, base.frequency)
        derived.append(d)
    return derived


def _validate_params(d: DerivedSpec, frequency: str) -> None:
    if d.formula != "rebase_100":
        if d.params:
            raise ValueError(f"{d.key}: formula {d.formula!r} takes no params")
        return
    if set(d.params) != {"base_period"}:
        raise ValueError(f"{d.key}: rebase_100 needs exactly params {{base_period}}")
    period = d.params["base_period"]
    try:
        ok = normalize_period(period, frequency) == period
    except ValueError:
        ok = False
    if not ok:
        raise ValueError(f"{d.key}: base_period {period!r} is not a canonical {frequency} period")


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


def sync_derived(db: Db, derived: list[DerivedSpec]) -> None:
    """Sync the WHOLE `derived:` list (absent keys become inactive), with the formula label."""
    db.upsert_derived_series([
        {"key": d.key, "formula": d.formula, "base_series_id": d.base,
         "params_json": json.dumps(d.params, sort_keys=True), "label": d.label,
         "formula_label_pt": formula_label_pt(d.formula, d.params, d.base), "unit": d.unit,
         "active": d.active}
        for d in derived])


def sync_registry(db: Db, specs: list[SeriesSpec]) -> None:
    db.upsert_source_and_series(
        [s.source.model_dump() for s in {s.source.name: s for s in specs}.values()],
        [{**s.model_dump(exclude={"source", "schedule", "throttle_rps"}), "source_name": s.source.name}
         for s in specs],
    )
