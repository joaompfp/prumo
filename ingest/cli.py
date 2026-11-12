"""Command line interface for Prumo base-data operations (Task 17A).

    python -m ingest [--db P] [--raw-dir D] [--registry Y] <command>

    run <source|all> [--dry-run]   fresh fetch + verification through run_with_refetch ONLY;
                                   World Bank runs one isolated dataset per indicator, so one
                                   indicator's outage never blocks the healthy others; a
                                   failing source/group never stops the rest; exit 1 if any
                                   ACTIVE, verifiable source did not verify
    status [--json]                typed report from Db records: per source/series latest
                                   attempt, last REAL verification, the retained data's genuine
                                   retrieval date, staleness (our refresh policy), event
                                   totals, pending-verification runs
    verify <run_id>                verify ONE existing pending-verification run with the
                                   verifier registered for its source (this command exists to
                                   resolve a specific pending run; normal flows never call it)
    import-legacy <csv>            import the legacy CSV export (Ruling U - NOT the old DuckDB
                                   store); legacy rows stay legacy-unverified and keep their
                                   original retrieval dates
    replay --from YYYY-MM          fresh re-fetch of every source through run_with_refetch;
                                   the cutoff scopes ONLY E-REDES' explicit day window
                                   ([<month>-01T00:00:00+00:00, today UTC day start)); other
                                   sources always fetch their full native window, so missing
                                   vintages are NOT recreated; legacy rows/runs are untouched

argparse/printing ONLY: domain work lives in ingest.operations / ingest.verify /
ingest.legacy_import / ingest.status; SQL lives in ingest.db.
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

from ingest import operations
from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.legacy_import import DEFAULT_REGISTRY, import_legacy
from ingest.operations import RunReport, RunRequest, run_all
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.status import build_status, render_text
from ingest.verifiers import get_verifier
from ingest.verify import verify_run

_MONTH = re.compile(r"[0-9]{4}-[0-9]{2}")  # ASCII digits only
DEFAULT_CLIENT_TIMEOUT_S = 30.0


def _default_db() -> str:
    return os.environ.get("PRUMO_DB", "/data/prumo.sqlite3")


def _default_raw() -> str:
    return os.environ.get("PRUMO_RAW_DIR", "/data/raw")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m ingest",
        description="Prumo base-data operations (run/status/verify/import-legacy/replay).")
    p.add_argument("--db", help="SQLite database (default: $PRUMO_DB or /data/prumo.sqlite3)")
    p.add_argument("--raw-dir", help="raw evidence store (default: $PRUMO_RAW_DIR or /data/raw)")
    p.add_argument("--registry", help=f"registry YAML (default: {DEFAULT_REGISTRY})")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="fresh fetch+verify of one source or all (see module help)")
    r.add_argument("source", help="registry source name, or 'all'")
    r.add_argument("--dry-run", action="store_true",
                   help="isolate: a throwaway DB/raw store under TMPDIR; --db/--raw-dir are "
                        "never opened")

    s = sub.add_parser("status", help="operational status report (read-only)")
    s.add_argument("--json", dest="as_json", action="store_true", help="typed JSON report")

    v = sub.add_parser("verify", help="verify ONE existing pending-verification run id "
                                      "(normal runs never use this)")
    v.add_argument("run_id", type=int, help="dataset_run.id in state pending-verification")

    i = sub.add_parser("import-legacy", help="import the legacy indicators CSV export "
                                             "(Ruling U)")
    i.add_argument("csv", help="path to the indicators.csv-style export (NOT a DuckDB file)")

    rp = sub.add_parser(
        "replay",
        help="fresh re-fetch of all sources; --from scopes ONLY the E-REDES day window "
             "([<month>-01 UTC day start, today UTC day start)); other sources fetch their "
             "full native window and missing vintages are NOT recreated; legacy untouched")
    rp.add_argument("--from", dest="from_month", required=True, metavar="YYYY-MM",
                    help="catch-up month (strict ASCII; not in the future)")
    rp.add_argument("--dry-run", action="store_true",
                    help="isolate: a throwaway DB/raw store under TMPDIR")
    return p


def _check_month(text: str) -> str:
    """A canonical YYYY-MM month, ASCII digits, a real month, not in the future."""
    if not _MONTH.fullmatch(text):
        raise ValueError(f"--from must be an ASCII YYYY-MM month, got {text!r}")
    year, month = int(text[:4]), int(text[5:])
    if not 1 <= month <= 12:
        raise ValueError(f"--from month out of range: {text!r}")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if (year, month) > (now.year, now.month):
        raise ValueError(f"--from {text!r} is in the future (now {now:%Y-%m}); refusing a "
                         f"cutoff that would skip unseen data")
    return text


def _http_for(specs, name=None):
    """CLI default Http factory: per-source polite client - min registry throttle (default
    1 rps), the registry timeout_s (INE 300; client default otherwise) and NO client retries
    (0: retry budgets must not multiply the bounded run_with_refetch attempts)."""
    active = [s for s in specs if s.active and (name is None or s.source.name == name)]
    throttle = min((s.throttle_rps for s in active), default=1.0)
    timeouts = {s.source.timeout_s for s in active}
    timeout = None if timeouts == {None} else max(t for t in timeouts if t is not None)
    return RequestsHttp(throttle_rps=throttle,
                        timeout=timeout or DEFAULT_CLIENT_TIMEOUT_S, retries=0)


def _print_report(report: RunReport, out) -> None:
    for source, outcomes in report.by_source().items():
        states = sorted(o.state for o in outcomes)
        head = "verified" if states == ["verified"] * len(states) else \
            "partial" if "verified" in states else states[0] if len(states) == 1 else "failed"
        print(f"{source}: {head}", file=out)
        for o in outcomes:
            bits = f"  {o.group}: {o.state}"
            if o.run_id is not None:
                bits += f" (run {o.run_id}, {o.n_written} obs, {o.n_quarantined} quarantined)"
            if o.detail:
                bits += f" - {o.detail}"
            print(bits, file=out)


def _resolve_paths(args):
    return Path(args.db or _default_db()), Path(args.raw_dir or _default_raw()), \
        Path(args.registry) if args.registry else DEFAULT_REGISTRY


def _open_run(args, specs, db_path: Path, raw_path: Path, request: RunRequest,
              http_for) -> int:
    """The run/replay body: prints the aggregate report; honours --dry-run with a throwaway
    DB/raw store under TMPDIR - the real --db/--raw-dir are never opened."""
    if args.dry_run:
        tmp = tempfile.TemporaryDirectory(prefix="prumo-dry-run-")  # TMPDIR-scoped
        db_path, raw_path = Path(tmp.name) / "prumo.sqlite3", Path(tmp.name) / "raw"
    else:
        tmp = None
    db = open_db(db_path)
    try:
        store = RawStore(raw_path)
        sync_registry(db, specs)
        only = None if getattr(args, "source", "all") == "all" else [args.source]
        report = run_all(db, store, specs, http_for=http_for, request=request, only=only)
        _print_report(report, sys.stdout)
        return report.exit_code()
    finally:
        db.close()
        if tmp is not None:
            tmp.cleanup()


def main(argv: list[str] | None = None, *, http_for=None) -> int:
    """CLI entry. `http_for` is the test seam (default: the polite per-source client)."""
    args = build_parser().parse_args(argv)
    db_path, raw_path, registry = _resolve_paths(args)
    specs = load_registry(registry)
    known = sorted({s.source.name for s in specs})
    http_for = http_for or (lambda name: _http_for(specs, name))

    if args.command == "status":
        db = open_db(db_path)
        try:
            report = build_status(db, specs)
        finally:
            db.close()
        print(report.to_json() if args.as_json else render_text(report))
        return 0

    if args.command == "import-legacy":
        csv_path = Path(args.csv)
        if csv_path.suffix.lower() != ".csv":
            print(f"import-legacy takes the CSV export (e.g. indicators.csv); "
                  f"{csv_path} is not a .csv file - the old DuckDB store is unsupported "
                  f"here (Ruling U: the migration is CSV-based)", file=sys.stderr)
            return 2
        if not csv_path.is_file():
            print(f"legacy export not found: {csv_path}", file=sys.stderr)
            return 2
        db = open_db(db_path)
        try:
            report = import_legacy(db, csv_path, specs)
        finally:
            db.close()
        print(f"imported {report.n_imported} legacy rows; "
              f"quarantined {report.n_quarantined_by_reason or '{}'}")
        return 0

    if args.command == "verify":
        if args.run_id <= 0:
            print(f"verify needs a positive dataset_run id, got {args.run_id}", file=sys.stderr)
            return 2
        db = open_db(db_path)
        try:
            return _cmd_verify(args.run_id, specs, db, RawStore(raw_path), http_for)
        finally:
            db.close()

    if args.command in ("run", "replay"):
        names = known + ["all"]
        if args.command == "run" and args.source not in names:
            print(f"unknown source {args.source!r}; registry sources: {known} or 'all'",
                  file=sys.stderr)
            return 2
        request = RunRequest()
        if args.command == "replay":
            try:
                month = _check_month(args.from_month)  # rejects before ANY db open/mutation
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 2
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            request = RunRequest(window=(f"{month}-01T00:00:00+00:00",
                                         f"{today.isoformat()}T00:00:00+00:00"))
        return _open_run(args, specs, db_path, raw_path, request, http_for)
    raise AssertionError("unreachable")  # argparse required=True already enforced the command


def _cmd_verify(run_id: int, specs, db, store, http_for) -> int:
    """Verify ONE existing pending-verification run: resolve its source, require it verifiable
    and non-legacy, take the verifier instance registered for the source (registering the
    reviewed configuration first when absent) and hand THAT instance to verify_run."""
    info = db.run_info(run_id)
    if info is None:
        print(f"no such run: {run_id}", file=sys.stderr)
        return 2
    _id, source_name, dataset_key, state, _started, _finished = info
    if dataset_key is None or dataset_key.startswith(operations.LEGACY_DATASET_PREFIX):
        print(f"run {run_id} is a legacy import run: legacy data is never re-verified as if "
              f"it were fresh (it stays 'legacy-unverified' with its original dates)",
              file=sys.stderr)
        return 2
    if state != "pending-verification":
        print(f"run {run_id} is {state!r}; only pending-verification runs can be verified",
              file=sys.stderr)
        return 2
    run_specs = [s for s in specs if s.source.name == source_name]
    if not run_specs:
        print(f"run {run_id} belongs to {source_name!r}, which is not in the registry; "
              f"refusing to verify unrelated data", file=sys.stderr)
        return 2
    if not run_specs[0].source.verifiable:
        print(f"source {source_name!r} is 'verifiable: false' in the registry; its runs are "
              f"never verified", file=sys.stderr)
        return 2
    by_id = {s.id: s for s in run_specs}
    ids = db.run_series_ids(run_id)
    bad = [sid for sid in ids if sid not in by_id or not by_id[sid].active]
    if bad:
        print(f"run {run_id} touches series absent from the registry or inactive: {bad}; "
              f"refusing to verify", file=sys.stderr)
        return 2
    try:
        operations.ensure_verifier(operations.VERIFIER_OPS[source_name])
        verifier = get_verifier(source_name)
    except (KeyError, ValueError) as e:
        print(f"cannot obtain the registered verifier for {source_name!r}: {e}",
              file=sys.stderr)
        return 2
    http = http_for(source_name)
    passed = verify_run(db, run_id, verifier, http, specs=[by_id[sid] for sid in ids],
                        store=store)
    print(f"run {run_id}: {'verified' if passed else 'FAILED verification'}")
    return 0 if passed else 1
