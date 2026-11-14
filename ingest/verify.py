"""Truth verification (spec 6b): a seeded sample of a run's observations (ingest.sampling,
procedure prumo-sample-v2) is re-read through an independent, blinded `Verifier`; only a 100%
match moves the run to `verified`.

    pending-verification ──verify_run──> verified             (every sampled item matches)
                                    └──> failed-verification  (any mismatch, not-found, missing
                                         evidence, verifier error / wrong count / wrong key or
                                         order) + event(verification_failure)
                                         + event(verifier_outage) when the channel was down
    run_with_refetch: a genuine failure -> event(refetch) -> a new run_dataset + fresh seed, up
    to max_attempts (1 for recorded input: re-reading the same bundle proves nothing new); a
    verifier OUTAGE never triggers a dataset re-download; giving up writes
    event(verification_escalated). A failed-verification run is never served.

The verifier sees only `BlindItem`s (key + spec); the expected side stays here. Each
verify_run writes one `verification` row (seed, sample procedure + design summary, input
origin, verifier channel, passed), the spec each series was verified with (verification_spec)
and one `verification_item` per sampled observation holding every field the comparison used
(expected and observed text/decimal/unit/flag, the key the verifier answered for, why the item
was drawn, which fields were compared and why unit/flag were not, evidence URL and the sha256
of the evidence bytes kept in the raw store). `replay_item` re-reads that evidence with the
verifier's pure `reread` and re-decides the item offline; `draw_sample` redraws the sample.
"""
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from ingest.db import Db
from ingest.http import Http
from ingest.models import SeriesSpec, parse_decimal
from ingest.pipeline import DatasetRunResult, _iso, _utc_now, run_dataset
from ingest.rawstore import RawStore
from ingest.sampling import DEFAULT_POLICY, SamplingPolicy, design_sample
from ingest.sources import Source
from ingest.verifiers import BlindItem, ItemResult, Verifier, VerifierUnavailable, get_verifier

VERIFIER_CHANNELS = ("live", "pinned-bundle")


class VerificationConflict(ValueError):
    """The run left `pending-verification` while this verification was in progress (another
    worker verified it); this verification's rows were rolled back."""


class NoVerifierRegistered(ValueError):
    """No verifier is registered for the source. Raised by run_with_refetch BEFORE any fetch:
    a source without a verifier can never be served, so fetching from it is wasted work (and
    passing verifier=None used to crash deep inside verify_run after a full fetch)."""


class SourceNotVerifiable(ValueError):
    """The registry marks the source `verifiable: false` (no independent channel, spec 6b).
    Raised by run_with_refetch BEFORE any fetch, even if a verifier were registered."""


@dataclass(frozen=True)
class SampleItem:
    """A sampled observation with its expected side. Internal: verifiers get `blind()` only."""
    series_id: str
    period: str
    expected_text: str  # stored value_text (publisher token, in spec.decimal format)
    spec: SeriesSpec
    expected_unit: str
    expected_flag: str | None
    reason: str  # why it was drawn (ingest.sampling.REASONS)

    def blind(self) -> BlindItem:
        return BlindItem(series_id=self.series_id, period=self.period, spec=self.spec)


def _draw(db: Db, run_id: int, seed: int, specs: list[SeriesSpec], verifier: Verifier,
          policy: SamplingPolicy) -> tuple[list[SampleItem], dict]:
    by_id = {s.id: s for s in specs}
    rows = db.observations_of_run(run_id)
    missing = sorted({r[0] for r in rows} - by_id.keys())
    if missing:
        raise ValueError(f"run {run_id} has series without a spec: {missing}")

    def request_key(key: tuple[str, str]):
        try:
            return ("response", verifier.request_key(BlindItem(key[0], key[1], by_id[key[0]])))
        except Exception:  # a malformed identity: no free closure; check() fails it loudly
            return ("item", key)

    design = design_sample([(r[0], r[1]) for r in rows], seed=seed,
                           changed=db.run_changed_keys(run_id), request_key=request_key,
                           policy=policy, previously_failed=db.previously_failed_keys(run_id))
    items = [SampleItem(series_id=sid, period=period, expected_text=text, spec=by_id[sid],
                        expected_unit=by_id[sid].unit, expected_flag=flag, reason=why)
             for (sid, period, text, flag), why in ((rows[i], why) for i, why in design.chosen)]
    return items, design.summary


