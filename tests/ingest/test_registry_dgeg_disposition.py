"""Task 12B DGEG safe disposition (NOT ingestion).

Pins the disposition invariants: all 17 DGEG annual PT series stay in the registry with their
original ids/units/frequencies/geographies/roles/indicator_keys but active=false; the dgeg source
carries verifiable=false (a CURRENT-core-scope eligibility flag, not a claim that no independent
channel can ever exist) and redistribution_ok=false (no data-specific reuse grant established);
core.yaml == core.proposed.yaml and the one-primary-per-indicator_key invariant still holds;
run_with_refetch refuses dgeg BEFORE any fetch even when handed explicit standalone test doubles
(here, not the real network); and the normal registry sync + 0005 licence gate withholds even
synthetic verified/fetched and legacy DGEG rows, legacy_served='1' included (synthetic policy
test — this is NOT a live DGEG ingestion and must never be read as one). Evidence pins make the
disposition auditable without the expiring scratch paths: the original workbook bytes/hash and a
small raw+derived bundle under docs/superpowers/handoff/evidence/task-12-dgeg/.
"""
import hashlib
import json
from pathlib import Path

import pytest

from ingest.db import open_db  # noqa: F401  (fixture module import pattern kept explicit)
from ingest.models import Observation
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.verifiers import get_verifier
from ingest.verify import SourceNotVerifiable, run_with_refetch
from tests.ingest.fakes import FakeHttp

REPO = Path(__file__).parents[2]
REGISTRY = REPO / "registry"
EVIDENCE = REPO / "docs" / "superpowers" / "handoff" / "evidence" / "task-12-dgeg"

# Original publisher workbook (raw XML ground truth for every row coordinate cited in
# registry/unmapped-dgeg.md): sha256/bytes verified byte-identical against the research archive.
WORKBOOK_SHA256 = "5f31904ad33757ba2b52d02fd5107be4054ad94db7e97d1bc17edfda177837be"
WORKBOOK_BYTES = 119336
# Source PDFs of the DERIVED excerpts (the PDFs themselves are NOT committed — too large).
APN_PDF_SHA256 = "d4490a8e3d296ed1895fc5d716db10c30191ef169a09489f7564ede07d0007a7"  # 2369104 B
AEN_PDF_SHA256 = "9486137ed36e25c1a7dbfe5da683ee6d20548c7d405304d1199a11a8378c4db1"  # 13114538 B

# The exact 17 DGEG series that exist in the base registry (7f58a21): id -> (unit, indicator_key).
# Disposition changes ONLY `active`; identity, units, frequency, geography, role and keys are
# byte-preserved (no unit conversions, no display-rounding policy, no re-mapping).
EXPECTED_DGEG = {
    "dgeg.co2_emissions_energy.PT": ("Mton CO2e", "dgeg_co2_emissions_energy.PT.A"),
    "dgeg.co2_emissions_total.PT": ("Mton CO2e", "dgeg_co2_emissions_total.PT.A"),
    "dgeg.consumption_industry.PT": ("ktep", "dgeg_consumption_industry.PT.A"),
    "dgeg.consumption_primary_total.PT": ("ktep", "dgeg_consumption_primary_total.PT.A"),
    "dgeg.consumption_transport.PT": ("ktep", "dgeg_consumption_transport.PT.A"),
    "dgeg.electricity_consumption.PT": ("TWh", "dgeg_electricity_consumption.PT.A"),
    "dgeg.energy_dependence.PT": ("%", "dgeg_energy_dependence.PT.A"),
    "dgeg.energy_intensity.PT": ("tep/M€", "dgeg_energy_intensity.PT.A"),
    "dgeg.energy_intensity_final.PT": ("tep/M€'2021", "dgeg_energy_intensity_final.PT.A"),
    "dgeg.energy_intensity_industry.PT": ("tep/M€'2021", "dgeg_energy_intensity_industry.PT.A"),
    "dgeg.energy_intensity_primary.PT": ("tep/M€2021", "dgeg_energy_intensity_primary.PT.A"),
    "dgeg.energy_intensity_services.PT": ("tep/M€'2021", "dgeg_energy_intensity_services.PT.A"),
    "dgeg.final_energy_consumption.PT": ("Mtep", "dgeg_final_energy_consumption.PT.A"),
    "dgeg.primary_energy_consumption.PT": ("Mtep", "dgeg_primary_energy_consumption.PT.A"),
    "dgeg.renewable_share_electricity.PT": ("%", "dgeg_renewable_share_electricity.PT.A"),
    "dgeg.renewable_share_total.PT": ("%", "dgeg_renewable_share_total.PT.A"),
    "dgeg.renewable_share_transport.PT": ("%", "dgeg_renewable_share_transport.PT.A"),
}

