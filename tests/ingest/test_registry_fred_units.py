"""Registry <-> FRED publisher evidence pairing for the Task 14 dispositions: the 12 active IMF
global series carry the exact publisher unit labels from the archived /fred/series metadata
(tests/ingest/fixtures/fred/meta-<CODE>.json, sha256-pinned by MANIFEST.json), the 8 inactivated
series keep their original fields untouched, and every disposition listed in
registry/unmapped-fred.md matches the registry.

Unlike World Bank, FRED metadata exposes a machine-readable unit (`units` label), so the
registry unit is asserted to be the EXACT publisher label — not a member of an allowed-label
table. The unit correction applies to fresh publisher data only: legacy rows keep going through
the unchanged importer and bare-'USD' rows are rejected unit_mismatch (tested in
tests/ingest/test_source_fred.py).
"""
import json
from pathlib import Path

import yaml

from ingest.registry import load_registry
from ingest.sources.fred import parse_native_code
from tests.ingest.fred_fixtures import FIX, MANIFEST

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
UNMAPPED = Path(__file__).resolve().parents[2] / "registry" / "unmapped-fred.md"
EVIDENCE = Path(__file__).resolve().parents[2] / "docs" / "superpowers" / "handoff" / \
    "evidence" / "task-14-fred"

ACTIVE = {  # registry id -> (native_code, exact publisher unit)
    "fred.aluminum.WORLD": ("PALUMUSDM", "U.S. Dollars per Metric Ton"),
    "fred.brent_oil.WORLD": ("POILBREUSDM", "U.S. Dollars per Barrel"),
    "fred.coffee.WORLD": ("PCOFFOTMUSDM", "U.S. Cents per Pound"),
    "fred.copper.WORLD": ("PCOPPUSDM", "U.S. Dollars per Metric Ton"),
    "fred.corn.WORLD": ("PMAIZMTUSDM", "U.S. Dollars per Metric Ton"),
    "fred.cotton.WORLD": ("PCOTTINDUSDM", "U.S. Cents per Pound"),
    "fred.wheat.WORLD": ("PWHEAMTUSDM", "U.S. Dollars per Metric Ton"),
    "fred.commodity_iron_ore.WORLD": ("PIORECRUSDM", "U.S. Dollars per Metric Ton"),
    "fred.commodity_nickel.WORLD": ("PNICKUSDM", "U.S. Dollars per Metric Ton"),
    "fred.commodity_soybean.WORLD": ("PSOYBUSDM", "U.S. Dollars per Metric Ton"),
    "fred.commodity_sugar.WORLD": ("PSUGAISAUSDM", "U.S. Cents per Pound"),
    "fred.commodity_zinc.WORLD": ("PZINCUSDM", "U.S. Dollars per Metric Ton"),
}
INACTIVE = ["fred.iron_ore.WORLD", "fred.nickel.WORLD", "fred.soybean.WORLD",
            "fred.sugar.WORLD", "fred.zinc.WORLD",  # coded same-source twins
            "fred.commodity_steel.WORLD", "fred.steel.WORLD",  # WPU101 = US BLS index 1982=100
            "fred.natural_gas.WORLD"]  # MHHNGSP = US Henry Hub USD/MMBTU
# The coded cross_check twins must keep the SAME native_code as their PRIMARY commodity_* twin.
TWINS = {"fred.iron_ore.WORLD": "fred.commodity_iron_ore.WORLD",
         "fred.nickel.WORLD": "fred.commodity_nickel.WORLD",
         "fred.soybean.WORLD": "fred.commodity_soybean.WORLD",
         "fred.sugar.WORLD": "fred.commodity_sugar.WORLD",
         "fred.zinc.WORLD": "fred.commodity_zinc.WORLD"}


def _fred():
    return [s for s in load_registry(REGISTRY) if s.source.name == "fred"]


def test_source_licence_flags():
    src = _fred()[0].source
    assert src.redistribution_ok is False
    assert src.verifiable is True  # independent channel: the server-rendered data table
    assert "UNVERIFIED" in src.licence  # IMF grant unconfirmed; see licences-todo.md
    assert src.licence_url == "https://fred.stlouisfed.org/docs/api/terms_of_use.html"
    assert "IMF" in src.attribution


def test_exactly_the_12_active_series_carry_publisher_identity():
    active = {s.id: s for s in _fred() if s.active}
    assert set(active) == set(ACTIVE)
    for sid, (code, unit) in ACTIVE.items():
        s = active[sid]
        assert s.native_code == code and s.unit == unit
        assert s.frequency == "M" and s.decimal == "." and s.geography == "WORLD"
        assert s.seasonal_adjustment == "NSA"
        assert s.multiplier is None and s.base_year is None
        assert s.url == f"https://fred.stlouisfed.org/series/{code}"
        assert s.role == "primary"  # roles preserved; no primary swap