def draw_sample(db: Db, run_id: int, seed: int, *, specs: list[SeriesSpec], verifier: Verifier,
                policy: SamplingPolicy = DEFAULT_POLICY) -> list[SampleItem]:
    """The sample of run `run_id` (ingest.sampling, procedure prumo-sample-v2): the latest
    period of every series, every cell that mismatched in a failed verification of the same
    dataset since its last verified run, the run's changed cells (revision/new_periods
    events, capped),
    per-series history strata, a discovery-sized random history sample and every cell read from
    a response those already need (`verifier.request_key`). Same db + seed + policy + verifier
    -> same list, ordered by (series_id, period). ValueError if a series has no spec."""
    return _draw(db, run_id, seed, specs, verifier, policy)[0]


@dataclass(frozen=True)
class _Outcome:
    passed: bool
    outage: str | None  # the verifier channel was unavailable (no item compared)


def verify_run(db: Db, run_id: int, verifier: Verifier, http: Http, seed: int | None = None,
               *, specs: list[SeriesSpec], store: RawStore | None = None,
               now: Callable[[], datetime] = _utc_now, policy: SamplingPolicy = DEFAULT_POLICY,
               verifier_channel: str = "live") -> bool:
    """Verify a `pending-verification` run; True iff it ends `verified`.

    The sample is draw_sample(db, run_id, seed, ...); seed defaults to secrets.randbits(63)
    and is stored either way, with the design summary. The verifier gets the blinded items;
    each result is turned into a stored item row and decided by `_row_mismatch` (key at the
    same position, exact Decimal value, unit/flag when exposed, a recorded reason when not).
    A verifier that raises or returns the wrong number of results fails every item (noted;
    VerifierUnavailable/OSError is additionally recorded as event(verifier_outage)). Evidence
    is mandatory: it is saved to `store` under "verify-<source>"; an item without it fails.

    `verifier_channel` records what the verifier read: 'live' HTTP, or 'pinned-bundle'
    (operator-captured responses; NOT audit-grade, only for recorded input).

    Rows, events and the state change are one transaction; the state change is a
    compare-and-set from pending-verification, so if another worker finished this run meanwhile
    everything is rolled back and VerificationConflict is raised.
    ValueError (nothing written) if the run is not `pending-verification` (e.g. a short-circuit
    `verified` run, which has no verification of its own), the verifier/specs belong to
    another source, the channel is unknown or store is None.
    """
    return _verify(db, run_id, verifier, http, seed, specs=specs, store=store, now=now,
                   policy=policy, verifier_channel=verifier_channel).passed


