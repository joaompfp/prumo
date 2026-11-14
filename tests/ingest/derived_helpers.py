"""Shared test helpers for the derived layer (project 3)."""
from ingest.models import DerivedSpec, Observation


def verified_values(db, sid: str, values: dict[str, str], fetched_at: str, key: str, *,
                    source: str = "fake") -> int:
    """One verified fetched vintage of `sid` (period -> value_text) written straight through
    Db, exactly like `_direct_verified` in test_task20_serving.py. Returns the run id."""
    run = db.begin_run(source, key, fetched_at)
    fid = db.record_raw_fetch(source_name=source, run_id=run, url="http://x", params_json=None,
                              fetched_at=fetched_at, http_status=200,
                              sha256=f"sha-{key}", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(sid, p, v), fid, fetched_at)
                                for p, v in values.items()])
    db.set_run_state(run, "verified")
    return run


def derived_spec(key: str, base: str, formula: str, **kw) -> DerivedSpec:
    kw.setdefault("label", f"Derivada {key}")
    kw.setdefault("unit", "%" if formula.endswith("_pct") else "EUR")
    return DerivedSpec(key=key, base=base, formula=formula, **kw)
