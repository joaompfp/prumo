"""Operational status projection (Task 17A, extended in Task 23): a typed, honest report
built from Db records (every SQL statement lives in ingest/db.py) plus the registry specs
(schedule/unit/verifiable live only in the YAML). The CLI opens the database strictly
read-only for it (ingest.db.open_db_readonly).

Honesty rules:
- a legacy import's synthetic run is stored in state 'verified' but is NEVER verification
  evidence: `last_verified` counts only PASSED verification rows on fetched (non-legacy)
  datasets, and a series whose only data is legacy is availability 'legacy-unverified';
- `latest_attempt` excludes the legacy synthetic runs entirely;
- two retrieval dates are reported per series:
  * `real_data_fetched_at`: the latest observation fetched_at of the retained data (for
    legacy rows the ORIGINAL legacy fetch date), i.e. when the bytes now held were received;
  * `last_confirmed_current`: the latest publisher retrieval (raw_fetch.fetched_at) of a run
    that is still 'verified' and either wrote that series' observations, or is an
    identical-payload short-circuit whose matched run (followed through earlier
    short-circuits) is still 'verified' and holds that series. Legacy rows never confirm
    anything (None), and neither does a run verified only against its own pinned bundle
    (verifier_channel 'pinned-bundle', not audit-grade; Task 24): a series whose only
    verified data is pinned-bundle data is stale with reason 'pinned_bundle_only';
- 'stale' is OUR refresh policy (series.schedule when present, else frequency defaults
  A/S=30d, Q=7d, M/D/PT15M=1d - the shared knowledge lives in ingest.cadence, which the
  Task 18 scheduler also derives from), never a claimed publisher release date. It is judged
  on `last_confirmed_current`, so unchanged publisher data that the scheduler keeps
  re-verifying is not stale. Legacy-only series are always stale (reason
  'legacy_unverified'); never-fetched / never-verified series report stale=None with an
  explicit reason;
- latest state is per DATASET (ingest.operations.group_specs): a healthy final World Bank
  indicator can never conceal an earlier failed indicator; each dataset also shows the
  scheduler's persisted retry state (failure streak, an in-flight or interrupted 'running'
  marker, next eligible time computed by ingest.cadence exactly as the scheduler does);
- each dataset shows the verifier channel of its latest passed verification ('live' or
  'pinned-bundle');
- pending-verification runs are listed; one pending for more than 24 h (an interrupted
  verification: nothing sweeps it) is marked STALE with its remedy,
  `python -m ingest verify <run_id>`, and counted in totals['pending_stuck']; a verified
  short-circuit run with no observations invents no new verification;
- events are counted for the last 24 h, the last 7 days and over the database's lifetime.

Timestamps come from the database and the system clock only; the CLI status command accepts no
time arguments.
"""
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from ingest.cadence import DEFAULT_INTERVAL, group_interval, next_eligible_at, series_interval
from ingest.db import Db, SchedulerState
from ingest.models import SeriesSpec
from ingest.operations import LEGACY_DATASET_PREFIX, group_specs

SCHEMA = "prumo-status"
VERSION = 3  # v2 (Task 23): stale judged on last_confirmed_current; counts/windows/scheduler
# v3 (Task 24): pinned-bundle verifications never confirm currency; per-dataset
# verifier_channel; totals['pending_stuck']

# Our refresh policy, not a publisher cadence claim. series.schedule ('7d', '12h'...) wins.
# Compatible alias for the pre-extraction (Task 18A) name; the knowledge lives in ingest.cadence.
DEFAULT_STALE_AFTER = DEFAULT_INTERVAL
PENDING_STALE_AFTER = timedelta(hours=24)
EVENT_WINDOWS = {"24h": timedelta(hours=24), "7d": timedelta(days=7)}
STALE_LIST_CAP = 10  # stale series ids listed per source in the text form


