"""Operational run policy for the CLI (Task 17A): which sources exist, how a source's series
group into INDEPENDENT dataset runs, how each source's verifier is built and registered ONCE,
and how per-group/source failures surface without stopping the rest.

Boundaries: no SQL here (ingest.db owns every statement) and no printing (ingest.cli owns it);
this module is the small public operations contract the CLI drives. Grouping is the single
authoritative policy — ingest.status derives per-series dataset identity from `group_specs`.
"""
from collections.abc import Callable
from dataclasses import dataclass

from ingest.db import Db
from ingest.http import Http, RequestsHttp
from ingest.models import SeriesSpec
from ingest.pipeline import dataset_key
from ingest.rawstore import RawStore
from ingest.sources import Source
from ingest.sources.bportugal import BPortugalSource
from ingest.sources.eredes import EredesSource
from ingest.sources.eurostat import EurostatSource
from ingest.sources.fred import FredSource
from ingest.sources.ine import INESource
from ingest.sources.oecd import OecdSource
from ingest.sources.ren import RenSource
from ingest.sources.worldbank import WorldBankSource, parse_native_code
from ingest.verifiers import Verifier, get_verifier, register_verifier
from ingest.verifiers.bportugal import BPortugalVerifier
from ingest.verifiers.eredes import EredesVerifier
from ingest.verifiers.eurostat import EurostatVerifier
from ingest.verifiers.fred import FredVerifier
from ingest.verifiers.ine import INEVerifier
from ingest.verifiers.oecd import OecdVerifier
from ingest.verifiers.ren import RenVerifier
from ingest.verifiers.worldbank import WorldBankVerifier
from ingest.verify import run_with_refetch

LEGACY_DATASET_PREFIX = "legacy:"

# Client timeout used when a source's registry `timeout_s` is absent. Kept here (not in the
# CLI) because the scheduler shares the polite-client policy; ingest.cli re-imports it.
DEFAULT_CLIENT_TIMEOUT_S = 30.0


def polite_http(specs: list[SeriesSpec], source_name: str | None = None, *,
                default_timeout_s: float = DEFAULT_CLIENT_TIMEOUT_S) -> Http:
    """The polite per-source Http client policy, shared by the CLI and the Task 18 scheduler
    (extracted from the CLI in Task 18A): min registry throttle_rps over the source's ACTIVE
    series (default 1 rps), the registry timeout_s (the client default when unset - INE
    declares 300 s), and NO client retries (0): client retry budgets must not multiply the
    bounded run_with_refetch attempts. Call only for a source that has active series."""
    active = [s for s in specs if s.active and (source_name is None or s.source.name == source_name)]
    throttle = min((s.throttle_rps for s in active), default=1.0)
    timeouts = {s.source.timeout_s for s in active}
    timeout = None if timeouts == {None} else max(t for t in timeouts if t is not None)
    return RequestsHttp(throttle_rps=throttle, timeout=timeout or default_timeout_s, retries=0)

# Reviewed 2026-11-12 recovery mapping (f0nix probe): the publisher's per-indicator CSV export
# times out on /v2/en/ for these two indicators; the SAME exporter answers under /v2/es/.
# Exact, explicit, per-indicator — everything else keeps the default 'en', no fallback.
WB_INDICATOR_LOCALES = {"NY.GDP.MKTP.KD.ZG": "es", "SL.UEM.TOTL.ZS": "es"}


@dataclass(frozen=True)
class RunRequest:
    """Operational knobs of one run/replay. `window`: optional EXPLICIT E-REDES day window
    (from_ts .. to_ts as canonical UTC day starts) used by replay/catch-up — and by the planned
    17B manual tiny-window procedures; None = every source's native default window."""
    window: tuple[str, str] | None = None
    # 'live' (default) or 'recorded' (validated original-file bundle replay, 17B): labels
    # every attempt's dataset_run, refetches included. 'legacy' is never set by callers.
    input_origin: str = "live"


@dataclass(frozen=True)
class DatasetGroup:
    """One isolated dataset run: a human label plus its series."""
    label: str
    specs: tuple[SeriesSpec, ...]

    def key(self) -> str:
        """The dataset_run.dataset_key this group runs under."""
        return dataset_key(self.specs[0].source.name, [s.id for s in self.specs])


def group_specs(specs: list[SeriesSpec]) -> list[DatasetGroup]:
    """THE authoritative grouping policy. World Bank: ONE dataset per active native indicator
    code (all its registered geographies), so one indicator's CSV outage can never block the
    healthy others. Every other source: one dataset of all given series."""
    if not specs:
        raise ValueError("group_specs needs at least one series")
    names = {s.source.name for s in specs}
    if len(names) != 1:
        raise ValueError(f"group_specs received mixed sources: {sorted(names)}")
    if names.pop() == "worldbank":
        by_code: dict[str, list[SeriesSpec]] = {}
        for s in specs:
            code, _ = parse_native_code(s.native_code)
            by_code.setdefault(code, []).append(s)
        return [DatasetGroup(code, tuple(sorted(g, key=lambda s: s.id)))
                for code, g in sorted(by_code.items())]
    return [DatasetGroup(specs[0].source.name, tuple(sorted(specs, key=lambda s: s.id)))]


