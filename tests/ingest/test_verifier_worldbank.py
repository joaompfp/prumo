"""World Bank verifier tests — recorded genuine publisher CSV ZIP exports
(tests/ingest/fixtures/worldbank/*.zip, full archives <= 200 KB, sha256-pinned by
MANIFEST.json). The verifier is BLIND: it reads values from the CSV channel only; mismatch
detection is verified through verify_run, never by echoing expected values."""
import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

import ingest.verifiers as verifiers
from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.worldbank import WorldBankSource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verifiers.worldbank import WorldBankVerifier
from ingest.verify import replay_item, run_with_refetch, verify_run
from tests.ingest.worldbank_fixtures import (
    GDP_PTDES,
    POP_EUGRAT,
    FixtureHttp,
    registry_specs,
    specs_of,
)
from tests.ingest.worldbank_verifier_fixtures import (
    CSV_URL,
    VerifyFixtureHttp,
    decode_evidence,
    zip_bytes,
)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def _item(sid: str, period: str) -> BlindItem:
    return BlindItem(sid, period, registry_specs()[sid])


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


# (series, period, token) pins from the archived CSV ZIP bytes (see worldbank_verifier_entry)
CASES = [
    ("worldbank.gdp_usd.PT", "2025", "346639825141.821"),
    ("worldbank.gdp_usd.PT", "2021", "256055879091.139"),
    ("worldbank.gdp_usd.DE", "1961", "96558204043.1028"),
    ("worldbank.gdp_usd.ES", "2020", "1289783836971.21"),
    ("worldbank.population.EU", "2025", "451127411"),
    ("worldbank.population.GR", "1960", "8331725"),
    ("worldbank.unemployment_wb.PT", "2025", "6.164"),
    ("worldbank.unemployment_wb.GR", "2024", "10.02"),
]


def test_verifier_reads_every_recorded_case():
    results = WorldBankVerifier().check(
        [_item(s, p) for s, p, _ in CASES], VerifyFixtureHttp())
    assert [(r.series_id, r.period, r.observed_text) for r in results] == list(CASES)
    assert all(r.observed_decimal == "." and r.observed_unit is None
               and r.observed_flag is None for r in results)
    assert [r.evidence_url for r in results] == [
        CSV_URL.format(code=registry_specs()[r.series_id].native_code.split(":")[0])
        for r in results]


def test_verifier_reads_five_pt_gdp_pins_of_the_intake_crosscheck():
    """The intake's 5 cross-channel pins (JSON vs genuine CSV export, 2021..2025) re-derived
    from the archived ZIP."""
    expect = {"2025": "346639825141.821", "2024": "313656884870.859",
              "2023": "292323800948.839", "2022": "256898677175.024",
              "2021": "256055879091.139"}
    results = WorldBankVerifier().check(
        [_item("worldbank.gdp_usd.PT", y) for y in sorted(expect)], VerifyFixtureHttp())
    assert {r.period: r.observed_text for r in results} == expect


def test_verifier_caches_one_zip_fetch_per_indicator_per_check():
    http = VerifyFixtureHttp()
    WorldBankVerifier().check(
        [_item("worldbank.gdp_usd.PT", "2025"), _item("worldbank.gdp_usd.ES", "2020"),
         _item("worldbank.gdp_usd.DE", "1961"), _item("worldbank.population.EU", "2025")],
        http)
    assert http.calls == ["NY.GDP.MKTP.CD", "SP.POP.TOTL"]


def test_verifier_empty_csv_cell_is_not_found_not_zero():
    """An empty quoted cell "" is the publisher's missing marker (never a zero)."""
    (r,) = WorldBankVerifier().check([_item("worldbank.unemployment_wb.PT", "1960")],
                                     VerifyFixtureHttp())
    assert r.observed_text is None and r.evidence  # evidence still archived


def test_verifier_evidence_envelope_carries_exact_zip_url_and_status():
    """ItemResult.evidence = versioned 'worldbank-csv-evidence' v1: the ONE deciding ZIP's exact
    bytes, FINAL url and ACTUAL http status, recoverable offline."""
    (r,) = WorldBankVerifier().check([_item("worldbank.population.EU", "2025")],
                                     VerifyFixtureHttp())
    url = CSV_URL.format(code="SP.POP.TOTL")
    assert r.evidence_url == url
    (rec,) = decode_evidence(r.evidence)
    assert rec == {"url": url, "status": 200, "body": zip_bytes("SP.POP.TOTL")}


