"""OECD independent verifier tests — recorded csvfilewithlabels SDMX-CSV bodies
(tests/ingest/fixtures/oecd/verify/, fetched 2026-11-12, sha256-pinned byte copies of Task 15
discovery items 2,4,6,8,10,12 in MANIFEST.json). Mutations are built IN-TEST only, never stored
as genuine evidence. The verifier reads no other channel: SDMX-JSON/codelists unused.
"""
import base64
import json
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlsplit

import pytest

import ingest.verifiers as verifiers
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.oecd import OecdSource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verifiers.oecd import (
    EVIDENCE_SCHEMA,
    EVIDENCE_VERSION,
    OecdVerifier,
    read_csv_evidence,
)
from ingest.verify import run_with_refetch, verify_run
from tests.ingest.oecd_fixtures import (
    ALL_SIX,
    registry_specs,
    specs_of,
)
from tests.ingest.oecd_fixtures import (
    FixtureHttp as SourceFixtureHttp,
)
from tests.ingest.oecd_verifier_fixtures import (
    CSV_BY_NATIVE_CODE,
    CsvFixtureHttp,
    body,
    csv_values,
    entry,
    extent,
)

CLI, EMP, OB, PR, SP, UNE = ALL_SIX
_PERIOD = re.compile(r"[0-9]{4}-[0-9]{2}")

# (series id, period) named pins, >=5 per dataflow family; expectations are re-derived from the
# ARCHIVED original CSV bytes via the test-only extractor — the exact publisher OBS_VALUE token.
# Each series' pins span its full archived extent, so the double serves the pinned originals
# unfiltered.
PINS = [
    (CLI, "2025-10"), (CLI, "2025-12"), (CLI, "2026-04"), (CLI, "2026-07"), (CLI, "2026-10"),
    (EMP, "2025-10"), (EMP, "2026-10"), (OB, "2025-10"), (OB, "2026-10"),
    (PR, "2025-10"), (PR, "2026-10"), (SP, "2025-10"), (SP, "2026-10"),
    (UNE, "2025-10"), (UNE, "2025-12"), (UNE, "2026-02"), (UNE, "2026-06"), (UNE, "2026-09"),
]


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


def _file(sid: str) -> str:
    return CSV_BY_NATIVE_CODE[registry_specs()[sid].native_code]


def _item(sid: str, period: str, end: str | None = None) -> list:
    """Full-extent pins for one series so the double serves the pinned original unfiltered
    (lo..hi of the archived rows), with `period` inside."""
    lo, hi = extent(_file(sid))
    ps = sorted({lo, period, end or hi})
    return [BlindItem(sid, p, registry_specs()[sid]) for p in ps]


def _one(sid: str, period: str, **kw):
    end = kw.pop("end", None)
    results = OecdVerifier().check(_item(sid, period, end), CsvFixtureHttp(**kw))
    return next(r for r in results if r.period == period)


def _row_line(file: str, period: str) -> str:
    """The single data line whose TIME_PERIOD cell is `period` (header-name located)."""
    text = body(file).decode("utf-8")
    lines = text.split("\r\n")
    ix = lines[0].split(",").index("TIME_PERIOD")
    hits = [ln for ln in lines[1:] if ln and ln.split(",")[ix] == period]
    assert len(hits) == 1, (file, period)
    return hits[0]


def _mutate_row(file: str, period: str, old: str, new: str) -> bytes:
    """In-test mutation: replace inside the ONE data row of `period`; the anchor must occur
    exactly once inside that row. Never written to the fixture files."""
    line = _row_line(file, period)
    assert line.count(old) == 1, (file, period, old)
    return body(file).replace(line.encode("utf-8"),
                              line.replace(old, new, 1).encode("utf-8"), 1)


def _set_cell(file: str, period: str, column: str, value: str) -> bytes:
    """In-test mutation: set one data row's cell (column by header NAME) to `value`."""
    line = _row_line(file, period)
    hdr = body(file).decode("utf-8").split("\r\n")[0].split(",")
    cells = line.split(",")
    cells[hdr.index(column)] = value
    return body(file).replace(line.encode("utf-8"), ",".join(cells).encode("utf-8"), 1)


# ----------------------------------------------------------------------- happy path / pins