@dataclass(frozen=True)
class VerifierOps:
    """How a source's verifier is built, and when an ALREADY-registered instance may be reused
    instead: register_verifier refuses a second instance, so repeated runs/tests in one process
    reuse the registered instance iff it has the same class and a compatible configuration,
    else raise a clear mismatch error. The private registry is never mutated."""
    make: Callable[[], Verifier]
    compatible: Callable[[Verifier], bool]


def ensure_verifier(ops: VerifierOps) -> Verifier:
    """The registered verifier of the source: register on first use; reuse a pre-registered
    instance only when `ops.compatible` says it is interchangeable. The returned instance is
    always the one get_verifier(source) returns, so verify_run/run_with_refetch identity rules
    hold without any private-registry access."""
    probe = ops.make()
    name = probe.source_name
    try:
        existing = get_verifier(name)
    except KeyError:
        register_verifier(probe)
        return probe
    if not ops.compatible(existing):
        raise ValueError(
            f"a verifier for source {name!r} is already registered with an incompatible "
            f"configuration ({type(existing).__name__}); refusing to reuse or replace it — "
            f"run differently configured datasets in separate processes")
    return existing


def _wb_compatible(existing: Verifier) -> bool:
    return (type(existing) is WorldBankVerifier and existing.csv_language == "en"
            and existing.indicator_locales == WB_INDICATOR_LOCALES)


def _same_class(cls: type) -> Callable[[Verifier], bool]:
    return lambda existing: type(existing) is cls


# Lazily evaluated per run: constructing a source can fail on missing credentials (FRED), and
# that must never block other sources or `status`.
def _worldbank(req: RunRequest):
    return WorldBankSource()


def _eurostat(req: RunRequest):
    return EurostatSource()


def _ine(req: RunRequest):
    return INESource()


def _bportugal(req: RunRequest):
    return BPortugalSource()


def _ren(req: RunRequest):
    return RenSource()


def _oecd(req: RunRequest):
    return OecdSource()


def _eredes(req: RunRequest):
    # explicit replay window, else the native last-3-complete-UTC-days default
    return EredesSource(*req.window) if req.window else EredesSource()


def _fred(req: RunRequest):
    return FredSource()  # explicit FRED_API_KEY env only; raises ValueError if absent


SOURCE_FACTORIES: dict[str, Callable[[RunRequest], Source]] = {
    "worldbank": _worldbank,
    "eurostat": _eurostat,
    "ine": _ine,
    "bportugal": _bportugal,
    "ren": _ren,
    "oecd": _oecd,
    "eredes": _eredes,
    "fred": _fred,
}

VERIFIER_OPS: dict[str, VerifierOps] = {
    "worldbank": VerifierOps(
        make=lambda: WorldBankVerifier(csv_language="en",
                                       indicator_locales=dict(WB_INDICATOR_LOCALES)),
        compatible=_wb_compatible),
    "eurostat": VerifierOps(make=EurostatVerifier, compatible=_same_class(EurostatVerifier)),
    "ine": VerifierOps(make=INEVerifier, compatible=_same_class(INEVerifier)),
    "bportugal": VerifierOps(make=BPortugalVerifier, compatible=_same_class(BPortugalVerifier)),
    "ren": VerifierOps(make=RenVerifier, compatible=_same_class(RenVerifier)),
    "oecd": VerifierOps(make=OecdVerifier, compatible=_same_class(OecdVerifier)),
    "eredes": VerifierOps(make=EredesVerifier, compatible=_same_class(EredesVerifier)),
    "fred": VerifierOps(make=FredVerifier, compatible=_same_class(FredVerifier)),
}


@dataclass(frozen=True)
class GroupOutcome:
    """What happened to ONE attempted (or deliberately not attempted) dataset/source."""
    source: str
    group: str          # DatasetGroup label, or the source name when never attempted
    state: str          # final dataset_run state, 'blocked' (not attempted on purpose) or
                        # 'skipped' (nothing active); 'error' = the run raised
    run_id: int | None = None
    n_written: int = 0
    n_quarantined: int = 0
    detail: str | None = None
    # exit-relevant: an active, verifiable source that did not verify fails the aggregate
    # (exit 1). A source reported blocked BECAUSE it is unverifiable/inactive (DGEG) does not.
    exit_relevant: bool = True


