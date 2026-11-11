"""Registry unit label <-> World Bank publisher unit evidence pairing, plus the Task 13
registry dispositions (native identity format, ISO3 derivation, the 52-series PPP unit
conflict inactivation). Evidence: the archived 19-indicator metadata sweep and the country
metadata (tests/ingest/fixtures/worldbank/, sha256-pinned by MANIFEST.json).

Both channels expose NO machine-readable per-observation unit or status surface (the API row
fields `unit` and `obs_status` are empty strings in all recorded bytes; the CSV export has no
unit/status columns): units are registry declarations audited against the publisher's
sourceNote prose, NOT observed at verification time (the verifier honestly reports
observed_unit=None / observed_flag=None).

Multiple registry labels legitimately name the SAME publisher unit (Portuguese spellings kept
from the legacy registry — never silently normalized):
    '% PIB'     = '% of GDP'     (PIB = Portuguese GDP)
    'hab.'/'persons' = de facto midyear population count
    '/1000'/'per_1000' = crude rate per 1,000 people
    'anos'/'years'     = years
"""
import json
import re
from pathlib import Path

from ingest.registry import load_registry
from ingest.sources.worldbank import parse_native_code
from tests.ingest.worldbank_fixtures import FIX, MANIFEST

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"

# indicator -> (publisher unit definition per the archived sourceNote prose, allowed registry labels)
WB_UNIT_LABELS = {
    # 'GDP (current US$)': "This indicator is expressed in United States dollars."
    "NY.GDP.MKTP.CD": ("current US$", {"USD"}),
    # 'GDP growth (annual %)': "percentage change ... of the constant price (base year 2015)
    # series" — the PUBLISHED statistic is the annual % change (no 'constant USD' unit)
    "NY.GDP.MKTP.KD.ZG": ("annual %", {"%"}),
    # 'GDP per capita (current US$)'
    "NY.GDP.PCAP.CD": ("current US$", {"USD"}),
    # 'GDP per capita, PPP (current international $)' — "expressed in current prices".
    # REGISTRY CONFLICT: labels 'USD (2017 PPC)'/'USD (2017)' declare constant-2017 dollars.
    # No allowed label: all 52 series are active:false (registry/unmapped-worldbank.md).
    "NY.GDP.PCAP.PP.CD": ("current international $ (NOT constant 2017)", set()),
    "SL.UEM.TOTL.ZS": ("% of total labor force", {"%"}),
    "SL.EMP.TOTL.SP.ZS": ("% of population ages 15+", {"%"}),
    "SL.TLF.CACT.FE.ZS": ("% of female population ages 15+", {"%"}),
    "SP.URB.TOTL.IN.ZS": ("% of total population", {"%"}),
    "NE.EXP.GNFS.ZS": ("% of GDP", {"% PIB"}),
    "NE.IMP.GNFS.ZS": ("% of GDP", {"% PIB"}),
    "NE.RSB.GNFS.ZS": ("% of GDP", {"% PIB"}),
    "BX.KLT.DINV.WD.GD.ZS": ("% of GDP", {"% PIB"}),
    "GC.DOD.TOTL.GD.ZS": ("% of GDP", {"% PIB"}),
    "GB.XPD.RSDV.GD.ZS": ("% of GDP", {"% PIB"}),
    # 'Gini index': "a Gini index of 0 represents perfect equality, while an index of 100
    # implies perfect inequality"
    "SI.POV.GINI": ("Gini index 0..100", {"0-100"}),
    # 'Population, total': "de facto definition of population ... midyear estimates"
    "SP.POP.TOTL": ("persons (de facto midyear count)", {"hab.", "persons"}),
    "SP.DYN.CBRT.IN": ("crude rate per 1,000 people", {"/1000", "per_1000"}),
    "SP.DYN.CDRT.IN": ("crude rate per 1,000 people", {"/1000", "per_1000"}),
    "SP.DYN.LE00.IN": ("years", {"anos", "years"}),
}


def _wb():
    return [s for s in load_registry(REGISTRY) if s.source.name == "worldbank"]


def test_every_active_series_unit_is_in_the_allowed_label_set():
    bad = []
    for s in _wb():
        code, _ = parse_native_code(s.native_code)
        _, allowed = WB_UNIT_LABELS[code]
        if s.active and s.unit not in allowed:
            bad.append((s.id, s.unit, code))
    assert not bad, bad


def test_every_label_in_use_on_active_series_appears_in_the_table():
    used = {s.unit for s in _wb() if s.active}
    tabled = set().union(*(a for _, a in WB_UNIT_LABELS.values()))
    assert used <= tabled
    # and no allowed label is unused on active series or the row would be a stale claim;
    # EXCEPT the PPP set which must be empty by construction (the conflict inactivation)
    per_indicator_used = {}
    for s in _wb():
        if s.active:
            per_indicator_used.setdefault(parse_native_code(s.native_code)[0], set()).add(s.unit)
    for code, (_, allowed) in WB_UNIT_LABELS.items():
        assert per_indicator_used.get(code, set()) == allowed, code


