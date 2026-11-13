"""Operational status projection (Task 17A): a typed, honest report built from Db records
(every SQL statement lives in ingest/db.py) plus the registry specs (schedule/unit/verifiable
live only in the YAML).

Honesty rules:
- a legacy import's synthetic run is stored in state 'verified' but is NEVER verification
  evidence: `last_verified` counts only PASSED verification rows on fetched (non-legacy)
  datasets, and a series whose only data is legacy is availability 'legacy-unverified';
- `latest_attempt` excludes the legacy synthetic runs entirely;
- the real data retrieval date (observation.fetched_at) is reported separately from
  last_attempt/last_verified; for legacy rows it is the ORIGINAL legacy fetch date, so the
  retained data's age is visible even if no verification ever ran;
- latest state is per DATASET (ingest.operations.group_specs): a healthy final World Bank
  indicator can never conceal an earlier failed indicator;
- 'stale' is OUR refresh policy (series.schedule when present, else frequency defaults
  A/S=30d, Q=7d, M/D/PT15M=1d - the shared knowledge lives in ingest.cadence, which the
  Task 18 scheduler also derives from), never a claimed publisher release date;
  never-fetched / never-verified series report stale=None with an explicit reason;
- pending-verification runs are listed (stale after 24 h); a verified short-circuit run with
  no observations invents no new verification.

Timestamps come from the database and the system clock only; the CLI status command accepts no
time arguments.
"""
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from ingest.cadence import DEFAULT_INTERVAL, series_interval
from ingest.db import Db
from ingest.models import SeriesSpec
from ingest.operations import LEGACY_DATASET_PREFIX, group_specs

SCHEMA = "prumo-status"
VERSION = 1

# Our refresh policy, not a publisher cadence claim. series.schedule ('7d', '12h'...) wins.
# Compatible alias for the pre-extraction (Task 18A) name; the knowledge lives in ingest.cadence.
DEFAULT_STALE_AFTER = DEFAULT_INTERVAL
PENDING_STALE_AFTER = timedelta(hours=24)