def test_named_pins_read_the_exact_publisher_tokens_units_and_flags():
    http = CsvFixtureHttp()
    items = [it for sid, period in PINS for it in _item(sid, period)]
    results = OecdVerifier().check(items, http)
    assert len(http.calls) == 6  # ONE bounded CSV request per distinct series
    by_key = {(r.series_id, r.period): r for r in results}
    for sid, period in PINS:
        spec = registry_specs()[sid]
        r = by_key[(sid, period)]
        expected = csv_values(_file(sid))[period]
        assert expected and r.observed_text == expected  # exact token, no float/rounding
        assert r.observed_unit == spec.unit  # translated from the publisher UNIT_MEASURE code
        assert r.observed_flag == "normal"  # publisher OBS_STATUS A -> normal
        assert r.observed_decimal == "." and r.evidence
        assert r.evidence_url.startswith(
            f"https://sdmx.oecd.org/public/rest/data/{spec.native_code}?")


def test_decimal_trailing_zero_difference_is_exact_not_rounded():
    # JSON collector archives '-6.0'/'12.0'; the CSV channel publishes '-6'/'12'. The verifier
    # returns the CSV token VERBATIM; exact-Decimal equality (not string equality, not rounding)
    # is engine policy in ingest.verify.
    assert csv_values(_file(EMP))["2026-05"] == "-6" and csv_values(_file(SP))["2026-01"] == "12"
    assert _one(EMP, "2026-05").observed_text == "-6"
    assert _one(SP, "2026-01").observed_text == "12"


def test_full_extent_request_is_served_byte_identical_to_the_pinned_original():
    http = CsvFixtureHttp()
    OecdVerifier().check(_item(CLI, "2026-05"), http)
    [(nc, p, headers)] = http.calls
    assert p == {"format": "csvfilewithlabels", "dimensionAtObservation": "AllDimensions",
                 "startPeriod": "2025-10", "endPeriod": "2026-10"}
    assert headers == {}  # no Accept/copy of the collector's JSON header on this channel
    import hashlib

    from tests.ingest.oecd_verifier_fixtures import _windowed
    served = _windowed(_file(CLI), "2025-10", "2026-10")
    assert hashlib.sha256(served).hexdigest() == entry(_file(CLI))["sha256"]


def test_missing_period_is_honest_not_found():
    # an interior row removed IN-TEST: the period is absent, never invented
    line = _row_line(_file(CLI), "2026-02")
    tampered = body(_file(CLI)).replace(line.encode("utf-8") + b"\r\n", b"", 1)
    r = _one(CLI, "2026-02", override={_file(CLI): tampered})
    assert r.observed_text is None and r.observed_flag is None  # a mismatch, decided by verify


def test_sparse_out_of_window_item_periods_still_answer():
    # a bounded sub-window request gets only its rows (publisher window semantics); periods
    # inside the extent but outside the sampled group are simply not asked.
    r = _one(CLI, "2026-03", end="2026-06")  # item group spans 2026-03..2026-06 only
    assert r.observed_text == csv_values(_file(CLI))["2026-03"]


# ----------------------------------------------------------------------- fail-closed drift

def test_non_2xx_raises():
    with pytest.raises(ValueError, match="HTTP 404"):
        _one(CLI, "2026-05", status={registry_specs()[CLI].native_code: 404})


def test_html_or_blank_body_raises():
    with pytest.raises(ValueError, match="HTML|markup"):
        _one(CLI, "2026-05", override={_file(CLI): b"<html><body>Just a moment</body></html>"})
    with pytest.raises(ValueError, match="blank"):
        _one(CLI, "2026-05", override={_file(CLI): b"  \r\n"})


def test_duplicate_header_and_unknown_column_raise():
    text = body(_file(CLI)).decode("utf-8")
    hdr = text.split("\r\n")[0]
    with pytest.raises(ValueError, match="duplicate header"):
        _one(CLI, "2026-05", override={_file(CLI): text.replace(hdr, hdr.replace(
            ",DECIMALS,", ",OBS_VALUE,", 1), 1).encode("utf-8")})
    lines = text.split("\r\n")
    with pytest.raises(ValueError, match="unknown column|unreviewed"):
        _one(CLI, "2026-05", override={_file(CLI): "\r\n".join(
            [ln + (",XTRA" if i == 0 else ",x" if ln else "") for i, ln in
             enumerate(lines)]).encode("utf-8")})


def test_malformed_row_width_raises():
    line = _row_line(_file(CLI), "2026-05")
    with pytest.raises(ValueError, match="width"):
        short = line.rsplit(",", 1)[0].encode("utf-8")
        _one(CLI, "2026-05", override={
            _file(CLI): body(_file(CLI)).replace(line.encode("utf-8"), short, 1)})