def _verify(db: Db, run_id: int, verifier: Verifier, http: Http, seed: int | None, *,
            specs: list[SeriesSpec], store: RawStore | None, now: Callable[[], datetime],
            policy: SamplingPolicy, verifier_channel: str) -> _Outcome:
    state = db.run_state(run_id)
    if state != "pending-verification":
        raise ValueError(f"run {run_id} is {state!r}; only pending-verification runs are verified")
    foreign = sorted({s.source.name for s in specs} - {verifier.source_name})
    if foreign:
        raise ValueError(f"verifier for {verifier.source_name!r} cannot verify source(s) {foreign}")
    if verifier_channel not in VERIFIER_CHANNELS:
        raise ValueError(f"verifier_channel must be one of {VERIFIER_CHANNELS}, "
                         f"got {verifier_channel!r}")
    if store is None:
        raise ValueError("verify_run needs a store: evidence is mandatory and archived")
    if seed is None:
        seed = secrets.randbits(63)
    items, design = _draw(db, run_id, seed, specs, verifier, policy)

    results: list = [None] * len(items)
    whole_note = outage = None
    try:
        got = list(verifier.check([i.blind() for i in items], http))
    except (VerifierUnavailable, OSError) as e:  # the channel is down: not a data mismatch
        outage = repr(e)
        whole_note = f"verifier unavailable: {e!r}"
    except Exception as e:  # a broken verifier is a failure, never a pass
        whole_note = f"verifier raised: {e!r}"
    else:
        if len(got) != len(items):
            whole_note = f"verifier returned {len(got)} results for {len(items)} items"
        else:
            results = got

    not_compared = getattr(verifier, "not_compared", {}) or {}
    saved: dict[int, str] = {}  # id(evidence bytes) -> sha256: shared responses saved once
    built = [_item_row(item, res, store, verifier.source_name, not_compared, saved)
             for item, res in zip(items, results)]
    replay = _replay_notes(verifier, items, results, built) if whole_note is None else {}
    rows = []
    for i, (row, note) in enumerate(built):
        note = whole_note or note or replay.get(i) or _row_mismatch(row)
        rows.append({**row, "match": note is None, "note": note})
    bad = [r for r in rows if not r["match"]]
    passed = bool(rows) and not bad

    t = _iso(now())
    with db.transaction():
        vid = db.add_verification(
            run_id, seed, len(rows), passed, t, sample_procedure=design["procedure"],
            sample_design=design, input_origin=db.run_input_origin(run_id),
            verifier_channel=verifier_channel)
        for sid, spec in sorted({i.series_id: i.spec for i in items}.items()):
            db.add_verification_spec(vid, sid, spec.model_dump_json())
        for row in rows:
            db.add_verification_item(vid, row)
        if not passed:
            db.add_event(t, "verification_failure", run_id, {
                "run_id": run_id, "seed": seed, "n_items": len(rows), "n_mismatch": len(bad),
                "first_mismatches": [
                    {"series_id": r["series_id"], "period": r["period"],
                     "expected": r["expected_text"], "observed": r["observed_text"]}
                    for r in bad[:5]]})
        if outage is not None:
            db.add_event(t, "verifier_outage", run_id, {"run_id": run_id, "error": outage,
                                                        "verifier_channel": verifier_channel})
        new_state = "verified" if passed else "failed-verification"
        if not db.transition_run_state(run_id, "pending-verification", new_state):
            raise VerificationConflict(
                f"run {run_id} is no longer pending-verification (now "
                f"{db.run_state(run_id)!r}); this verification was rolled back")
    return _Outcome(passed, outage)


def _str(x: object) -> str | None:
    """Only exact `str` is stored (no subclasses, whose dunders could lie in comparisons);
    anything else a verifier returns is recorded as None."""
    return x if type(x) is str else None


def _item_row(item: SampleItem, res: object, store: RawStore, source_name: str,
              not_compared: dict[str, str], saved: dict[int, str]) -> tuple[dict, str | None]:
    """The stored row for one item (without match/note) and a shape note for a malformed result.
    A malformed result keeps no observed fields, so its stored row can never replay as a match.
    `compared` lists the fields the decision compares; unit/flag left out carry the verifier's
    declared reason (None when it declares none: _row_mismatch then fails the item)."""
    row = {"series_id": item.series_id, "period": item.period,
           "expected_text": item.expected_text, "expected_decimal": item.spec.decimal,
           "expected_unit": item.expected_unit, "expected_flag": item.expected_flag,
           "observed_series_id": None, "observed_period": None, "observed_text": None,
           "observed_decimal": None, "observed_unit": None, "observed_flag": None,
           "evidence_url": None, "evidence_sha256": None, "reason": item.reason,
           "compared": None, "unit_not_compared": None, "flag_not_compared": None}
    if res is None:
        return row, None
    if type(res) is not ItemResult or (res.evidence is not None
                                       and type(res.evidence) is not bytes):
        return row, f"malformed result: {type(res).__name__}"
    if res.evidence is not None:
        if id(res.evidence) not in saved:
            saved[id(res.evidence)] = store.save(f"verify-{source_name}", res.evidence)[0]
        row["evidence_sha256"] = saved[id(res.evidence)]
    row.update(observed_series_id=_str(res.series_id), observed_period=_str(res.period),
               observed_text=_str(res.observed_text),
               observed_decimal=(res.observed_decimal
                                 if _str(res.observed_decimal) in (".", ",") else None),
               observed_unit=_str(res.observed_unit), observed_flag=_str(res.observed_flag),
               evidence_url=_str(res.evidence_url))
    exposed = {"unit": row["observed_unit"] is not None, "flag": row["observed_flag"] is not None}
    row["compared"] = ",".join(["series_id", "period", "value"]
                               + [f for f in ("unit", "flag") if exposed[f]])
    row["unit_not_compared"] = None if exposed["unit"] else not_compared.get("unit")
    row["flag_not_compared"] = None if exposed["flag"] else not_compared.get("flag")
    wrong = [f"{f}: {type(getattr(res, f)).__name__}" for f in _TEXT_FIELDS
             if getattr(res, f) is not None and _str(getattr(res, f)) is None]
    # e.g. a float observed_text (would bypass exact comparison) or a str subclass
    if wrong:
        return row, f"result fields must be exact str: {', '.join(wrong)}"
    if res.evidence is None:
        return row, "no evidence bytes returned (evidence is mandatory)"
    if not res.evidence:
        return row, "empty evidence bytes (evidence is mandatory)"
    return row, None