@dataclass(frozen=True)
class RunReport:
    outcomes: tuple[GroupOutcome, ...]

    def exit_code(self) -> int:
        bad = [o for o in self.outcomes if o.exit_relevant and o.state != "verified"]
        return 1 if bad else 0

    def by_source(self) -> dict[str, list[GroupOutcome]]:
        out: dict[str, list[GroupOutcome]] = {}
        for o in self.outcomes:
            out.setdefault(o.source, []).append(o)
        return out


def run_source(db: Db, store: RawStore, source_name: str, specs: list[SeriesSpec], *,
               http_for: Callable[[], Http], request: RunRequest = RunRequest(),
               max_attempts: int = 3, size: int = 50, now=None,
               source_factories: dict | None = None, verifier_ops: dict | None = None,
               blocked_groups: dict[str, str] | None = None) -> list[GroupOutcome]:
    """Every dataset group of ONE source, isolated from each other.

    - `verifiable: false` (DGEG) is reported BLOCKED without ANY HTTP or run rows;
    - no active series -> 'skipped';
    - source construction (lazy factory: a missing FRED_API_KEY) or verifier-registration
      failure -> 'blocked' with detail, exit-relevant because the source is active;
    - grouping-policy failures (a malformed registry native_code) and HTTP-client
      construction failures are contained the same way: 'blocked', never an outer abort;
    - `blocked_groups` (dataset_key -> refusal detail) reports those groups 'blocked'
      WITHOUT attempting them (per-group stale-bundle refusal, Task 17 review R1);
    - every group runs through run_with_refetch ONLY, and one group's exception is recorded as
      'error' while the next group/source continues.
    """
    src_specs = [s for s in specs if s.source.name == source_name]
    if not src_specs:
        raise ValueError(f"source {source_name!r} is not in the registry")
    source_spec = src_specs[0].source
    if not source_spec.verifiable:
        return [GroupOutcome(
            source_name, source_name, "blocked", exit_relevant=False,
            detail="registry marks the source 'verifiable: false' (no independent verification "
                   "channel); collected data is historical only - never fetched, never served")]
    active = [s for s in src_specs if s.active]
    if not active:
        return [GroupOutcome(source_name, source_name, "skipped", exit_relevant=False,
                             detail="no active series in the registry")]
    try:
        source = (source_factories or SOURCE_FACTORIES)[source_name](request)
    except Exception as e:
        return [GroupOutcome(source_name, source_name, "blocked",
                             detail=f"source setup failed: {e}")]
    try:
        verifier = ensure_verifier((verifier_ops or VERIFIER_OPS)[source_name])
    except Exception as e:
        return [GroupOutcome(source_name, source_name, "blocked",
                             detail=f"verifier setup failed: {e}")]
    try:
        groups = group_specs(active)
    except ValueError as e:
        return [GroupOutcome(source_name, source_name, "blocked",
                             detail=f"source grouping failed: {e}")]
    try:
        http = http_for()
    except Exception as e:
        return [GroupOutcome(source_name, source_name, "blocked",
                             detail=f"http client setup failed: {e}")]
    outcomes = []
    for group in groups:
        if blocked_groups and group.key() in blocked_groups:
            outcomes.append(GroupOutcome(source_name, group.label, "blocked",
                                         detail=blocked_groups[group.key()]))
            continue
        try:
            r = run_with_refetch(db, store, source, verifier, list(group.specs), http,
                                 max_attempts=max_attempts, size=size, now=now,
                                 input_origin=request.input_origin)
            outcomes.append(GroupOutcome(source_name, group.label, r.state, r.run_id,
                                         r.n_written, r.n_quarantined))
        except Exception as e:
            outcomes.append(GroupOutcome(source_name, group.label, "error",
                                         detail=f"{type(e).__name__}: {e}"))
    return outcomes


def run_all(db: Db, store: RawStore, specs: list[SeriesSpec], *,
            http_for: Callable[[str], Http], request: RunRequest = RunRequest(),
            max_attempts: int = 3, size: int = 50, now=None, only: list[str] | None = None,
            source_factories: dict | None = None, verifier_ops: dict | None = None,
            blocked_groups: dict[str, str] | None = None) -> RunReport:
    """`run all`: every registry source (or `only`), one failure never stopping the rest.
    http_for(source_name) is called lazily per source, only when the source is actually
    attempted (a blocked source makes no HTTP client at all). `blocked_groups`
    (dataset_key -> refusal detail) skips those groups with a 'blocked' outcome while their
    source's healthy groups still run."""
    names = only if only is not None else sorted({s.source.name for s in specs})
    outcomes: list[GroupOutcome] = []
    for name in names:
        outcomes += run_source(db, store, name, specs, http_for=lambda: http_for(name),
                               request=request, max_attempts=max_attempts, size=size, now=now,
                               source_factories=source_factories, verifier_ops=verifier_ops,
                               blocked_groups=blocked_groups)
    return RunReport(tuple(outcomes))