def _parse_ts(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _latest(*stamps: str | None) -> str | None:
    """The chronologically latest stamp (parsed, not compared as text); None if none."""
    dated = [s for s in stamps if s is not None]
    return max(dated, key=_parse_ts) if dated else None


@dataclass(frozen=True)
class SchedulerView:
    """The scheduler's persisted state for one dataset (scheduler_state, migration 0010)."""
    last_attempt_at: str
    last_attempt_state: str          # 'running' = in flight, or interrupted (process died)
    last_finished_at: str | None
    last_success_at: str | None
    failure_streak: int              # consecutive non-verified (incl. interrupted) attempts
    next_eligible_at: str | None     # None = eligible immediately


@dataclass(frozen=True)
class DatasetStatus:
    """Latest attempt on one grouping-policy dataset of the source (legacy keys excluded)."""
    label: str
    latest_state: str | None
    latest_attempt: str | None
    input_origin: str | None  # 'live' | 'recorded' of that latest attempt (never 'legacy')
    scheduler: SchedulerView | None = None
    verifier_channel: str | None = None  # of the latest PASSED verification of the dataset


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
    real_data_fetched_at: str | None  # latest observation fetched_at of the retained data
    last_confirmed_current: str | None  # latest verified retrieval confirming it (see module)
    availability: str               # 'verified' | 'legacy-unverified' | 'none'
    legacy_rows: int
    stale: bool | None
    stale_reason: str | None        # 'never_fetched' | 'never_verified' |
                                    # 'legacy_unverified' | 'pinned_bundle_only' | None


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
    last_confirmed_current: str | None
    stale: int                      # ACTIVE series counts
    never_fetched: int
    never_verified: int
    stale_series: tuple[str, ...]   # ACTIVE stale series ids, sorted
    events: dict[str, int]          # lifetime
    events_24h: dict[str, int]
    events_7d: dict[str, int]
    scheduler_retrying: int         # datasets with a failure streak
    scheduler_running: int          # datasets with an in-flight or interrupted attempt
    scheduler_max_streak: int
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
    totals: dict[str, int]          # active_series / stale / never_fetched / never_verified /
                                    # pending_stuck
    schema: str = SCHEMA
    version: int = VERSION
    staleness_policy: dict = field(default_factory=lambda: {
        "meaning": "our refresh policy, not a publisher release date",
        "judged_on": "last_confirmed_current (latest verified retrieval, including an "
                     "identical-payload re-fetch); legacy-only series are always stale",
        "defaults_days": {k: v.days for k, v in DEFAULT_STALE_AFTER.items()},
        "schedule_overrides": "series.schedule (e.g. '1d') when present",
        "pending_stale_after_hours": int(PENDING_STALE_AFTER.total_seconds() // 3600)})

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def _shortcut_confirmations(db: Db, runs) -> dict[str, str]:
    """series id -> latest retrieval of a still-verified identical-payload short-circuit run
    whose matched run (pipeline compares with the immediately previous run of the dataset,
    which had to be verified) is still verified - followed through earlier short-circuits -
    and holds observations of that series."""
    receipts = {rid: (at, bool(wrote), bool(pinned))
                for rid, _key, at, wrote, pinned in db.verified_run_receipts()}
    previous: dict[int, int | None] = {}
    last_in_key: dict[str, int] = {}
    for run_id, _src, key, _state, _started, _finished, _origin in runs:  # id order
        if key is not None:
            previous[run_id] = last_in_key.get(key)
            last_in_key[key] = run_id

    def base(run_id: int) -> int | None:
        seen = set()
        while run_id not in seen:
            seen.add(run_id)
            prev = previous.get(run_id)
            if prev is None or prev not in receipts:
                return None  # matched run no longer verified (withdrawn) or absent
            if receipts[prev][1]:
                return None if receipts[prev][2] else prev  # pinned-bundle confirms nothing
            run_id = prev
        return None

    shortcuts = [(rid, at, base(rid)) for rid, (at, wrote, _pinned) in receipts.items()
                 if not wrote and at is not None]
    series_of = db.series_of_runs(sorted({b for _, _, b in shortcuts if b is not None}))
    out: dict[str, str] = {}
    for _rid, at, b in shortcuts:
        for sid in series_of.get(b, ()) if b is not None else ():
            out[sid] = _latest(out.get(sid), at)
    return out


def _scheduler_view(state: SchedulerState, group) -> SchedulerView:
    eligible = next_eligible_at(group_interval(group.specs), failure_streak=state.failure_streak,
                                last_attempt_at=state.last_attempt_at,
                                last_finished_at=state.last_finished_at,
                                last_success_at=state.last_success_at)
    return SchedulerView(state.last_attempt_at, state.last_attempt_state,
                         state.last_finished_at, state.last_success_at, state.failure_streak,
                         eligible.isoformat() if eligible is not None else None)


def _event_counts(rows) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for src, kind, n in rows:
        if src is not None:
            out.setdefault(src, {})[kind] = n
    return out


def build_status(db: Db, specs: list[SeriesSpec], *,
                 now: Callable[[], datetime] | None = None) -> StatusReport:
    """The typed status report from current Db records + registry specs."""
    now_ts = (now or (lambda: datetime.now(timezone.utc)))()

    # dataset identity per ACTIVE series from the authoritative grouping policy
    label_of: dict[str, str] = {}     # series id -> dataset label
    key_of: dict[str, str] = {}       # series id -> dataset_key
    group_of_key: dict = {}           # dataset_key -> DatasetGroup
    by_source: dict[str, list[SeriesSpec]] = {}
    for s in specs:
        by_source.setdefault(s.source.name, []).append(s)
    for name, group in by_source.items():
        active = [s for s in group if s.active]
        if not active:
            continue
        for g in group_specs(active):
            group_of_key[g.key()] = g
            for s in g.specs:
                label_of[s.id] = g.label
                key_of[s.id] = g.key()

    # runs: latest non-legacy attempt per dataset; pending runs
    runs = db.runs_overview()
    latest_by_key: dict[str, tuple[str, str, str]] = {}  # key -> (started_at, state, origin)
    pending: list[PendingRun] = []
    legacy_keys = set()
    for run_id, source, key, state, started, _finished, origin in runs:
        if key is not None and key.startswith(LEGACY_DATASET_PREFIX):
            legacy_keys.add(key)
        if key is None or key.startswith(LEGACY_DATASET_PREFIX):
            continue  # legacy synthetic runs are never an attempt; keys-less rows are not
        if state == "pending-verification":
            started_dt = _parse_ts(started)
            label = group_of_key[key].label if key in group_of_key else key
            pending.append(PendingRun(run_id, label, source, started, origin,
                                      started_dt is not None
                                      and now_ts - started_dt > PENDING_STALE_AFTER))
        cur = latest_by_key.get(key)
        if cur is None or _parse_ts(started) > _parse_ts(cur[0]):
            latest_by_key[key] = (started, state, origin)

    # real verification evidence: PASSED verification rows on non-legacy datasets
    verified_by_key: dict[str, str] = {}   # dataset_key -> latest passed created_at
    channel_by_key: dict[str, str | None] = {}  # dataset_key -> its verifier_channel
    for _run_id, key, passed, created, channel in db.verification_overview():
        if passed and key is not None and key not in legacy_keys:
            latest = _latest(verified_by_key.get(key), created)
            if latest == created:
                channel_by_key[key] = channel
            verified_by_key[key] = latest

    # observation stats per series/kind/state
    stats: dict[tuple, tuple] = {}
    for sid, kind, state, n, max_fetched in db.observation_stats():
        stats[(sid, kind, state)] = (n, max_fetched)
    confirmed_by_shortcut = _shortcut_confirmations(db, runs)
    audit_grade = db.audit_grade_fetched_at()

    events = _event_counts(db.event_totals())
    windowed = {w: _event_counts(db.event_totals(since=(now_ts - span).astimezone(
        timezone.utc).isoformat())) for w, span in EVENT_WINDOWS.items()}
    scheduler = {st.dataset_key: st for st in db.scheduler_states()}

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
        series_out = [_series_status(s, now_ts, label_of, key_of, latest_by_key,
                                     verified_by_key, stats, confirmed_by_shortcut,
                                     audit_grade)
                      for s in sorted(group, key=lambda x: x.id)]
        source_keys = {key_of[s.id] for s in group if s.id in key_of}
        datasets = []
        for k in source_keys:
            if k not in latest_by_key and k not in scheduler:
                continue
            started, state, origin = latest_by_key.get(k, (None, None, None))
            view = _scheduler_view(scheduler[k], group_of_key[k]) if k in scheduler else None
            datasets.append(DatasetStatus(group_of_key[k].label, state, started, origin, view,
                                          channel_by_key.get(k)))
        datasets.sort(key=lambda d: d.label)
        views = [d.scheduler for d in datasets if d.scheduler is not None]
        latest_attempt, latest_state = None, None
        dated = [(s.latest_attempt, s.latest_attempt_state) for s in series_out
                 if s.latest_attempt is not None]
        if dated:
            latest_attempt, latest_state = max(dated, key=lambda d: _parse_ts(d[0]))
        active = [s for s in series_out if s.active]
        sources.append(SourceStatus(
            name=name, verifiable=verifiable, redistribution_ok=redistribution_ok,
            blockers=blockers,
            active_series=len(active),
            inactive_series=len(series_out) - len(active),
            latest_attempt=latest_attempt, latest_attempt_state=latest_state,
            last_verified=_latest(*(s.last_verified for s in series_out)),
            real_data_fetched_at=_latest(*(s.real_data_fetched_at for s in series_out)),
            last_confirmed_current=_latest(*(s.last_confirmed_current for s in series_out)),
            stale=sum(1 for s in active if s.stale is True),
            never_fetched=sum(1 for s in active if s.stale_reason == "never_fetched"),
            never_verified=sum(1 for s in active if s.stale_reason == "never_verified"),
            stale_series=tuple(s.id for s in active if s.stale is True),
            events=events.get(name, {}),
            events_24h=windowed["24h"].get(name, {}),
            events_7d=windowed["7d"].get(name, {}),
            scheduler_retrying=sum(1 for v in views if v.failure_streak),
            scheduler_running=sum(1 for v in views if v.last_attempt_state == "running"),
            scheduler_max_streak=max((v.failure_streak for v in views), default=0),
            pending_runs=tuple(p for p in pending if p.source == name),
            datasets=tuple(datasets), series=tuple(series_out)))
    totals = {"active_series": sum(s.active_series for s in sources),
              "stale": sum(s.stale for s in sources),
              "never_fetched": sum(s.never_fetched for s in sources),
              "never_verified": sum(s.never_verified for s in sources),
              "pending_stuck": sum(p.stale for s in sources for p in s.pending_runs)}
    return StatusReport(generated_at=now_ts.astimezone(timezone.utc).isoformat(),
                        sources=tuple(sources), totals=totals)


def _series_status(s: SeriesSpec, now: datetime, label_of, key_of, latest_by_key,
                   verified_by_key, stats, confirmed_by_shortcut,
                   audit_grade) -> SeriesStatus:
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
    confirmed = None
    if verified:
        availability = "verified"
        real_fetched = _latest(*(mf for _, mf in verified))
        confirmed = _latest(audit_grade.get(s.id), confirmed_by_shortcut.get(s.id))
    elif legacy:
        availability = "legacy-unverified"
        real_fetched = _latest(*(mf for _, mf in legacy))
    else:
        availability = "none"
        real_fetched = None
    if availability == "none":
        stale, reason = None, ("never_fetched" if not fetched_rows else "never_verified")
    elif availability == "legacy-unverified":
        stale, reason = True, "legacy_unverified"  # legacy rows are never confirmed current
    elif confirmed is None:
        stale, reason = True, "pinned_bundle_only"  # verified only against its own bundle
    else:
        stale, reason = now - _parse_ts(confirmed) > series_interval(s), None
    return SeriesStatus(
        id=s.id, active=s.active, frequency=s.frequency, dataset_label=label,
        latest_attempt=latest[0] if latest else None,
        latest_attempt_state=latest[1] if latest else None,
        latest_attempt_origin=latest[2] if latest else None,
        last_verified=last_verified, real_data_fetched_at=real_fetched,
        last_confirmed_current=confirmed,
        availability=availability, legacy_rows=legacy_rows, stale=stale,
        stale_reason=reason)


def _counts(stale: int, never_fetched: int, never_verified: int) -> str:
    return (f"stale {stale} / never fetched {never_fetched} / "
            f"never verified {never_verified}")


def render_text(report: StatusReport) -> str:
    """A compact readable rendering; the JSON form (to_json) is the full typed report."""
    t = report.totals
    lines = [f"prumo status (schema {report.schema} v{report.version}) - "
             f"generated {report.generated_at}",
             "staleness = our refresh policy (schedule or defaults A/S=30d, Q=7d, M/D/PT15M=1d)"
             " judged on the last verified retrieval that confirmed the data current "
             "(an identical re-fetch counts), not a publisher release date; "
             "legacy-only series are always stale",
             f"all sources: {t['active_series']} active series; "
             f"{_counts(t['stale'], t['never_fetched'], t['never_verified'])}; "
             f"pending verification over {report.staleness_policy['pending_stale_after_hours']}"
             f"h {t['pending_stuck']}"]
    for s in report.sources:
        flags = f" BLOCKED ({', '.join(s.blockers)})" if s.blocked else ""
        lines.append(f"{s.name}: {s.active_series} active / {s.inactive_series} inactive "
                     f"series{flags}; {_counts(s.stale, s.never_fetched, s.never_verified)}; "
                     f"latest attempt {s.latest_attempt or '-'} "
                     f"({s.latest_attempt_state or '-'}); "
                     f"last verified {s.last_verified or 'never'}; last confirmed current "
                     f"{s.last_confirmed_current or 'never'}; data fetched "
                     f"{s.real_data_fetched_at or 'none'}")
        lines.append(f"  events 24h {s.events_24h or '{}'}; 7d {s.events_7d or '{}'}; "
                     f"lifetime {s.events or '{}'}")
        if s.datasets:
            lines.append(f"  scheduler: {s.scheduler_retrying} retrying (max streak "
                         f"{s.scheduler_max_streak}), {s.scheduler_running} running or "
                         f"interrupted")
        if s.stale_series:
            shown = s.stale_series[:STALE_LIST_CAP]
            more = len(s.stale_series) - len(shown)
            lines.append(f"  STALE {', '.join(shown)}" + (f" (+{more} more)" if more else ""))
        for d in s.datasets:
            origin = f", input {d.input_origin}" if d.input_origin else ""
            line = (f"  dataset {d.label}: {d.latest_state or 'no attempt'} "
                    f"({d.latest_attempt or '-'}{origin})")
            if d.verifier_channel is not None:
                line += f"; last verified via {d.verifier_channel}"
            v = d.scheduler
            if v is not None:
                state = ("running (in flight, or interrupted if the worker is not "
                         "mid-attempt)" if v.last_attempt_state == "running"
                         else v.last_attempt_state)
                line += (f"; scheduler {state}, streak {v.failure_streak}, next eligible "
                         f"{v.next_eligible_at or 'now'}")
            lines.append(line)
        for p in s.pending_runs:
            mark = (f" STALE (interrupted verification? resolve with: python -m ingest "
                    f"verify {p.run_id})" if p.stale else "")
            lines.append(f"  PENDING run {p.run_id} ({p.dataset}, input {p.input_origin}) "
                         f"since {p.started_at}{mark}")
    return "\n".join(lines)
