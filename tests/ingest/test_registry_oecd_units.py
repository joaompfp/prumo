"""Registry <-> OECD publisher evidence pairing for the Task 15 dispositions: the six active
monthly PT series carry the full publisher request identity ('<agency>,<dataflow>/<key>') from
the archived SDMX-JSON responses (tests/ingest/fixtures/oecd/, sha256-pinned by MANIFEST.json,
byte-identical to the controller-rehashed discovery items), with units/multiplier/adjustment
population evidence-backed and ids/indicator_keys/roles/geography preserved.

The registry unit is derived PROSE, not a publisher label: the pairing test re-reads the
UNIT_MEASURE code+label from each archived structure and asserts the reviewed mapping table
(registry/mappings-oecd.md), rather than pretending the publisher prints 'balance %'.
"""
import json
from pathlib import Path

import yaml

from ingest.registry import load_registry
from ingest.sources.oecd import parse_native_code
from tests.ingest.oecd_fixtures import ALL_SIX, FIX, JSON_BY_NATIVE_CODE, MANIFEST

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
MAPPINGS = Path(__file__).resolve().parents[2] / "registry" / "mappings-oecd.md"
LICENCES = Path(__file__).resolve().parents[2] / "registry" / "licences-todo.md"

# id -> (native_code, unit prose, seasonal_adjustment, role, indicator_key)
EXPECTED = {
    "oecd.cli.PT": ("OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H",
                    "index (100=trend)", None, "primary", "oecd_cli.PT.M"),
    "oecd.employment.PT": ("OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.EM.PB.C.Y._Z.FT.N",
                           "balance %", "Calendar and seasonally adjusted",
                           "primary", "oecd_employment.PT.M"),
    "oecd.order_books.PT": ("OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.OB.PB.C.Y._Z.C.N",
                            "balance %", "Calendar and seasonally adjusted",
                            "primary", "oecd_order_books.PT.M"),
    "oecd.production.PT": ("OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.PR.PB.C.Y._Z.T.N",
                           "balance %", "Calendar and seasonally adjusted",
                           "primary", "oecd_production.PT.M"),
    "oecd.selling_prices.PT": ("OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.SP.PB.C.Y._Z.FT.N",
                               "balance %", "Calendar and seasonally adjusted",
                               "primary", "oecd_selling_prices.PT.M"),
    # cross_check of unemployment_rate.PT.M; INE stays the primary source of that indicator.
    "oecd.unemp_m.PT": ("OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M/"
                        "PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M",
                        "%", "Calendar and seasonally adjusted",
                        "cross_check", "unemployment_rate.PT.M"),
}
# reviewed unit-prose derivation from publisher UNIT_MEASURE evidence (registry/mappings-oecd.md)
UNIT_EVIDENCE = {
    "oecd.cli.PT": ("IX", "Index"),
    "oecd.employment.PT": ("PB", "Percentage balance"),
    "oecd.order_books.PT": ("PB", "Percentage balance"),
    "oecd.production.PT": ("PB", "Percentage balance"),
    "oecd.selling_prices.PT": ("PB", "Percentage balance"),
    "oecd.unemp_m.PT": ("PT_LF_SUB", "Percentage of labour force in the same subgroup"),
}
DECIMALS = {"oecd.cli.PT": "2", "oecd.employment.PT": "2", "oecd.order_books.PT": "2",
            "oecd.production.PT": "2", "oecd.selling_prices.PT": "2", "oecd.unemp_m.PT": "1"}


def _oecd():
    return [s for s in load_registry(REGISTRY) if s.source.name == "oecd"]


def _fixture(sid: str):
    return json.loads((FIX / JSON_BY_NATIVE_CODE[EXPECTED[sid][0]]).read_bytes())


def _attr_table(doc, scope: str, attr_id: str) -> dict[str, str]:
    attrs = doc["data"]["structures"][0]["attributes"][scope]
    (a,) = [a for a in attrs if a["id"] == attr_id]
    return {v["id"]: v["name"] for v in a["values"]}


def test_source_licence_flags():
    src = _oecd()[0].source
    assert src.redistribution_ok is False  # §3 grant pending per-dataset third-party clearance
    assert src.verifiable is True  # csvfilewithlabels SDMX CSV channel (Task 15 Part B)
    assert "UNVERIFIED" in src.licence and "§3" in src.licence and "CC BY" not in src.licence
    assert src.licence_url == "https://www.oecd.org/en/about/terms-conditions.html"
    assert src.attribution.startswith("Source: OECD") and "sdmx.oecd.org" in src.attribution


def test_exactly_the_six_active_series_with_preserved_identity_fields():
    series = {s.id: s for s in _oecd()}
    assert set(series) == set(EXPECTED)
    for sid, (nc, unit, adj, role, ikey) in EXPECTED.items():
        s = series[sid]
        assert (s.native_code, s.unit, s.seasonal_adjustment, s.role, s.indicator_key) == \
            (nc, unit, adj, role, ikey)
        parse_native_code(s.native_code)  # raises unless canonical
        assert s.frequency == "M" and s.decimal == "." and s.geography == "PT"
        assert s.active is True  # no inactivation, explicit or default
        assert s.multiplier == 0  # UNIT_MULT=0 observed in evidence
        assert s.base_year is None  # no base year published in channel; none invented
        assert s.url == f"https://sdmx.oecd.org/public/rest/data/{s.native_code}"
        assert len(s.native_code.rsplit("/", 1)[1].split(".")) == 9  # full pinned key