def test_duplicate_period_row_raises():
    line = _row_line(_file(CLI), "2026-05").encode("utf-8")
    doubled = line + b"\r\n" + line
    with pytest.raises(ValueError, match="duplicate period"):
        _one(CLI, "2026-05", override={
            _file(CLI): body(_file(CLI)).replace(line, doubled, 1)})


@pytest.mark.parametrize("bad", ["abc", "1e3", "N/A", "1.2.3", "+", ""])
def test_unreviewed_value_tokens_raise(bad):
    with pytest.raises(ValueError, match="OBS_VALUE"):
        _one(CLI, "2026-05", override={
            _file(CLI): _set_cell(_file(CLI), "2026-05", "OBS_VALUE", bad)})


def test_unknown_obs_status_fails_closed():
    # the full OBS_STATUS codelist is NOT enumerable (discovery item 13, 404): only 'A'
    with pytest.raises(ValueError, match="OBS_STATUS"):
        _one(UNE, "2026-02", override={
            _file(UNE): _mutate_row(_file(UNE), "2026-02", ",A,Normal value,", ",E,Estimated,")})


def test_foreign_or_drifted_coordinate_raises():
    with pytest.raises(ValueError, match="coordinate|identity|foreign"):
        _one(CLI, "2026-05", override={
            _file(CLI): _mutate_row(_file(CLI), "2026-05",
                                    ",BCICP,Composite business confidence,",
                                    ",LI,Composite leading indicator,")})  # the BCICP/LI trap
    with pytest.raises(ValueError, match="coordinate|identity|foreign"):
        _one(EMP, "2026-05", override={
            _file(EMP): _set_cell(_file(EMP), "2026-05", "REF_AREA", "ESP")})


def test_out_of_window_period_raises():
    with pytest.raises(ValueError, match="window"):
        _one(CLI, "2026-05", override={
            _file(CLI): _set_cell(_file(CLI), "2026-10", "TIME_PERIOD", "2026-11")})


def test_multiplier_and_base_period_fail_closed():
    with pytest.raises(ValueError, match="UNIT_MULT|multiplier"):
        _one(EMP, "2026-05", override={
            _file(EMP): _mutate_row(_file(EMP), "2026-05", ",0,Units,", ",3,Thousands,")})
    with pytest.raises(ValueError, match="BASE_PER|base"):
        _one(UNE, "2026-02", override={
            _file(UNE): _set_cell(_file(UNE), "2026-02", "BASE_PER", "2020")})


def test_unit_measure_code_and_registry_unit_are_asserted_never_echoed():
    with pytest.raises(ValueError, match="UNIT_MEASURE"):  # unreviewed code/label pair
        _one(CLI, "2026-05", override={
            _file(CLI): _set_cell(_file(CLI), "2026-05", "Unit of measure", "Percent")})
    spec = registry_specs()[EMP].model_copy(update={"unit": "%"})  # registry drift raises too
    with pytest.raises(ValueError, match="!= registry unit"):
        OecdVerifier().check([BlindItem(EMP, "2025-10", spec), BlindItem(EMP, "2026-10", spec)],
                             CsvFixtureHttp())


def test_frequency_adjustment_and_structure_identity_raise():
    spec = registry_specs()[OB].model_copy(update={"frequency": "Q"})
    with pytest.raises(ValueError, match="frequency"):
        OecdVerifier().check([BlindItem(OB, "2025-10", spec), BlindItem(OB, "2026-10", spec)],
                             CsvFixtureHttp())
    spec = registry_specs()[UNE].model_copy(update={"seasonal_adjustment": None})
    with pytest.raises(ValueError, match="adjustment"):
        OecdVerifier().check([BlindItem(UNE, "2025-10", spec), BlindItem(UNE, "2026-09", spec)],
                             CsvFixtureHttp())
    with pytest.raises(ValueError, match="STRUCTURE_ID|dataflow"):
        _one(CLI, "2026-05", override={
            _file(CLI): _mutate_row(_file(CLI), "2026-05", "DSD_STES@DF_CLI(4.1)",
                                    "DSD_STES@DF_BTS(4.0)")})
    with pytest.raises(ValueError, match="ACTION"):
        _one(CLI, "2026-05", override={
            _file(CLI): _set_cell(_file(CLI), "2026-05", "ACTION", "D")})