_CLAIM_FIELDS = ("observed_series_id", "observed_period", "observed_text", "observed_decimal",
                 "observed_unit", "observed_flag")


def _claim_of(res: ItemResult) -> tuple:
    """The stored-claim tuple (_CLAIM_FIELDS order) a verifier result makes."""
    return (_str(res.series_id), _str(res.period), _str(res.observed_text),
            res.observed_decimal if _str(res.observed_decimal) in (".", ",") else None,
            _str(res.observed_unit), _str(res.observed_flag))


def _replay_notes(verifier: Verifier, items: list[SampleItem], results: list,
                  built: list[tuple[dict, str | None]]) -> dict[int, str]:
    """Re-read every well-formed item from the evidence bytes it returned, with the
    verifier's pure `reread` (re-review 2 M1): {item index: why it does not replay}. An
    item is accepted only if what `replay_item` will later re-derive from the archived bytes
    equals the claim stored now, so every stored match replays by construction. Items
    sharing one evidence object go through `reread_many` (one parse) when the verifier has
    it."""
    groups: dict[int, list[int]] = {}
    for i, ((_row, note), res) in enumerate(zip(built, results)):
        if note is None and type(res) is ItemResult:
            groups.setdefault(id(res.evidence), []).append(i)
    many = getattr(verifier, "reread_many", None)
    notes: dict[int, str] = {}
    for idx in groups.values():
        evidence = results[idx[0]].evidence
        blind = [items[i].blind() for i in idx]
        try:
            got = (list(many(evidence, blind)) if many is not None
                   else [verifier.reread(evidence, b) for b in blind])
        except Exception as e:
            for i in idx:
                notes[i] = f"evidence does not re-read (replay would fail): {e!r}"
            continue
        if len(got) != len(idx):
            for i in idx:
                notes[i] = f"reread returned {len(got)} results for {len(idx)} items"
            continue
        for i, res in zip(idx, got):
            if type(res) is not ItemResult:
                notes[i] = f"reread returned {type(res).__name__}, not ItemResult"
                continue
            stored = tuple(built[i][0][k] for k in _CLAIM_FIELDS)
            if _claim_of(res) != stored:
                notes[i] = (f"re-read of the evidence {_claim_of(res)!r} disagrees with the "
                            f"claim {stored!r} (replay would fail)")
    return notes


_TEXT_FIELDS = ("series_id", "period", "observed_text", "evidence_url", "observed_decimal",
                "observed_unit", "observed_flag")


def _blank(s: str | None) -> str | None:
    return s.strip() or None if s is not None else None