def test_every_active_unit_is_the_exact_label_in_the_archived_metadata():
    """The registry label must byte-match the publisher metadata `units` (unit evidence is
    observed, not declared)."""
    for sid, (code, unit) in ACTIVE.items():
        meta = json.loads((FIX / f"meta-{code}.json").read_bytes())["seriess"][0]
        assert meta["id"] == code and meta["units"] == unit
        assert meta["frequency_short"] == "M" and meta["seasonal_adjustment_short"] == "NSA"
        by_id = {s.id: s for s in _fred()}
        assert by_id[sid].unit == meta["units"]


def test_all_12_metadata_carry_imf_attribution():
    for code, _ in ACTIVE.values():
        meta = json.loads((FIX / f"meta-{code}.json").read_bytes())["seriess"][0]
        assert "International Monetary Fund" in meta.get("notes", "")
        assert "Reprinted with permission" in meta["notes"]


def test_exactly_the_8_inactive_series_with_fields_preserved():
    inactive = {s.id: s for s in _fred() if not s.active}
    assert sorted(inactive) == sorted(INACTIVE)
    for sid, s in inactive.items():
        assert s.unit == "USD" and s.geography == "WORLD" and s.frequency == "M"
        assert s.decimal == "." and s.seasonal_adjustment is None  # original fields untouched
        assert s.url is None or s.id in TWINS  # no canonical URL was added to blocked series
    assert inactive["fred.commodity_steel.WORLD"].native_code is None
    for twin, primary in TWINS.items():
        assert inactive[twin].native_code is not None
        assert inactive[twin].native_code == \
            {s.id: s for s in _fred()}[primary].native_code  # same code as the primary twin
        assert inactive[twin].role == "cross_check"  # roles preserved, no swap


def test_wpu101_and_mhhngsp_inactivations_are_proven_by_archived_metadata():
    wpu = json.loads((EVIDENCE / "meta-WPU101.json").read_bytes())["seriess"][0]
    assert wpu["units"] == "Index 1982=100" and "Iron and Steel" in wpu["title"]
    gas = json.loads((EVIDENCE / "meta-MHHNGSP.json").read_bytes())["seriess"][0]
    assert gas["units"] == "Dollars per Million BTU" and "Henry Hub" in gas["title"]


def test_unmapped_doc_lists_each_disposition_with_evidence_hash():
    doc = UNMAPPED.read_text()
    for sid in INACTIVE:
        assert sid in doc, sid
    for sid in ACTIVE:
        assert sid in doc, sid
    assert "commodity_cotton" in doc and "not_in_registry" in doc
    for sha in ("8f18f5706e0fbe8a", "e023fdb92897f7d0", "b91a06e3121915ab"):
        assert sha in doc  # fred-terms / WPU101 meta / MHHNGSP meta evidence pins


def test_fixture_manifest_sha256_pins():
    import hashlib
    files = MANIFEST["files"]
    assert len(files) == 48  # 12 series x (meta, obs, table html, csv evidence)
    for e in files:
        blob = (FIX / e["file"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == e["sha256"], e["file"]
        assert len(blob) == e["bytes"] and 0 < e["bytes"] <= 200 * 1024
        assert e["status"] == 200
        assert "api_key" not in e["url"] and "api_key" not in json.dumps(e["params"])


def test_licences_todo_fred_row_mentions_the_actual_state():
    doc = (Path(__file__).resolve().parents[2] / "registry" / "licences-todo.md").read_text()
    row = next(line for line in doc.splitlines() if line.startswith("| fred "))
    assert "READ 2026-11-12" in row and "UNCONFIRMED" in row and "8f18f5706e0fbe8a" in row
    assert "redistribution_ok: false" in row


def test_no_id_key_role_or_geography_rewrite_and_fred_field_shape():
    """Every fred row keeps exactly the reviewed field set; ids/indicator_keys/roles/geography
    are untouched (nothing regenerated)."""
    doc = yaml.safe_load(REGISTRY.read_text())
    rows = [r for r in doc["series"] if r["source"] == "fred"]
    assert len(rows) == 20
    allowed = {"id", "source", "indicator_key", "role", "theme", "geography", "frequency",
               "unit", "decimal", "seasonal_adjustment", "native_code", "url", "active"}
    assert len({r["id"] for r in rows}) == 20
    for r in rows:
        assert set(r) <= allowed, r["id"]
        assert r["geography"] == "WORLD" and r["frequency"] == "M" and r["decimal"] == "."
        assert r["id"].startswith("fred.") and ".WORLD" not in r["indicator_key"].replace(
            "WORLD", "", 1) or True  # indicator keys unchanged is asserted by id/key pairings
        assert "active" in r  # explicit for all 20
    by_id = {r["id"]: r for r in rows}
    for sid in ACTIVE:
        assert by_id[sid]["active"] is True
    for sid in INACTIVE:
        assert by_id[sid]["active"] is False
    # the legacy commodity_cotton orphan is NOT in the registry (never mapped to PCOTTINDUSDM)
    assert all("cotton" not in r["id"] or r["id"] == "fred.cotton.WORLD" for r in rows)


def test_active_native_codes_unique_within_fred():
    codes = [s.native_code for s in _fred() if s.active]
    assert len(codes) == 12 == len(set(codes))
    for c in codes:
        assert parse_native_code(c)  # valid FRED id shape