def test_value_and_period_label_cells_must_stay_blank():
    with pytest.raises(ValueError, match="label"):
        _one(CLI, "2026-05", override={
            _file(CLI): _set_cell(_file(CLI), "2026-05", "Time period", "May 2026")})
    with pytest.raises(ValueError, match="label"):
        _one(UNE, "2026-02", override={
            _file(UNE): _set_cell(_file(UNE), "2026-02", "Observation value", "5.9")})


def test_decimals_is_display_metadata_but_shape_checked():
    with pytest.raises(ValueError, match="DECIMALS|Decimals"):
        _one(CLI, "2026-05", override={
            _file(CLI): _mutate_row(_file(CLI), "2026-05", ",2,Two,", ",2,Three,")})


# ----------------------------------------------------------------------- evidence envelope

def _decode(evidence: bytes) -> dict:
    doc = json.loads(evidence)
    assert doc["schema"] == EVIDENCE_SCHEMA and doc["version"] == EVIDENCE_VERSION
    rec = doc["csv"]
    return {"url": rec["url"], "status": rec["status"],
            "body": base64.b64decode(rec["body_b64"], validate=True)}


def _window_of(url: str) -> tuple[str, str]:
    q_ = dict(parse_qsl(urlsplit(url).query))
    assert q_["format"] == "csvfilewithlabels" and q_["dimensionAtObservation"] == "AllDimensions"
    return q_["startPeriod"], q_["endPeriod"]


def test_evidence_envelope_recovers_values_units_and_flags_offline():
    results = OecdVerifier().check(_item(UNE, "2026-03"), CsvFixtureHttp())
    r = next(x for x in results if x.period == "2026-03")
    rec = _decode(r.evidence)
    assert rec["status"] == 200 and rec["url"] == r.evidence_url
    assert rec["body"] == body(_file(UNE))  # full-extent request -> the pinned original bytes
    # offline replay (NO http): unit + value + flag recover from the envelope bytes alone
    start, end = _window_of(rec["url"])
    unit, values = read_csv_evidence(rec["body"], registry_specs()[UNE].native_code,
                                     registry_specs()[UNE], start=start, end=end)
    assert unit == r.observed_unit
    assert values["2026-03"] == ("5.9", "normal") == (r.observed_text, r.observed_flag)


# ----------------------------------------------------------------------- registration

def test_verifier_registers_and_passes_allowlist():
    v = OecdVerifier()
    register_verifier(v)  # the static independence allowlist runs here
    assert get_verifier("oecd") is v


def test_verifier_registers_even_in_same_process_as_the_source():
    import ingest.sources.oecd  # noqa: F401  (loaded: the static allowlist must still pass)
    register_verifier(OecdVerifier())


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.oecd",
                                "tests.ingest.oecd_verifier_fixtures:run",
                                source_name="oecd",
                                blocked_prefixes=("collectors", "ingest.flags",
                                                  "ingest.sources"))


# ----------------------------------------------------------------------- through the pipeline

@pytest.fixture
def env(db, tmp_path):
    specs = specs_of(ALL_SIX)
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def _source():
    # bounded window of the recorded responses (full history stays the production default)
    return OecdSource(start_period="2025-10", end_period="2026-10")


class _BothChannels:
    """run_with_refetch shares one Http between collector and verifier: the same host carries
    both (params distinguish them — the collector never sends format=csvfilewithlabels)."""

    def __init__(self, verifier: CsvFixtureHttp | None = None):
        self.collector = SourceFixtureHttp()
        self.verifier = verifier or CsvFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if (params or {}).get("format") == "csvfilewithlabels":
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        return self.collector.get(url, params=params, headers=headers, timeout=timeout)


def test_clean_run_verifies_and_stays_unserved(env):
    db, specs, store, clock = env
    r = run_dataset(db, store, _source(), specs, SourceFixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_written == 77 and r.n_quarantined == 0
    assert verify_run(db, r.run_id, OecdVerifier(), CsvFixtureHttp(), seed=7, size=40,
                      specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
                      r.run_id)
    assert passed == 1 and n == 40
    # the licence gate: redistribution_ok=false -> even a verified run serves nothing
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]
    # compared surfaces: unit AND flag from the labelled CSV channel, evidence archived
    assert q(db, "SELECT COUNT(*) FROM verification_item WHERE observed_unit IS NULL OR "
                 "observed_flag IS NULL OR evidence_sha256 IS NULL") == [(0,)]
    urls = {u for (u,) in q(db, "SELECT evidence_url FROM verification_item")}
    assert urls and all(u.startswith("https://sdmx.oecd.org/public/rest/data/")
                        and "format=csvfilewithlabels" in u for u in urls)