def test_verifier_tampered_value_comes_back_verbatim_for_verify_run():
    tampered = _zip_with_main_cell("NY.GDP.MKTP.CD", "PRT", "2025", "346639825141.999")
    (r,) = WorldBankVerifier().check([_item("worldbank.gdp_usd.PT", "2025")],
                                     VerifyFixtureHttp({"NY.GDP.MKTP.CD": tampered}))
    assert r.observed_text == "346639825141.999"  # detection is verify_run's Decimal compare


# --- malformed-channel guards -------------------------------------------------------------

def test_verifier_non_2xx_raises():
    for code in (301, 400, 404, 500):
        with pytest.raises(ValueError, match=f"HTTP {code}"):
            WorldBankVerifier().check([_item("worldbank.gdp_usd.PT", "2025")],
                                      VerifyFixtureHttp(status={"NY.GDP.MKTP.CD": code}))


def test_verifier_html_instead_of_zip_raises():
    with pytest.raises(ValueError, match="ZIP|markup"):
        WorldBankVerifier().check([_item("worldbank.gdp_usd.PT", "2025")],
                                  VerifyFixtureHttp({"NY.GDP.MKTP.CD": b"<!DOCTYPE html>"}))


def test_verifier_malformed_zip_raises():
    body = zip_bytes("NY.GDP.MKTP.CD")[:1000]  # truncated archive
    with pytest.raises(ValueError, match="ZIP"):
        WorldBankVerifier().check([_item("worldbank.gdp_usd.PT", "2025")],
                                  VerifyFixtureHttp({"NY.GDP.MKTP.CD": body}))


def _rezip(code: str, members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def _members(code: str) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes(code))) as z:
        return {n: z.read(n) for n in z.namelist()}


def _main_name(code: str) -> str:
    return next(n for n in _members(code) if n.startswith("API_"))


def _zip_with_main_cell(code: str, iso3: str, year: str, new_token: str) -> bytes:
    """Rebuild the recorded ZIP with exactly one CSV cell replaced (identity kept)."""
    import csv as _csv
    mem = _members(code)
    main = _main_name(code)
    rows = list(_csv.reader(io.StringIO(mem[main].decode("utf-8-sig"))))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == "Country Name")
    yi = rows[hi].index(year)
    hit = 0
    for r in rows[hi + 1:]:
        if len(r) > yi and r[1] == iso3 and r[3] == code:
            old, r[yi] = r[yi], new_token
            hit += 1
    assert hit == 1 and old != new_token
    mem[main] = ("\r\n".join(_csv_escape(r) for r in rows) + "\r\n").encode()
    return _rezip(code, mem)


def _csv_escape(row: list[str]) -> str:
    return ",".join('"' + c.replace('"', '""') + '"' if (i >= 4 or "," in c or '"' in c)
                    else c for i, c in enumerate(row))


def test_verifier_zip_with_unexpected_member_raises():
    mem = _members("SP.POP.TOTL")
    mem["Extra_File.csv"] = b"surprise"
    with pytest.raises(ValueError, match="member"):
        WorldBankVerifier().check([_item("worldbank.population.EU", "2025")],
                                  VerifyFixtureHttp({"SP.POP.TOTL": _rezip("SP.POP.TOTL", mem)}))


def test_verifier_zip_path_traversal_member_raises():
    mem = _members("SP.POP.TOTL")
    del mem["Metadata_Country_API_SP.POP.TOTL_DS2_en_csv_v2_264687.csv"]
    mem["../Metadata_Country_API_SP.POP.TOTL_DS2_en_csv_v2_264687.csv"] = b"x"
    with pytest.raises(ValueError, match="member"):
        WorldBankVerifier().check([_item("worldbank.population.EU", "2025")],
                                  VerifyFixtureHttp({"SP.POP.TOTL": _rezip("SP.POP.TOTL", mem)}))


def test_verifier_zip_member_size_cap_raises(monkeypatch):
    import ingest.verifiers.worldbank as vw
    monkeypatch.setattr(vw, "MAX_MEMBER_BYTES", 100_000)  # main CSV is 297 580 bytes
    with pytest.raises(ValueError, match="too large|exceed"):
        WorldBankVerifier().check([_item("worldbank.gdp_usd.PT", "2025")], VerifyFixtureHttp())