def test_exactly_the_52_ppp_series_are_inactive_with_units_preserved():
    inactive = [s for s in _wb() if not s.active]
    assert len(inactive) == 52
    assert {s.id.split(".")[1] for s in inactive} == {"gdp_per_capita_ppp"}
    assert {parse_native_code(s.native_code)[0] for s in inactive} == {"NY.GDP.PCAP.PP.CD"}
    assert {s.unit for s in inactive} == {"USD (2017 PPC)", "USD (2017)"}  # preserved, not edited
    assert all(s.role == "primary" and s.frequency == "A" for s in inactive)


def test_unmapped_doc_lists_each_inactivated_series_individually():
    doc = (Path(__file__).resolve().parents[2] / "registry" / "unmapped-worldbank.md").read_text()
    listed = sorted(set(re.findall(r"worldbank\.gdp_per_capita_ppp\.[A-Z]{2}", doc)))
    inactive = sorted(s.id for s in _wb() if not s.active)
    assert listed == inactive
    # the documented evidence hash is the controller-pinned PPP metadata body
    assert "a95c4834552a80e2c6b755c22e887d401d7930c2b97453f76fc063108a4a1a8d" in doc


def test_ppp_conflict_proven_by_archived_metadata():
    """The pinned metadata body really does publish 'current international $' and explicitly
    'current prices' (no 2017 constant-dollar claim) — the reason for inactivation."""
    body = (FIX / "meta-NY.GDP.PCAP.PP.CD.json").read_text()
    doc = json.loads(body)
    assert doc[0]["total"] == 1 and doc[1][0]["id"] == "NY.GDP.PCAP.PP.CD"
    assert "current international $" in doc[1][0]["name"]
    assert "current prices" in doc[1][0]["sourceNote"]
    assert doc[1][0]["unit"] == ""  # no machine-readable unit surface (as documented)


def test_indicator_metadata_backing_matches_the_unit_table():
    """Each table justification string is grounded in the archived sourceNote prose."""
    expect_signal = {
        "NY.GDP.MKTP.CD": "United States dollars",
        "NY.GDP.MKTP.KD.ZG": "annual %",
        "NY.GDP.PCAP.CD": "current US$",
        "SL.UEM.TOTL.ZS": "% of total labor force",
        "SP.URB.TOTL.IN.ZS": "% of total population",
        "NE.EXP.GNFS.ZS": "% of GDP",
        "GB.XPD.RSDV.GD.ZS": "% of GDP",
        "SI.POV.GINI": "Gini index",
        "SP.POP.TOTL": "Population, total",
        "SP.DYN.CBRT.IN": "per 1,000 people",
        "SP.DYN.CDRT.IN": "per 1,000 people",
        "SP.DYN.LE00.IN": "years",
    }
    for code, signal in expect_signal.items():
        doc = json.loads((FIX / f"meta-{code}.json").read_text())
        assert doc[0]["total"] == 1 and doc[1][0]["id"] == code
        assert signal in doc[1][0]["name"] or signal in doc[1][0]["sourceNote"]


def test_country_metadata_derives_every_active_series_iso3():
    """The ISO3 in every native_code equals the publisher metadata iso2Code -> id mapping of
    the registry geography (offline, from the archived controller-pinned country metadata)."""
    meta = json.loads((FIX / "country-metadata.json").read_text())
    assert meta[0]["total"] == len(meta[1])  # the archive is the complete one-page listing
    iso2 = {}
    for row in meta[1]:
        assert row["iso2Code"] not in iso2  # unique publisher iso2 codes
        iso2[row["iso2Code"]] = row["id"]
    assert iso2["EU"] == "EUU" and iso2["GR"] == "GRC" and iso2["PT"] == "PRT" \
        and iso2["AT"] == "AUT"
    for s in _wb():
        _, iso3 = parse_native_code(s.native_code)
        assert iso2[s.geography] == iso3, s.id


def test_fixture_manifest_sha256_pins():
    import hashlib
    for e in MANIFEST["files"]:
        blob = (FIX / e["file"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == e["sha256"], e["file"]
        assert len(blob) == e["bytes"] and e["bytes"] <= 200 * 1024 and e["status"] == 200


def test_no_id_unit_role_key_or_geography_rewrite_vs_source_of_truth_shape():
    """Every series keeps exactly the reviewed field set (the registry remains hand-edited,
    never regenerated): id/source/indicator_key/role/theme/geography/frequency/unit/decimal
    + the Task-13 additions native_code/url (/active)."""
    import yaml
    doc = yaml.safe_load(REGISTRY.read_text())
    allowed = {"id", "source", "indicator_key", "role", "theme", "geography", "frequency",
               "unit", "decimal", "native_code", "url", "active"}
    for row in doc["series"]:
        if row["source"] == "worldbank":
            assert set(row) <= allowed, row["id"]
            assert row["role"] == "primary" and row["frequency"] == "A" \
                and row["decimal"] == "."