def test_registry_unit_drift_fails_verification_and_serves_nothing(db, tmp_path):
    """A drifted registry unit makes the VERIFIER raise (publisher prose != registry): the run
    fails closed, nothing is ever served."""
    specs = [s.model_copy(update={"unit": "Percent"}) if s.id == EMP else s
             for s in specs_of(ALL_SIX)]
    sync_registry(db, specs)
    store, clock = RawStore(tmp_path / "raw"), Clock()
    v = OecdVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, _source(), v, specs, _BothChannels(), size=40,
                           now=clock, max_attempts=1)
    assert res.state == "failed-verification"
    assert q(db, "SELECT passed FROM verification") == [(0,)]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]


def test_run_with_refetch_registered_verifier_all_six(env):
    db, specs, store, clock = env
    v = OecdVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, _source(), v, specs, _BothChannels(), size=40,
                           now=clock, max_attempts=1)
    assert res.state == "verified"
    assert q(db, "SELECT passed FROM verification") == [(1,)]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]  # licence gate
    # provenance: observations come from the collector's SDMX-JSON responses only
    urls = {row[0] for row in q(db, "SELECT DISTINCT r.url FROM observation o JOIN raw_fetch "
                                    "r ON r.id = o.raw_fetch_id WHERE o.dataset_run_id = ?",
                                res.run_id)}
    assert urls and all("format=csvfilewithlabels" not in u for u in urls)


def test_archived_verifier_evidence_replays_offline(env):
    """Every sampled item's evidence_sha256 reloads from the raw store (integrity-checked, no
    HTTP) and decodes to exact CSV bytes; value AND unit AND flag re-derive from the body."""
    db, specs, store, clock = env
    r = run_dataset(db, store, _source(), specs, SourceFixtureHttp(), clock)
    assert verify_run(db, r.run_id, OecdVerifier(), CsvFixtureHttp(), seed=7, size=40,
                      specs=specs, store=store, now=clock)
    rows = q(db, "SELECT series_id, period, evidence_url, evidence_sha256, observed_unit, "
                 "observed_flag, observed_text FROM verification_item")
    assert len(rows) == 40
    by_id = {s.id: s for s in specs}
    for sid, period, url, sha, unit, flag, token in rows:
        blob = store.load(store.root / "verify-oecd" / sha[:2] / sha)  # raises if altered
        rec = _decode(blob)
        assert rec["url"] == url and rec["status"] == 200
        spec = by_id[sid]
        start, end = _window_of(rec["url"])
        got_unit, values = read_csv_evidence(rec["body"], spec.native_code, spec,
                                             start=start, end=end)
        assert got_unit == unit and values[period] == (token, flag)


# ----------------------------------------------------------------------- live (controller-run)