def test_verifier_wrong_indicator_zip_raises():
    """Serving the population ZIP for a GDP item: member names and Indicator Code rows disagree
    with the request — identity drift, fail closed."""
    with pytest.raises(ValueError, match="member|Indicator Code|identity"):
        WorldBankVerifier().check([_item("worldbank.gdp_usd.PT", "2025")],
                                  VerifyFixtureHttp({"NY.GDP.MKTP.CD": zip_bytes("SP.POP.TOTL")}))


def test_verifier_duplicate_year_header_raises():
    mem = _members("SP.POP.TOTL")
    main = _main_name("SP.POP.TOTL")
    tampered = mem[main].replace(b'"2024","2025"', b'"2025","2025"', 1)
    mem[main] = tampered
    with pytest.raises(ValueError, match="year|duplicate"):
        WorldBankVerifier().check([_item("worldbank.population.EU", "2025")],
                                  VerifyFixtureHttp({"SP.POP.TOTL": _rezip("SP.POP.TOTL", mem)}))


def test_verifier_duplicate_country_row_raises():
    mem = _members("SP.POP.TOTL")
    main = _main_name("SP.POP.TOTL")
    text = mem[main].decode("utf-8-sig")
    row = next(line for line in text.splitlines() if line.startswith('"European Union","EUU",'))
    tampered = text.replace(row, row + "\r\n" + row, 1)
    mem[main] = tampered.encode()
    with pytest.raises(ValueError, match="duplicate"):
        WorldBankVerifier().check([_item("worldbank.population.EU", "2025")],
                                  VerifyFixtureHttp({"SP.POP.TOTL": _rezip("SP.POP.TOTL", mem)}))


def test_verifier_last_updated_surface_drift_raises():
    mem = _members("SP.POP.TOTL")
    main = _main_name("SP.POP.TOTL")
    mem[main] = mem[main].replace(b'"Last Updated Date","2026-10-08"',
                                  b'"Updated On","2026-10-08"', 1)
    with pytest.raises(ValueError, match="Last Updated"):
        WorldBankVerifier().check([_item("worldbank.population.EU", "2025")],
                                  VerifyFixtureHttp({"SP.POP.TOTL": _rezip("SP.POP.TOTL", mem)}))


def test_verifier_period_must_be_a_canonical_year():
    with pytest.raises(ValueError, match="period"):
        WorldBankVerifier().check([_item("worldbank.gdp_usd.PT", "2025-M1")],
                                  VerifyFixtureHttp())


def test_verifier_registers_and_passes_allowlist():
    v = WorldBankVerifier()
    register_verifier(v)  # the static independence allowlist runs here
    assert get_verifier("worldbank") is v


def test_verifier_registers_even_in_same_process_as_the_source():
    import ingest.sources.worldbank  # noqa: F401  (loaded: the static allowlist must still pass)
    register_verifier(WorldBankVerifier())


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.worldbank",
                                "tests.ingest.worldbank_verifier_entry:run",
                                source_name="worldbank",
                                blocked_prefixes=("collectors", "ingest.flags", "ingest.sources"))


# --- through the pipeline ------------------------------------------------------------------

@pytest.fixture
def env(db, tmp_path):
    specs = specs_of(GDP_PTDES + POP_EUGRAT)
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def _run(env, src_http=None, seed=7):
    db, specs, store, clock = env
    r = run_dataset(db, store, WorldBankSource(), specs, src_http or FixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_written == 396
    ok = verify_run(db, r.run_id, WorldBankVerifier(), VerifyFixtureHttp(), seed=seed, size=50,
                    specs=specs, store=store, now=clock)
    return db, specs, store, r, ok


def test_verifier_matches_clean_run_through_verify_run(env):
    """Blind verification passes on recorded bytes; CC BY 4.0 (redistribution_ok=true) serves."""
    db, specs, store, r, ok = _run(env)
    assert ok and db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
                      r.run_id)
    assert n >= 50 and passed == 1  # latest per populated series -> at least 6, filled to 50
    items = q(db, "SELECT observed_unit, observed_flag, observed_decimal FROM verification_item")
    assert all(u is None and f is None and d == "." for u, f, d in items)
    assert q(db, "SELECT redistribution_ok FROM source WHERE name='worldbank'") == [(1,)]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(396,)]