def test_every_registry_unit_is_derived_from_archived_publisher_metadata():
    """UNIT_MEASURE (code + label) re-read from the recorded bodies must match the reviewed
    unit derivation, ADJUSTMENT must be the pinned code, and UNIT_MULT/DECIMALS the recorded
    series attributes."""
    adj_label = {"oecd.cli.PT": "AA"}
    for sid in ALL_SIX:
        doc = _fixture(sid)
        agency, dataflow, key = parse_native_code(EXPECTED[sid][0])
        key_segs = key.split(".")
        dims = {d["id"]: d for d in doc["data"]["structures"][0]["dimensions"]["series"]}
        (series_key, entry), = doc["data"]["dataSets"][0]["series"].items()
        key_pos = series_key.split(":")
        resolved = {d["id"]: d["values"][int(i)]["id"]
                    for i, d in zip(key_pos,
                                    sorted(dims.values(), key=lambda x: x["keyPosition"]))}
        assert [resolved[d["id"]] for d in dims.values()] == key_segs  # full pin identity
        unit_dim = dims["UNIT_MEASURE"]
        pinned = unit_dim["values"][int(key_pos[unit_dim["keyPosition"]])]
        assert (pinned["id"], pinned["name"]) == UNIT_EVIDENCE[sid]
        assert _attr_table(doc, "series", "UNIT_MULT") == {"0": "Units"}
        assert set(_attr_table(doc, "series", "DECIMALS")) == {DECIMALS[sid]}
        oa = _attr_table(doc, "observation", "OBS_STATUS")
        assert oa == {"A": "Normal value"}  # only reviewed code present in evidence
        if sid == "oecd.cli.PT":
            assert resolved["ADJUSTMENT"] == "AA" == adj_label[sid]
        else:
            assert resolved["ADJUSTMENT"] == "Y"


def test_cli_is_bcicp_business_confidence_not_the_li_default():
    """The registry id says 'cli' but the pinned MEASURE is BCICP (composite business
    confidence); the dataflow's DEFAULT annotation references MEASURE=LI - proof the trap is
    real and the explicit pin is required."""
    doc = _fixture("oecd.cli.PT")
    dims = {d["id"]: d for d in doc["data"]["structures"][0]["dimensions"]["series"]}
    assert dims["MEASURE"]["values"][0]["id"] == "BCICP"
    assert dims["MEASURE"]["values"][0]["name"] == "Composite business confidence"
    titles = [a.get("title", "") for a in doc["data"]["structures"][0]["annotations"]]
    assert any(t.startswith("MEASURE=LI,") for t in titles)
    assert all("MEASURE=BCICP" not in t for t in titles)  # BCICP is NOT any default


def test_oecd_rows_keep_the_reviewed_field_shape():
    doc = yaml.safe_load(REGISTRY.read_text())
    rows = [r for r in doc["series"] if r["source"] == "oecd"]
    assert len(rows) == 6
    allowed = {"id", "source", "indicator_key", "role", "theme", "geography", "frequency",
               "unit", "decimal", "native_code", "url", "multiplier", "seasonal_adjustment"}
    for r in rows:
        assert set(r) <= allowed, r["id"]
        assert r["theme"] == "economy"
    assert len({r["id"] for r in rows}) == 6
    assert len({r["native_code"] for r in rows}) == 6


def test_licences_todo_oecd_row_matches_the_reviewed_state():
    row = next(r for r in LICENCES.read_text().splitlines() if r.startswith("| oecd |"))
    assert "READ 2026-11-12" in row and "UNVERIFIED" in row and "redistribution_ok: false" in row
    assert "https://www.oecd.org/en/about/terms-conditions.html" in row
    assert "§3" in row and "third-party" in row and "bot-wall" in row
    assert "CC BY 4.0" in row and "NOT" in row  # the caveat wording, not a blanket licence


def test_mappings_note_documents_every_series_and_the_cli_trap():
    doc = MAPPINGS.read_text()
    for sid in ALL_SIX:
        assert sid in doc, sid
    assert "BCICP" in doc and "MEASURE=LI" in doc
    for nc, *_ in EXPECTED.values():
        agency_df = nc.split("/")[0]
        assert agency_df.split(",")[0] in doc  # agency id mentioned
        assert agency_df.split(",")[1] in doc  # <DSD>@<DF> token mentioned
    assert "cross_check" in doc and "INE" in doc


def test_fixture_manifest_covers_exactly_the_six_json_channels():
    assert sorted(e["file"] for e in MANIFEST["files"]) == sorted(
        JSON_BY_NATIVE_CODE[EXPECTED[sid][0]] for sid in ALL_SIX)