def _row_mismatch(row: dict) -> str | None:
    """Why the stored item row is not a match, or None if it is. Uses only stored fields and
    exact Decimals (never float); shared by verify_run and replay_item."""
    if (row["observed_series_id"], row["observed_period"]) != (row["series_id"], row["period"]):
        return (f"result is for {row['observed_series_id']}/{row['observed_period']}, "
                f"expected {row['series_id']}/{row['period']} (wrong order or key)")
    if row["observed_text"] is None:
        return "not found by verifier"
    if row["observed_decimal"] not in (".", ","):
        return "invalid observed_decimal"
    try:
        expected = parse_decimal(row["expected_text"], row["expected_decimal"])
    except ValueError:
        return f"expected_text not a number with decimal {row['expected_decimal']!r}"
    try:
        observed = parse_decimal(row["observed_text"], row["observed_decimal"])
    except ValueError:
        return f"observed_text not a number with decimal {row['observed_decimal']!r}"
    if observed != expected:
        return "value differs"
    if (row["observed_unit"] is not None
            and row["observed_unit"].strip() != (row["expected_unit"] or "").strip()):
        return f"unit differs: expected {row['expected_unit']!r}, observed {row['observed_unit']!r}"
    if row["observed_flag"] is not None and _blank(row["observed_flag"]) != _blank(
            row["expected_flag"]):
        return f"flag differs: expected {row['expected_flag']!r}, observed {row['observed_flag']!r}"
    if row.get("compared") is not None:  # recorded since migration 0012 (B-M1)
        for f in ("unit", "flag"):
            if row[f"observed_{f}"] is None and not row[f"{f}_not_compared"]:
                return f"{f} not exposed and the verifier declares no reason it cannot be"
    return None


def replay_check(db: Db, store: RawStore, verification_item_id: int, verifier: Verifier, *,
                 specs: list[SeriesSpec] | None = None) -> str | None:
    """Re-decide a stored verification_item offline (no network, no registry): None if it
    replays as a match, else why not.

    1. its evidence must have been archived (missing -> not a match) and still hash to its
       name (RawIntegrityError if the file was altered);
    2. `verifier.reread(evidence, item)` - the verifier's PURE re-read of those bytes, with the
       spec the item was verified with (verification_spec; `specs` only for items verified
       before migration 0012) - must not raise and must return exactly the stored claim
       (key, observed text/decimal/unit/flag): a verifier that misread its evidence fails;
    3. the stored comparison is re-decided by `_row_mismatch`.
    ValueError for a legacy (pre-0004) item, a verifier of another source or a pre-0012 item
    without `specs`."""
    row = db.verification_item(verification_item_id)
    if row["expected_decimal"] is None:  # always set since 0004 (spec.decimal is never None)
        raise ValueError(f"verification_item {verification_item_id} is a legacy item "
                         "(pre-0004): its comparison fields were not stored, cannot replay")
    source = db.verification_item_source(verification_item_id)
    if verifier.source_name != source:
        raise ValueError(f"item {verification_item_id} belongs to {source!r}, not "
                         f"{verifier.source_name!r}")
    if row["evidence_sha256"] is None:
        return "no evidence archived for this item"
    sha = row["evidence_sha256"]
    evidence = store.load(store.root / f"verify-{source}" / sha[:2] / sha)
    spec_json = db.verification_item_spec(verification_item_id)
    if spec_json is not None:
        spec = SeriesSpec.model_validate_json(spec_json)
    else:
        spec = next((s for s in specs or [] if s.id == row["series_id"]), None)
        if spec is None:
            raise ValueError(f"verification_item {verification_item_id} predates migration 0012 "
                             f"(no stored spec): pass the registry specs to re-read it")
    try:
        res = verifier.reread(evidence, BlindItem(row["series_id"], row["period"], spec))
    except Exception as e:
        return f"archived evidence does not re-read: {e!r}"
    if type(res) is not ItemResult:
        return f"reread returned {type(res).__name__}, not ItemResult"
    got = _claim_of(res)
    claim = tuple(row[k] for k in _CLAIM_FIELDS)
    if got != claim:
        return f"re-read of the evidence {got!r} disagrees with the stored claim {claim!r}"
    return _row_mismatch(row)


def replay_item(db: Db, store: RawStore, verification_item_id: int, verifier: Verifier, *,
                specs: list[SeriesSpec] | None = None) -> bool:
    """True iff replay_check finds the stored item to be a match re-derived from its evidence."""
    return replay_check(db, store, verification_item_id, verifier, specs=specs) is None


