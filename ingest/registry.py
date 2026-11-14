"""Indicator registry: YAML -> validated SeriesSpec list -> DB sync."""
from collections import Counter
from pathlib import Path

import yaml

from ingest.db import Db
from ingest.models import SeriesSpec, SourceSpec


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