@pytest.mark.live
def test_live_run_with_refetch_all_six_verified_and_served_zero(tmp_path, monkeypatch):
    """Live end-to-end against sdmx.oecd.org — network. Deselected by default
    (pytest.ini adds -m "not live"); the CONTROLLER runs it separately, never this suite:

        .venv-ci/bin/python -m pytest tests/ingest/test_verifier_oecd.py -m live -s

    Real RequestsHttp over BOTH channels, ALL 6 active series, isolated temp db, bounded:
    <=15 req/min (throttle 0.25 rps), 30 s per-request timeout, client retries DISABLED
    (retries=0), ONE whole-dataset attempt (max_attempts=1), at most 18 requests and a <=150 s
    whole-phase deadline asserted around the run. NON-STALE: expectations are re-derived from
    THIS run's freshly archived publisher bytes (raw store re-parsed offline), never frozen
    fixture counts/dates, and verifier expectations from the freshly archived CSV envelopes.
    """
    import time
    from pathlib import Path

    from ingest.db import open_db
    from ingest.http import RequestsHttp
    from ingest.registry import load_registry
    from ingest.sources import RawResponse
    from tests.ingest.oecd_fixtures import ROOT

    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    verifier = OecdVerifier()
    register_verifier(verifier)

    reg = {s.id: s for s in load_registry(ROOT / "registry" / "core.yaml")}
    specs = [reg[sid] for sid in ALL_SIX]
    assert len(specs) == 6 and all(s.active and s.source.verifiable for s in specs)
    # rolling bounded collector window: from 14 months ago (canonical YYYY-MM), no end bound —
    # the publisher answers with whatever is currently published; nothing frozen here.
    today = date.today()
    y, m = (today.year, today.month - 14) if today.month > 2 else (today.year - 1, today.month + 10)
    start = f"{y - (1 if m <= 0 else 0)}-{(m % 12) or 12:02d}" if m <= 0 else f"{y}-{m:02d}"
    assert _PERIOD.fullmatch(start)

    class _Counting:
        def __init__(self, base):
            self.base, self.n = base, 0

        def get(self, url, params=None, headers=None, timeout=None):
            self.n += 1
            return self.base.get(url, params=params, headers=headers, timeout=timeout)

    db = open_db(tmp_path / "live.db")
    try:
        sync_registry(db, specs)
        http = _Counting(RequestsHttp(throttle_rps=0.25, timeout=30.0, retries=0))  # <=15/min
        t0 = time.monotonic()
        result = run_with_refetch(db, RawStore(tmp_path / "raw"),
                                  OecdSource(start_period=start), verifier, specs, http,
                                  size=12, max_attempts=1)
        elapsed = time.monotonic() - t0
        store = RawStore(tmp_path / "raw")
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period) FROM observation "
            "WHERE dataset_run_id = ? GROUP BY series_id", (result.run_id,)).fetchall()
        served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
        verifs = db.conn.execute(
            "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
            (result.run_id,)).fetchall()
        quar = db.conn.execute(
            "SELECT reason, COUNT(*) FROM quarantine WHERE dataset_run_id=? GROUP BY reason",
            (result.run_id,)).fetchall()
        print(f"\nfinal state: {result.state}  run_id={result.run_id}  "
              f"http_calls={http.n}  elapsed={elapsed:.1f}s  served={served}  "
              f"verifications={verifs}")
        for sid, n, lo, hi in sorted(per_series):
            print(f"  {sid}: {n} observations {lo}..{hi}")
        for reason, n in quar:
            print(f"  quarantine: {reason} x{n}")
        assert result.state == "verified"
        assert http.n <= 18 and elapsed <= 150.0  # whole-phase deadline + request cap
        assert {r[0] for r in per_series} == set(ALL_SIX)  # all active series covered
        # Non-stale expectations derived from the run's OWN archived publisher bytes (never
        # frozen counts: OECD revises/publishes monthly). Re-parsing the raw store offline
        # asserts DB == publisher archive exactly, incl. row loss between fetch and write.
        raws = db.conn.execute(
            "SELECT url, params_json, path FROM raw_fetch WHERE dataset_run_id=? AND ok=1 "
            "ORDER BY id", (result.run_id,)).fetchall()
        responses = [RawResponse(url=url, params=json.loads(params_json), status=200,
                                 body=store.load(Path(path)))
                     for url, params_json, path in raws
                     if "format=csvfilewithlabels" not in url]
        assert len(responses) == 6  # the collector's SDMX-JSON responses, not the verifier's
        expected = OecdSource().parse(specs, responses)  # offline, no HTTP
        for sid, n, lo, hi in per_series:
            rows = expected[sid]
            assert rows, f"{sid}: archived publisher response holds no rows"
            assert n == len([r for r in rows if r.value_raw is not None])
            assert (lo, hi) == (rows[0].period_raw, rows[-1].period_raw)
            assert _PERIOD.fullmatch(lo) and _PERIOD.fullmatch(hi)
        assert served == 0  # redistribution_ok=false: verified is not served
        assert verifs == [(12, 1)]
        assert sorted(quar) == sorted({"non_numeric": sum(
            r.value_raw is None for rows in expected.values() for r in rows)}.items())
        # offline evidence replay (no HTTP): every sampled item's archived CSV envelope
        # re-reads value + unit + flag from its stored bytes alone
        items = db.conn.execute(
            "SELECT series_id, period, evidence_url, evidence_sha256, observed_text, "
            "observed_unit, observed_flag FROM verification_item").fetchall()
        assert {i[0] for i in items} == set(ALL_SIX)
        for sid, period, url, sha, token, unit, flag in items:
            blob = store.load(store.root / "verify-oecd" / sha[:2] / sha)
            rec = _decode(blob)
            assert rec["url"] == url and rec["status"] == 200
            s, e = _window_of(rec["url"])
            got_unit, values = read_csv_evidence(rec["body"], reg[sid].native_code, reg[sid],
                                                 start=s, end=e)
            assert values[period] == (token, flag) and got_unit == unit
        print(f"  offline evidence replay: {len(items)} envelopes re-read without HTTP")
    finally:
        db.close()