def run_with_refetch(db: Db, store: RawStore, source: Source, verifier: Verifier,
                     specs: list[SeriesSpec], http: Http, max_attempts: int = 3,
                     now: Callable[[], datetime] | None = None, *,
                     input_origin: str = "live", verify_http: Http | None = None,
                     verifier_channel: str = "live",
                     policy: SamplingPolicy = DEFAULT_POLICY) -> DatasetRunResult:
    """run_dataset, then verify_run with a fresh random seed; on a genuine verification
    failure emit event(refetch) and re-fetch the whole dataset (a new run: identical bytes are
    re-processed because the previous run is not verified), at most `max_attempts` runs.

    `verifier` must be the one registered for `source.name` (register_verifier enforces the
    independence rule), else ValueError. Refuses up front (before any fetch): SourceNotVerifiable
    if the registry marks the source `verifiable: false`; NoVerifierRegistered if the source has
    no registered verifier.

    `verify_http` is the verifier's client (default: `http`). Recorded input (B-I3): the
    collector reads a pinned bundle, so the caller passes a LIVE client here
    (verifier_channel='live'); only an explicit non-audit-grade choice pins the verifier to the
    bundle too (verifier_channel='pinned-bundle', recorded input only). `input_origin` labels
    every attempt; recorded input gets ONE attempt (re-reading the same bundle is no refetch).

    A verifier OUTAGE (VerifierUnavailable / OSError: no item could be compared) stops the loop
    at once - re-downloading the dataset cannot fix the verifier's channel. Giving up (outage,
    or the last attempt failed) writes event(verification_escalated, {reason, run_ids, ...})
    and returns `failed-verification` with `detail`. Any other run_dataset outcome
    (failed-fetch, failed-validation, the `verified` short-circuit for a payload identical to
    the previous verified run, which gets no verification) is returned as-is.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    if verifier_channel == "pinned-bundle" and input_origin != "recorded":
        raise ValueError("a pinned-bundle verifier channel is only for recorded input")
    unverifiable = sorted({s.source.name for s in specs if not s.source.verifiable})
    if unverifiable:
        raise SourceNotVerifiable(
            f"source(s) {unverifiable} are marked 'verifiable: false' in the registry: no "
            f"independent verification channel (spec 6b); never served, not fetched here")
    try:
        registered = get_verifier(source.name)
    except KeyError:
        raise NoVerifierRegistered(
            f"no verifier registered for source {source.name!r}: register_verifier() must run "
            f"first; a source without a verifier is never served") from None
    if registered is not verifier:
        raise ValueError(f"verifier is not the one registered for source {source.name!r}")
    now = now or _utc_now
    attempts = 1 if input_origin == "recorded" else max_attempts
    failed: list[int] = []
    for attempt in range(1, attempts + 1):
        result = run_dataset(db, store, source, specs, http, now, input_origin=input_origin)
        if result.state != "pending-verification":
            return result
        out = _verify(db, result.run_id, verifier, verify_http or http, None, specs=specs,
                      store=store, now=now, policy=policy, verifier_channel=verifier_channel)
        if out.passed:
            return replace(result, state="verified")
        failed.append(result.run_id)
        if out.outage is not None:
            return _escalate(db, now, result, failed, "verifier_outage",
                             f"verifier channel unavailable, no re-download: {out.outage}",
                             attempts)
        if attempt < attempts:
            db.add_event(_iso(now()), "refetch", result.run_id,
                         {"failed_run_id": result.run_id, "next_attempt": attempt + 1,
                          "max_attempts": attempts})
    reason = "recorded_input_single_attempt" if input_origin == "recorded" else "max_attempts"
    return _escalate(db, now, result, failed, reason,
                     f"verification failed on {len(failed)} attempt(s) ({reason})", attempts)


def _escalate(db: Db, now: Callable[[], datetime], result: DatasetRunResult, failed: list[int],
              reason: str, detail: str, attempts: int) -> DatasetRunResult:
    db.add_event(_iso(now()), "verification_escalated", result.run_id,
                 {"reason": reason, "run_ids": failed, "max_attempts": attempts,
                  "detail": detail})
    return replace(result, state="failed-verification", detail=detail)