def test_archived_evidence_recovers_offline_and_replays(env):
    db, specs, store, r, ok = _run(env)
    assert ok
    rows = q(db, "SELECT id, series_id, evidence_url, evidence_sha256 FROM verification_item")
    assert rows
    seen_payloads = set()
    for item_id, sid, url, sha in rows:
        blob = store.load(store.root / "verify-worldbank" / sha[:2] / sha)  # raises if altered
        code, iso3 = registry_specs()[sid].native_code.split(":")
        (rec,) = decode_evidence(blob)
        assert rec == {"url": url, "status": 200, "body": zip_bytes(code)}
        assert url == CSV_URL.format(code=code)
        seen_payloads.add(sha)
        assert replay_item(db, store, item_id) is True
    # content-addressed store: one archived ZIP payload per indicator used in the sample
    assert len(seen_payloads) == 2  # NY.GDP.MKTP.CD + SP.POP.TOTL


def test_verifier_detects_tampered_value(env):
    """PT GDP 2025 tampered to ...999 in the ZIP channel: blind compare fails the whole run."""
    db, specs, store, r, ok = _run(
        env, seed=13)
    assert ok  # clean first
    db2_specs = specs
    r2 = run_dataset(db, store, WorldBankSource(), db2_specs, FixtureHttp(), Clock())
    assert r2.state == "verified"  # identical payload short-circuits (previous run verified)
    # now a fresh DB: tampered CSV channel vs collected JSON
    dbX = open_db(store.root.parent / "t2.db")
    try:
        sync_registry(dbX, specs)
        r3 = run_dataset(dbX, store, WorldBankSource(), specs, FixtureHttp(), Clock())
        assert r3.state == "pending-verification"
        tampered = _zip_with_main_cell("NY.GDP.MKTP.CD", "PRT", "2025", "346639825141.999")
        assert not verify_run(dbX, r3.run_id, WorldBankVerifier(),
                              VerifyFixtureHttp({"NY.GDP.MKTP.CD": tampered}), seed=13, size=50,
                              specs=specs, store=store, now=Clock())
        assert dbX.run_state(r3.run_id) == "failed-verification"
        bad = q(dbX, "SELECT series_id, period, expected_text, observed_text, note FROM "
                     "verification_item WHERE match=0")
        assert bad == [("worldbank.gdp_usd.PT", "2025", "346639825141.821",
                        "346639825141.999", "value differs")]
        assert q(dbX, "SELECT COUNT(*) FROM served_observation") == [(0,)]
    finally:
        dbX.close()


def test_verifier_detects_tampered_geography_row(env):
    """A row re-labelled to FR still answers the requested identity only if the channel lies:
    the EU row removed from the table -> item not found -> failed-verification."""
    db, specs, store, clock = env
    r = run_dataset(db, store, WorldBankSource(), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification"
    mem = _members("SP.POP.TOTL")
    main = _main_name("SP.POP.TOTL")
    text = mem[main].decode("utf-8-sig")
    row = next(line for line in text.splitlines() if line.startswith('"European Union","EUU",'))
    mem[main] = text.replace(row, row.replace('"EUU"', '"XXX"', 1), 1).encode()
    assert not verify_run(db, r.run_id, WorldBankVerifier(),
                          VerifyFixtureHttp({"SP.POP.TOTL": _rezip("SP.POP.TOTL", mem)}),
                          seed=5, size=50, specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "failed-verification"
    bad = q(db, "SELECT series_id, period, note FROM verification_item WHERE match=0")
    assert any(sid == "worldbank.population.EU" and "not found" in note
               for sid, _, note in bad)


class _BothChannels:
    """run_with_refetch shares one Http between collector and verifier: dispatch by path."""

    def __init__(self):
        self.collector = FixtureHttp()
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "downloadformat=csv" in url or (params or {}).get("downloadformat") == "csv":
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        if "api.worldbank.org" in url and "/country/" in url:
            return self.collector.get(url, params=params, headers=headers, timeout=timeout)
        # verifier builds ?downloadformat=csv via params on some clients: dispatch by host path
        if "api.worldbank.org" in url and "/en/indicator/" in url:
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        raise AssertionError(f"unroutable {url}")


def test_run_with_refetch_verifies_the_registered_verifier(env):
    db, specs, store, clock = env
    v = WorldBankVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, WorldBankSource(), v, specs, _BothChannels(), size=50,
                           now=clock, max_attempts=1)
    assert res.state == "verified"
    [(passed,)] = q(db, "SELECT passed FROM verification")
    assert passed == 1
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(396,)]