def _parse_ts(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class DatasetStatus:
    """Latest attempt on one grouping-policy dataset of the source (legacy keys excluded)."""
    label: str
    latest_state: str | None
    latest_attempt: str | None
    input_origin: str | None  # 'live' | 'recorded' of that latest attempt (never 'legacy')


@dataclass(frozen=True)
class PendingRun:
    run_id: int
    dataset: str
    source: str  # the run's OWN source: attribution never depends on current grouping
    started_at: str
    input_origin: str
    stale: bool  # started more than PENDING_STALE_AFTER ago


@dataclass(frozen=True)
class SeriesStatus:
    id: str
    active: bool
    frequency: str
    dataset_label: str | None  # None for inactive series (they are not scheduled to run)
    latest_attempt: str | None
    latest_attempt_state: str | None
    latest_attempt_origin: str | None  # 'live' | 'recorded' of the latest attempt
    last_verified: str | None       # real verification evidence only (never a legacy run)
    real_data_fetched_at: str | None  # the retained data's genuine retrieval date
    availability: str               # 'verified' | 'legacy-unverified' | 'none'
    legacy_rows: int
    stale: bool | None
    stale_reason: str | None        # 'never_fetched' | 'never_verified' | None


@dataclass(frozen=True)
class SourceStatus:
    name: str
    verifiable: bool
    redistribution_ok: bool
    blockers: tuple[str, ...]       # 'not_verifiable' / 'licence_withheld' (kept separate
                                    # from technical failures on purpose)
    active_series: int
    inactive_series: int
    latest_attempt: str | None
    latest_attempt_state: str | None
    last_verified: str | None
    real_data_fetched_at: str | None
    events: dict[str, int]
    pending_runs: tuple[PendingRun, ...]
    datasets: tuple[DatasetStatus, ...]
    series: tuple[SeriesStatus, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.blockers)


@dataclass(frozen=True)
class StatusReport:
    generated_at: str
    sources: tuple[SourceStatus, ...]
    schema: str = SCHEMA
    version: int = VERSION
    staleness_policy: dict = field(default_factory=lambda: {
        "meaning": "our refresh policy, not a publisher release date",
        "defaults_days": {k: v.days for k, v in DEFAULT_STALE_AFTER.items()},
        "schedule_overrides": "series.schedule (e.g. '1d') when present",
        "pending_stale_after_hours": PENDING_STALE_AFTER.seconds // 3600})

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def build_status(db: Db, specs: list[SeriesSpec], *,
                 now: Callable[[], datetime] | None = None) -> StatusReport:
    """The typed status report from current Db records + registry specs."""
    now_ts = (now or (lambda: datetime.now(timezone.utc)))()

    # dataset identity per ACTIVE series from the authoritative grouping policy
    label_of: dict[str, str] = {}     # series id -> dataset label
    key_of: dict[str, str] = {}       # series id -> dataset_key
    label_of_key: dict[str, str] = {}
    by_source: dict[str, list[SeriesSpec]] = {}
    for s in specs:
        by_source.setdefault(s.source.name, []).append(s)
    for name, group in by_source.items():
        active = [s for s in group if s.active]
        if not active:
            continue
        for g in group_specs(active):
            label_of_key[g.key()] = g.label
            for s in g.specs:
                label_of[s.id] = g.label
                key_of[s.id] = g.key()

    # runs: latest non-legacy attempt per dataset; pending runs
    latest_by_key: dict[str, tuple[str, str, str]] = {}  # key -> (started_at, state, origin)
    pending: list[PendingRun] = []
    for run_id, source, key, state, started, _finished, origin in db.runs_overview():
        if key is None or key.startswith(LEGACY_DATASET_PREFIX):
            continue  # legacy synthetic runs are never an attempt; keys-less rows are not
        if state == "pending-verification":
            started_dt = _parse_ts(started)
            pending.append(PendingRun(run_id, label_of_key.get(key, key), source, started,
                                      origin, started_dt is not None
                                      and now_ts - started_dt > PENDING_STALE_AFTER))
        cur = latest_by_key.get(key)
        if cur is None or started > cur[0]:
            latest_by_key[key] = (started, state, origin)

    legacy_keys = set()
    for run_id, source, key, state, started, _finished, _o in db.runs_overview():
        if key is not None and key.startswith(LEGACY_DATASET_PREFIX):
            legacy_keys.add(key)

    # real verification evidence: PASSED verification rows on non-legacy datasets
    verified_by_key: dict[str, str] = {}   # dataset_key -> latest passed created_at
    for run_id, key, passed, created in db.verification_overview():
        if passed and key is not None and key not in legacy_keys:
            if created > verified_by_key.get(key, ""):
                verified_by_key[key] = created

    # observation stats per series/kind/state
    stats: dict[tuple, tuple] = {}
    for sid, kind, state, n, max_fetched in db.observation_stats():
        stats[(sid, kind, state)] = (n, max_fetched)

    events: dict[str, dict[str, int]] = {}
    for src, kind, n in db.event_totals():
        if src is not None:
            events.setdefault(src, {})[kind] = n

    source_rows = {name: redist for name, redist in db.source_list()}

    sources = []
    # Sources known ONLY through pending runs (unknown/old-registry source names) still get a
    # row, so pending state is visible under its own source instead of vanishing.
    for name in sorted(set(by_source) | set(source_rows) | {p.source for p in pending}):
        group = by_source.get(name, [])
        spec0 = group[0].source if group else None
        verifiable = spec0.verifiable if spec0 else True
        redistribution_ok = bool(source_rows.get(name,
                                                 int(spec0.redistribution_ok) if spec0 else 0))
        blockers = tuple(b for b, on in (("not_verifiable", not verifiable),
                                         ("licence_withheld", not redistribution_ok)) if on)
        series_out = []
        for s in sorted(group, key=lambda x: x.id):
            series_out.append(_series_status(s, now_ts, label_of, key_of, latest_by_key,
                                             verified_by_key, stats))
        tried = series_out
        datasets = tuple(
            DatasetStatus(label_of_key[k], state, started, origin)
            for k, (started, state, origin) in sorted(latest_by_key.items())
            if label_of_key.get(k) is not None
            and any(key_of.get(s.id) == k for s in group))
        latest_attempt, latest_state = None, None
        if tried:
            dated = [(s.latest_attempt, s.latest_attempt_state) for s in tried
                     if s.latest_attempt is not None]
            if dated:
                latest_attempt, latest_state = max(dated)
        last_verified = max((s.last_verified for s in tried if s.last_verified), default=None)
        real_fetched = max((s.real_data_fetched_at for s in tried if s.real_data_fetched_at),
                           default=None)
        sources.append(SourceStatus(
            name=name, verifiable=verifiable, redistribution_ok=redistribution_ok,
            blockers=blockers,
            active_series=sum(1 for s in group if s.active),
            inactive_series=sum(1 for s in group if not s.active),
            latest_attempt=latest_attempt, latest_attempt_state=latest_state,
            last_verified=last_verified, real_data_fetched_at=real_fetched,
            events=events.get(name, {}),
            pending_runs=tuple(p for p in pending if p.source == name),
            datasets=datasets, series=tuple(series_out)))
    return StatusReport(generated_at=now_ts.astimezone(timezone.utc).isoformat(),
                        sources=tuple(sources))


def _series_status(s: SeriesSpec, now: datetime, label_of, key_of, latest_by_key,
                   verified_by_key, stats) -> SeriesStatus:
    label, key = label_of.get(s.id), key_of.get(s.id)
    latest = latest_by_key.get(key) if key else None
    last_verified = verified_by_key.get(key) if key else None
    fetched_rows = sum(n for (sid, kind, state), (n, _) in stats.items()
                       if sid == s.id and kind == "fetched")
    verified = [(n, mf) for (sid, kind, state), (n, mf) in stats.items()
                if sid == s.id and kind == "fetched" and state == "verified"]
    legacy = [(n, mf) for (sid, kind, state), (n, mf) in stats.items()
              if sid == s.id and kind == "legacy-unverified"]
    legacy_rows = sum(n for n, _ in legacy)
    if verified:
        availability = "verified"
        real_fetched = max(mf for _, mf in verified)
    elif legacy:
        availability = "legacy-unverified"
        real_fetched = max(mf for _, mf in legacy)
    else:
        availability = "none"
        real_fetched = None
    if availability == "none":
        stale, reason = None, ("never_fetched" if not fetched_rows else "never_verified")
    else:
        age = now - (_parse_ts(real_fetched) or now)
        stale, reason = age > series_interval(s), None
    return SeriesStatus(
        id=s.id, active=s.active, frequency=s.frequency, dataset_label=label,
        latest_attempt=latest[0] if latest else None,
        latest_attempt_state=latest[1] if latest else None,
        latest_attempt_origin=latest[2] if latest else None,
        last_verified=last_verified, real_data_fetched_at=real_fetched,
        availability=availability, legacy_rows=legacy_rows, stale=stale,
        stale_reason=reason)


def render_text(report: StatusReport) -> str:
    """A compact readable rendering; the JSON form (to_json) is the full typed report."""
    lines = [f"prumo status (schema {report.schema} v{report.version}) - "
             f"generated {report.generated_at}",
             "staleness = our refresh policy (schedule or defaults A/S=30d, Q=7d, M/D/PT15M=1d)"
             ", not a publisher release date"]
    for s in report.sources:
        flags = f" BLOCKED ({', '.join(s.blockers)})" if s.blocked else ""
        lines.append(f"{s.name}: {s.active_series} active / {s.inactive_series} inactive "
                     f"series{flags}; latest attempt "
                     f"{s.latest_attempt or '-'} ({s.latest_attempt_state or '-'}); "
                     f"last verified {s.last_verified or 'never'}; data as of "
                     f"{s.real_data_fetched_at or 'none'}; events {s.events or '{}'}")
        for d in s.datasets:
            origin = f", input {d.input_origin}" if d.input_origin else ""
            lines.append(f"  dataset {d.label}: {d.latest_state or 'no attempt'} "
                         f"({d.latest_attempt or '-'}{origin})")
        for p in s.pending_runs:
            mark = " STALE" if p.stale else ""
            lines.append(f"  PENDING run {p.run_id} ({p.dataset}, input {p.input_origin}) "
                         f"since {p.started_at}{mark}")
    return "\n".join(lines)