T = "2026-01-01T00:00:00+00:00"


def _core_specs():
    return load_registry(REGISTRY / "core.yaml")


def _dgeg_specs():
    return [s for s in _core_specs() if s.source.name == "dgeg"]


class _StandaloneDgegSourceDouble:
    """CLEARLY LABELLED TEST DOUBLE — not a DGEG adapter (none exists). Any use explodes: the
    disposition must block before fetch/parse are ever reached."""
    name = "dgeg"
    expected_format = "xlsx"

    def fetch(self, specs, http):
        raise AssertionError("TEST DOUBLE: DGEG disposition blocks the run before any fetch")

    def parse(self, specs, responses):
        raise AssertionError("TEST DOUBLE: DGEG disposition blocks the run before any parse")


class _StandaloneDgegVerifierDouble:
    """CLEARLY LABELLED TEST DOUBLE — not a DGEG verifier (none exists or is registered)."""
    source_name = "dgeg"

    def check(self, items, http):
        raise AssertionError("TEST DOUBLE: no DGEG verification exists to call")


def test_exactly_the_expected_17_dgeg_series_all_inactive_identity_preserved():
    specs = {s.id: s for s in _dgeg_specs()}
    assert set(specs) == set(EXPECTED_DGEG), "the DGEG set must be exactly the 17 base series"
    for sid, (unit, key) in EXPECTED_DGEG.items():
        s = specs[sid]
        assert s.active is False, f"{sid} must be inactive (adapters/rules 2+9: never silently eligible)"
        assert s.unit == unit and s.indicator_key == key
        assert s.role == "primary" and s.theme == "energy"
        assert s.geography == "PT" and s.frequency == "A"
        assert s.decimal == "." and s.native_code == "energy-data.db"


def test_core_equals_proposed_and_invariants_hold():
    assert (REGISTRY / "core.yaml").read_text() == (REGISTRY / "core.proposed.yaml").read_text()
    specs = _core_specs()  # load_registry enforces exactly-one-primary per indicator_key
    assert specs and not [s for s in specs if s.source.name == "erse"], \
        "ERSE has zero core series and must not be added here"


def test_dgeg_source_scoped_flags_and_unchanged_licence_fields():
    dgeg = _dgeg_specs()[0].source
    assert dgeg.verifiable is False, "scoped marker: not verifiable AS CURRENTLY CONFIGURED"
    assert dgeg.redistribution_ok is False
    # base licence wording/URL/attribution preserved (evidence detail lives in licences-todo.md)
    assert dgeg.licence == "UNVERIFIED — builder must confirm before serving"
    assert dgeg.licence_url == "https://www.dgeg.gov.pt/"
    assert dgeg.attribution == "Source: DGEG"
    with pytest.raises(KeyError):
        get_verifier("dgeg")  # no DGEG verifier is registered anywhere


