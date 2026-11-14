"""Command line interface for Prumo base-data operations (Task 17A).

    python -m ingest [--db P] [--raw-dir D] [--registry Y] <command>

    run <source|all> [--dry-run]   fresh fetch + verification through run_with_refetch ONLY;
                                   World Bank runs one isolated dataset per indicator, so one
                                   indicator's outage never blocks the healthy others; a
                                   failing source/group never stops the rest; exit 1 if any
                                   ACTIVE, verifiable source did not verify
    lag                            read-only data-time check: ACTIVE series whose newest
                                   fetched period lags today beyond ingest.data_lag.MAX_LAG
                                   (possibly frozen publisher dataset); exit 1 if any
    status [--json]                typed report from Db records: per source/series latest
                                   attempt, last REAL verification, the retained data's genuine
                                   retrieval date, staleness (our refresh policy), event
                                   totals, pending-verification runs
    withdraw <run_id> --reason R   withdraw ONE verified fetched run from serving (terminal,
                                   recorded as event 'withdrawal' with the reason; rows kept)
    verify <run_id>                verify ONE existing pending-verification run with the
                                   verifier registered for its source (this command exists to
                                   resolve a specific pending run; normal flows never call it)
    import-legacy <csv>            import the legacy CSV export (Ruling U - NOT the old DuckDB
                                   store); legacy rows stay legacy-unverified and keep their
                                   original retrieval dates
    capture <wb|eredes>            MANUAL original-file capture for networks where the server
                                   routes fail: runs the full registered source+verifier flow
                                   through a bounded recording client on a THROWAWAY scratch
                                   DB under TMPDIR (--db/--raw-dir are never opened) and
                                   writes an auditable bundle: exact bodies + manifest with
                                   ACTUAL statuses and ORIGINAL fetch times
    run <source> --bundle DIR      replay one validated bundle offline (--indicator scopes a
                                   World Bank bundle to one indicator's whole geography
                                   group; E-REDES bundle runs need explicit --from/--to day
                                   bounds, also usable live for catch-up); recorded input
                                   keeps its ORIGINAL retrieval dates and is labelled
                                   'recorded'; never replaces newer verified data; the
                                   VERIFIER reads the publisher over live HTTP (fails
                                   clearly offline) unless --pinned-verifier (NOT
                                   audit-grade, recorded per verification) is given
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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ingest import operations
from ingest.bundle import (
    BundleError,
    BundleRecorder,
    CaptureHttp,
    PinnedHttp,
    RecordedSource,
    RecordingHttp,
    load_bundle,
)
from ingest.data_lag import lagging_series
from ingest.db import ReadOnlyOpenError, open_db, read_db_readonly
from ingest.legacy_import import DEFAULT_REGISTRY, import_legacy
from ingest.operations import DEFAULT_CLIENT_TIMEOUT_S, RunReport, RunRequest, polite_http, run_all
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.worldbank import parse_native_code as wb_parse_native_code
from ingest.status import build_status, render_text
from ingest.verifiers import get_verifier
from ingest.verify import verify_run

_MONTH = re.compile(r"[0-9]{4}-[0-9]{2}")  # ASCII digits only
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
BUNDLE_SOURCES = ("worldbank", "eredes")  # keyless, reviewed channels only


def _default_db() -> str:
    # PRUMO_DB_PATH is the image/scheduler contract; PRUMO_DB is the deprecated older name.
    return (os.environ.get("PRUMO_DB_PATH") or os.environ.get("PRUMO_DB")
            or "/data/prumo.sqlite3")


def _default_raw() -> str:
    return os.environ.get("PRUMO_RAW_DIR", "/data/raw")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m ingest",
        description="Prumo base-data operations (run/status/verify/withdraw/import-legacy/replay).")
    p.add_argument("--db", help="SQLite database (default: $PRUMO_DB_PATH, else the deprecated "
                                "$PRUMO_DB, else /data/prumo.sqlite3)")
    p.add_argument("--raw-dir", help="raw evidence store (default: $PRUMO_RAW_DIR or /data/raw)")
    p.add_argument("--registry", help=f"registry YAML (default: {DEFAULT_REGISTRY})")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("docs", help="render registry source documentation to stdout (offline)",
                   description="Render the selected --registry to stdout; no DB, raw store "
                               "or network access. Redirect stdout to save the Markdown.")

    r = sub.add_parser("run", help="fresh fetch+verify of one source or all (see module help)")
    r.add_argument("source", help="registry source name, or 'all'")
    r.add_argument("--bundle", metavar="DIR",
                   help="replay an exact validated original-file bundle offline "
                        "(worldbank/eredes only); recorded input keeps original fetch dates")
    r.add_argument("--indicator", metavar="CODE",
                   help="worldbank only: one native indicator code (its whole registered "
                        "geography group, never one country)")
    r.add_argument("--from", dest="from_day", metavar="YYYY-MM-DD",
                   help="eredes only: first UTC day of an explicit catch-up/replay window")
    r.add_argument("--to", dest="to_day", metavar="YYYY-MM-DD",
                   help="eredes only: last UTC day of the window (inclusive; before today UTC)")
    r.add_argument("--dry-run", action="store_true",
                   help="isolate: a throwaway DB/raw store under TMPDIR; --db/--raw-dir are "
                        "never opened")
    r.add_argument("--pinned-verifier", action="store_true",
                   help="with --bundle only, NOT AUDIT-GRADE: verify against the bundle's "
                        "own captured verifier responses instead of live HTTP (recorded as "
                        "verifier_channel='pinned-bundle'); default: the verifier reads the "
                        "publisher live and fails clearly when offline")

    c = sub.add_parser(
        "capture",
        help="MANUAL original-file capture on any machine with network (worldbank/eredes "
             "keyless channels): full registered source+verifier flow on a THROWAWAY scratch "
             "DB under TMPDIR (--db/--raw-dir are never opened), writing an auditable bundle "
             "of exact bodies + manifest; partial captures keep healthy files archived and "
             "exit nonzero")
    c.add_argument("source", choices=BUNDLE_SOURCES)
    c.add_argument("--output", required=True, metavar="DIR",
                   help="new (or empty) bundle directory; an existing non-empty one is "
                        "refused, never overwritten")
    c.add_argument("--indicator", metavar="CODE",
                   help="worldbank only: one native indicator code (whole geography group)")
    c.add_argument("--from", dest="from_day", metavar="YYYY-MM-DD",
                   help="eredes only: first UTC day to capture")
    c.add_argument("--to", dest="to_day", metavar="YYYY-MM-DD",
                   help="eredes only: last UTC day to capture (inclusive; before today UTC)")
    c.add_argument("--timeout", type=float, default=DEFAULT_CLIENT_TIMEOUT_S,
                   help="per-request timeout seconds (positive finite)")
    c.add_argument("--max-requests", type=int, default=256,
                   help="physical network request cap, redirects and retries included")
    c.add_argument("--deadline", type=float, default=300.0,
                   help="hard whole-phase deadline in seconds: checked BEFORE every physical "
                        "request, each request's timeout is clamped to the remaining budget, "
                        "a stalled server is KILLED at the deadline and a late response is "
                        "discarded rather than returned")

    sub.add_parser("lag", help="read-only data-time check: active series whose newest "
                               "fetched period lags today beyond the per-frequency allowance "
                               "(ingest.data_lag.MAX_LAG); exit 1 if any",
                   description="Flags possibly frozen/discontinued publisher datasets. A hit "
                               "means investigate, never deactivate automatically.")

    s = sub.add_parser("status", help="operational status report (read-only)")
    s.add_argument("--json", dest="as_json", action="store_true", help="typed JSON report")

    v = sub.add_parser("verify", help="verify ONE existing pending-verification run id "
                                      "(normal runs never use this)")
    v.add_argument("run_id", type=int, help="dataset_run.id in state pending-verification")

    w = sub.add_parser("withdraw", help="withdraw ONE verified fetched run from serving, with "
                                        "a recorded reason (terminal; rows are kept)")
    w.add_argument("run_id", type=int, help="dataset_run.id in state verified (not legacy)")
    w.add_argument("--reason", required=True,
                   help="why the vintage is withdrawn (recorded in event 'withdrawal')")

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

def _check_day(text: str) -> date:
    """A canonical YYYY-MM-DD day, ASCII digits, a real Gregorian date."""
    if not _DAY.fullmatch(text):
        raise ValueError(f"day bounds must be ASCII YYYY-MM-DD, got {text!r}")
    try:
        return date.fromisoformat(text)
    except ValueError as e:
        raise ValueError(f"day bound is not a real date: {text!r}") from e


def _eredes_bounds(args) -> tuple[str, str]:
    """Validate --from/--to (both required by callers here) into a [from, to+1d) UTC window
    of canonical day starts: strict ASCII days, non-empty, never in the future (today UTC is
    a running, partial day, so the last allowed day is yesterday)."""
    if bool(args.from_day) != bool(args.to_day):
        raise ValueError("E-REDES explicit windows need BOTH --from and --to")
    first, last = _check_day(args.from_day), _check_day(args.to_day)
    if last < first:
        raise ValueError(f"--from {first} must not be after --to {last} (window is non-empty)")
    today = datetime.now(timezone.utc).date()
    if last >= today:
        raise ValueError(f"--to {last} must be before today UTC ({today}): today's window is "
                         f"still running/partial; refusing to capture/ingest it as complete")
    return (f"{first.isoformat()}T00:00:00+00:00",
            f"{(last + timedelta(days=1)).isoformat()}T00:00:00+00:00")


def _http_for(specs, name=None):
    """CLI default Http factory: the shared polite-client policy (operations.polite_http) -
    min registry throttle (default 1 rps), the registry timeout_s (INE 300; client default
    otherwise) and NO client retries (0: retry budgets must not multiply the bounded
    run_with_refetch attempts)."""
    return polite_http(specs, name, default_timeout_s=DEFAULT_CLIENT_TIMEOUT_S)


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
              http_for, *, bundle=None) -> int:
    """The run/replay body: prints the aggregate report; honours --dry-run with a throwaway
    DB/raw store under TMPDIR - the real --db/--raw-dir are never opened. With `bundle` (a
    fully validated ingest.bundle.Bundle), input comes ONLY from the pinned offline
    responses: the run is labelled 'recorded', keeps the receipts' ORIGINAL fetch dates, and
    stale groups are refused PER DATASET GROUP before sync_registry or any insertion when the
    group's own original collector receipts are not newer than the verified fetched data
    already held for that group; an atomic in-transaction guard (ingest.pipeline) covers the
    race with a concurrent newer writer."""
    pinned = None
    source_factories = None
    verify_http_for, verifier_channel = None, "live"
    if args.dry_run:
        tmp = tempfile.TemporaryDirectory(prefix="prumo-dry-run-")  # TMPDIR-scoped
        db_path, raw_path = Path(tmp.name) / "prumo.sqlite3", Path(tmp.name) / "raw"
    else:
        tmp = None
    if bundle is not None:
        pinned = PinnedHttp(bundle)  # refuses partial (failure-carrying) bundles
        source_factories = {
            args.source: lambda req: RecordedSource(
                operations.SOURCE_FACTORIES[args.source](req), pinned)}
        live_http_for = http_for

        def http_for(_name):  # recorded path: the pinned bundle is the only COLLECTOR input
            return pinned
        if getattr(args, "pinned_verifier", False):
            # NON-AUDIT-GRADE (explicit flag): the verifier reads the same operator-captured
            # bundle as the collector, so a consistently edited bundle would still "verify";
            # recorded on every verification row as verifier_channel='pinned-bundle'
            verify_http_for, verifier_channel = http_for, "pinned-bundle"
        else:  # B-I3: verification of recorded input re-reads the publisher over LIVE HTTP
            verify_http_for = live_http_for
    db = open_db(db_path)
    try:
        store = RawStore(raw_path)
        blocked_groups = None
        if bundle is not None:
            blocked_groups, n_groups = _stale_bundle_groups(db, bundle, args.source, specs,
                                                            request)
            for detail in blocked_groups.values():
                print(detail, file=sys.stderr)  # every refusal diagnosed BEFORE any write
            if n_groups and len(blocked_groups) == n_groups:
                # every selected group is stale: refuse the replay BEFORE sync_registry, so a
                # refused bundle cannot even rewrite registry metadata
                return 1
        sync_registry(db, specs)
        only = None if getattr(args, "source", "all") == "all" else [args.source]
        report = run_all(db, store, specs, http_for=http_for, request=request, only=only,
                         source_factories=source_factories, blocked_groups=blocked_groups,
                         verify_http_for=verify_http_for, verifier_channel=verifier_channel)
        _print_report(report, sys.stdout)
        return report.exit_code()
    finally:
        db.close()
        if tmp is not None:
            tmp.cleanup()


def _stale_bundle_groups(db, bundle, source_name: str, specs, request: RunRequest):
    """Per-dataset-group stale preflight of a recorded replay (Task 17 review R1).

    For each ACTUAL DatasetGroup of the selected source, compares the OLDEST ORIGINAL
    collector receipt that would back an OBSERVATION of that group (the real adapter
    re-driven over a fresh PinnedHttp, fetch+parse, and the rows' response_index receipts -
    so dataset-metadata and verifier receipts can neither boost nor doom a payload's
    freshness) against the NEWEST held (verified or pending-verification) fetched row of
    that group's series.
    Conservative on both sides (MIN vs MAX): a group is stale when the held data is strictly
    newer than its own oldest observation receipt, no matter how fresh OTHER groups are.

    Returns ({group_key: refusal detail}, total groups). A group whose collector receipt
    plan cannot be reproduced offline (missing pinned request, adapter failure) is NOT
    preflight-refused: the real run fails honestly on its own, and the in-transaction guard
    still applies if it ever reaches an insert. Pure reads + bundle file IO: no DB writes.
    """
    active = [s for s in specs if s.source.name == source_name and s.active]
    if not active:
        return {}, 0
    groups = operations.group_specs(active)
    blocked: dict[str, str] = {}
    for group in groups:
        held = db.max_held_fetched_at([s.id for s in group.specs])
        if held is None:
            continue
        oldest = _group_oldest_receipt(bundle, source_name, request, group.specs)
        if oldest is None or datetime.fromisoformat(held) <= oldest:
            continue
        blocked[group.key()] = (
            f"refusing an outdated bundle for dataset group {group.label!r}: the "
            f"(verified or pending) fetched data already held for THIS group reaches "
            f"{held}, but the bundle's oldest original collector receipt for the group is "
            f"{oldest.isoformat()}; a recorded bundle never replaces NEWER verified data - "
            f"legacy April rows stay untouched, and a LATER valid recorded download is "
            f"still accepted")
    return blocked, len(groups)


def _group_oldest_receipt(bundle, source_name: str, request: RunRequest, group_specs):
    """The OLDEST original fetch time of the collector responses that would back this group's
    OBSERVATIONS (rows parse out of; dataset-metadata responses carry no rows and are
    excluded), or None when the adapter's request plan cannot be reproduced offline (missing
    pinned request, adapter parse error): such a group gets no preflight verdict and is left
    to the real run (the in-transaction guard still applies if it ever reaches an insert)."""
    pinned = PinnedHttp(bundle)
    source = operations.SOURCE_FACTORIES[source_name](request)
    recorded = RecordedSource(source, pinned)
    base = len(pinned.served)
    try:
        responses = list(recorded.fetch(list(group_specs), pinned))
        served = pinned.served[base:]
        parsed = recorded.parse(list(group_specs), responses)
        stamps = [datetime.fromisoformat(served[row.response_index].fetched_at)
                  for rows in parsed.values() for row in rows]
    except Exception:  # a predictive probe only; the real run reports the failure honestly
        return None
    return min(stamps) if stamps else None


def main(argv: list[str] | None = None, *, http_for=None) -> int:
    """CLI entry. `http_for` is the test seam (default: the polite per-source client)."""
    args = build_parser().parse_args(argv)
    if args.command == "docs":
        from ingest.docgen import generate_sources
        registry = Path(args.registry) if args.registry else DEFAULT_REGISTRY
        print(generate_sources(registry), end="")
        return 0
    db_path, raw_path, registry = _resolve_paths(args)
    specs = load_registry(registry)
    known = sorted({s.source.name for s in specs})
    custom_http = http_for is not None
    http_for = http_for or (lambda name: _http_for(specs, name))

    if args.command in ("status", "lag"):
        # never migrates, never creates a file; one plain mode=ro retry on a concurrent writer
        read = ((lambda db: build_status(db, specs)) if args.command == "status"
                else (lambda db: db.latest_fetched_periods()))
        try:
            result = read_db_readonly(db_path, read)
        except ReadOnlyOpenError as e:
            print(f"{args.command} refused: {e}", file=sys.stderr)
            return 2

    if args.command == "status":
        print(result.to_json() if args.as_json else render_text(result))
        return 0

    if args.command == "lag":
        latest = result
        found = lagging_series(specs, latest, datetime.now(timezone.utc).date())
        for f in found:
            print(f"LAGGING {f.series_id} {f.frequency} latest={f.latest_period} "
                  f"lag={f.lag} > {f.max_lag}")
        never = sorted(s.id for s in specs if s.active and s.id not in latest)
        for sid in never:
            print(f"NO-FETCHED-DATA {sid}")
        print(f"{len(found)} lagging, {len(never)} without fetched data, "
              f"{sum(s.active for s in specs)} active")
        return 1 if found else 0

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

    if args.command == "withdraw":
        db = open_db(db_path)
        try:
            db.withdraw_run(args.run_id, args.reason, datetime.now(timezone.utc).isoformat())
        except ValueError as e:
            print(f"withdraw refused: {e}", file=sys.stderr)
            return 2
        finally:
            db.close()
        print(f"run {args.run_id} withdrawn: its rows are kept but no longer served")
        return 0

    if args.command in ("run", "replay"):
        names = known + ["all"]
        if args.command == "run" and args.source not in names:
            print(f"unknown source {args.source!r}; registry sources: {known} or 'all'",
                  file=sys.stderr)
            return 2
        request = RunRequest()
        bundle = None
        if args.command == "replay":
            try:
                month = _check_month(args.from_month)  # rejects before ANY db open/mutation
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 2
            today = datetime.now(timezone.utc).date()
            request = RunRequest(window=(f"{month}-01T00:00:00+00:00",
                                         f"{today.isoformat()}T00:00:00+00:00"))
            return _open_run(args, specs, db_path, raw_path, request, http_for)
        try:  # every run-mode validation BEFORE any DB open or file mutation
            if args.pinned_verifier and args.bundle is None:
                raise ValueError("--pinned-verifier only applies to a recorded --bundle run")
            if args.dry_run and args.bundle:
                raise ValueError("--dry-run and --bundle do not combine: a recorded run IS "
                                 "already the isolated path")
            if args.bundle is not None:
                if args.source == "all":
                    raise ValueError("--bundle is per-source: run one source per bundle")
                if args.source not in BUNDLE_SOURCES:
                    raise ValueError(f"--bundle supports {list(BUNDLE_SOURCES)} only (the "
                                     f"keyless recorded channels), got {args.source!r}")
            if args.indicator is not None:
                if args.source != "worldbank":
                    raise ValueError("--indicator is a World Bank-only selector (its whole "
                                     "registered geography group, never one country)")
                selected = _select_indicator(specs, args.indicator)
            else:
                selected = specs
            if (args.from_day or args.to_day) and args.source != "eredes":
                raise ValueError("--from/--to day bounds are E-REDES-only")
            if args.source == "eredes" and (args.from_day or args.to_day):
                request = RunRequest(window=_eredes_bounds(args))
            if args.source == "eredes" and args.bundle is not None and not request.window:
                raise ValueError("a recorded E-REDES replay needs explicit --from/--to day "
                                 "bounds (the bundle was captured for a specific window)")
            if args.bundle is not None:
                bundle = load_bundle(Path(args.bundle), source=args.source)  # FULL entry+
                # byte validation here, BEFORE any DB open/mutation
                request = RunRequest(window=request.window, input_origin="recorded")
        except (ValueError, BundleError) as e:
            print(str(e), file=sys.stderr)
            return 2
        return _open_run(args, selected, db_path, raw_path, request, http_for, bundle=bundle)
    if args.command == "capture":
        try:
            return _cmd_capture(args, specs, http_for, custom_http=custom_http)
        except (ValueError, FileExistsError) as e:
            print(str(e), file=sys.stderr)
            return 2
    raise AssertionError("unreachable")  # argparse required=True already enforced the command


def _select_indicator(specs, code: str):
    """World Bank registry restricted to ONE active indicator code (whole geography group,
    never a single country). ValueError on an unknown/inactive code."""
    known_codes = sorted({wb_parse_native_code(s.native_code)[0]
                          for s in specs if s.source.name == "worldbank" and s.active})
    if code not in known_codes:
        raise ValueError(f"unknown active World Bank indicator {code!r}; registry "
                         f"indicators: {known_codes}")
    return [s for s in specs if s.source.name != "worldbank" or not s.active
            or wb_parse_native_code(s.native_code)[0] == code]


_CSV_DAY = re.compile(r'([0-9]{4}-[0-9]{2}-[0-9]{2})')


def _eredes_covered_csv_days(recorder: BundleRecorder) -> set[str]:
    """UTC days with a recorded /exports/csv entry in the capture (per-day where params)."""
    covered = set()
    for e in recorder.entries:
        if e.url.endswith("/exports/csv") and e.params and "where" in e.params:
            m = _CSV_DAY.search(e.params["where"])
            if m:
                covered.add(m.group(1))
    return covered


def _capture_eredes_coverage(window: tuple[str, str], rec_http, recorder: BundleRecorder,
                             specs) -> None:
    """Record a genuine /exports/csv for EVERY source window day, not only the days the
    capture's own random verification sampled - a later replay draws a FRESH seed and must
    find every day pinned. Uses the registered verifier itself (same reviewed endpoint/
    format) on one BlindItem per uncovered day through the SAME recording client; nothing is
    synthesized."""
    from ingest.sources.eredes import EredesSource
    from ingest.verifiers import BlindItem
    covered = _eredes_covered_csv_days(recorder)
    days = [d.isoformat() for d in EredesSource(*window).days]
    missing = [d for d in days if d not in covered]
    if not missing:
        return
    spec = next(s for s in specs if s.source.name == "eredes" and s.active)
    verifier = operations.ensure_verifier(operations.VERIFIER_OPS["eredes"])
    items = [BlindItem(series_id=spec.id, period=f"{d}T00:00:00+00:00", spec=spec)
             for d in missing]
    verifier.check(items, rec_http)  # raises (recorded honestly) on any non-2xx/drift


def _cmd_capture(args, specs, http_for, *, custom_http: bool = False) -> int:
    """Bounded manual capture on a scratch DB; seals the bundle; exit 0 only when the full
    registered flow verified AND every capture-relevant request succeeded. Never opens the
    configured --db/--raw-dir."""
    if args.indicator is not None and args.source != "worldbank":
        raise ValueError("--indicator is a World Bank-only selector")
    if (args.from_day or args.to_day) and args.source != "eredes":
        raise ValueError("--from/--to day bounds are E-REDES-only")
    request = RunRequest()
    window = None
    if args.source == "eredes":
        if not (args.from_day and args.to_day):
            raise ValueError("capture eredes needs explicit --from/--to day bounds (record "
                             "exactly the window you intend to replay)")
        window = _eredes_bounds(args)
        request = RunRequest(window=window)
    selected = (_select_indicator(specs, args.indicator)
                if args.indicator is not None else specs)
    base = http_for(args.source) if custom_http else CaptureHttp(
        timeout=args.timeout, max_requests=args.max_requests, deadline_s=args.deadline)
    recorder = BundleRecorder(Path(args.output))  # refuses an existing non-empty output
    rec_http = RecordingHttp(base, recorder)
    tmp = tempfile.TemporaryDirectory(prefix="prumo-capture-")  # scratch under TMPDIR only
    ok = True
    try:
        db = open_db(Path(tmp.name) / "capture.sqlite3")
        try:
            store = RawStore(Path(tmp.name) / "raw")
            sync_registry(db, specs)
            report = run_all(db, store, selected, http_for=lambda _n: rec_http,
                             request=request, only=[args.source])
            _print_report(report, sys.stdout)
            ok = report.exit_code() == 0
            if ok and args.source == "eredes" and window is not None:
                _capture_eredes_coverage(window, rec_http, recorder, selected)
        finally:
            db.close()
    except Exception as e:  # honest failure record; healthy files already on disk stay
        recorder.record_failure("<capture>", None, f"{type(e).__name__}: {e}")
        ok = False
    finally:
        tmp.cleanup()
    manifest = recorder.seal(args.source)  # atomic operator receipt, failures included
    if not ok or recorder.failures:
        print(f"capture INCOMPLETE (failures: {len(recorder.failures)}); healthy responses "
              f"stay archived under {manifest.parent} for audit; fix the failing route and "
              f"capture again into a FRESH directory - a partial bundle is never runnable",
              file=sys.stderr)
        return 1
    print(f"capture complete: {len(recorder.entries)} exact response(s) sealed with original "
          f"fetch times in {manifest}")
    return 0


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