def test_run_with_refetch_refuses_dgeg_before_any_network(db, tmp_path):
    """The flags above are not advisory: run_with_refetch must raise SourceNotVerifiable BEFORE
    any source fetch/parse, any verifier call and any HTTP request, even when handed explicit
    standalone test doubles (so this test cannot be read as a live DGEG attempt)."""
    specs = _dgeg_specs()
    assert len(specs) == 17
    sync_registry(db, specs)
    http = FakeHttp()  # empty script: would raise on first get(); must never be touched
    with pytest.raises(SourceNotVerifiable, match="verifiable: false"):
        run_with_refetch(db, RawStore(tmp_path / "raw"), _StandaloneDgegSourceDouble(),
                         _StandaloneDgegVerifierDouble(), specs, http)
    assert http.calls == []
    assert db.conn.execute("SELECT count(*) FROM dataset_run").fetchone()[0] == 0
    assert db.conn.execute("SELECT count(*) FROM raw_fetch").fetchone()[0] == 0


def test_licence_gate_withholds_synthetic_dgeg_rows_fetched_and_legacy(db):
    """SYNTHETIC POLICY TEST ONLY (single hard-coded rows, no source, no verifier, no network):
    after a normal registry sync, the 0005 served_observation licence gate withholds DGEG rows of
    a hypothetical `verified` run AND legacy rows even with legacy_served='1', because the dgeg
    source is redistribution_ok=false. This is NOT a real DGEG ingestion and proves nothing about
    DGEG data; it pins the gate behaviour the disposition relies on."""
    sync_registry(db, _core_specs())
    dep = {s.id: s for s in _core_specs()}["dgeg.energy_dependence.PT"]
    run = db.begin_run("dgeg", "synthetic-only-ds", T)
    fid = db.record_raw_fetch(source_name="dgeg", run_id=run, url="http://synthetic.invalid/x",
                              params_json=None, fetched_at=T, http_status=200,
                              sha256="synthetic", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(dep.id, "2024", "0.64312837828385205",
                                                      decimal=dep.decimal), fid, T)])
    db.set_run_state(run, "verified", finished_at=T)
    legacy = db.legacy_run("dgeg", "legacy:dgeg", T)
    db.write_legacy_observations(legacy, [(Observation.from_raw(
        "dgeg.co2_emissions_total.PT", "2023", "53.3", decimal="."), T)])
    assert db.conn.execute("SELECT count(*) FROM served_observation").fetchone()[0] == 0
    db.conn.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")
    assert db.conn.execute("SELECT count(*) FROM served_observation").fetchone()[0] == 0
    # withheld, not deleted: synthetic rows persist unaudited in storage
    assert db.conn.execute("SELECT count(*) FROM observation").fetchone()[0] == 2


def test_evidence_bundle_workbook_hash_and_manifest(db):
    """The disposition's reasons must outlive the expiring scratch dirs: the original workbook is
    committed byte-pinned, and the manifest identifies every raw vs derived file with its source
    URL/status/hash. Derived excerpts must name the source-PDF sha256 (PDFs are not committed)."""
    wb = EVIDENCE / "dgeg-iie-1995-2024.xlsx"
    body = wb.read_bytes()
    assert len(body) == WORKBOOK_BYTES
    assert hashlib.sha256(body).hexdigest() == WORKBOOK_SHA256
    manifest = json.loads((EVIDENCE / "MANIFEST.json").read_text())
    seen_derived = set()
    for entry in manifest["files"]:
        f = EVIDENCE / entry["path"]
        assert f.is_file(), f"manifest path missing: {entry['path']}"
        data = f.read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]
        assert len(data) == entry["bytes"] and entry["bytes"] <= 200 * 1024
        assert entry["kind"] in ("raw", "derived") and entry["source_url"].startswith("https://")
        if entry["kind"] == "derived":
            seen_derived.add(entry["derived_from"]["sha256"])
            assert "DERIVED" in data.decode("utf-8", "replace").splitlines()[0].upper()
    assert {APN_PDF_SHA256, AEN_PDF_SHA256} <= seen_derived, \
        "APN table text and AEN rights excerpt must derive from the pinned source PDFs"
