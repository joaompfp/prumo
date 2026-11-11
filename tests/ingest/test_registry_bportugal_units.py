"""Registry unit label <-> BPstat metadata pairing (same pattern as test_registry_ine_units.py).

BPstat states the unit once per series in its metadata — the "Unit of measure" dimension (70)
category of the dataset payload and of /api/series/?view_full membercombination — never per cell,
so the adapter derives and CHECKS it from the payload and this reviewed table records, per native
series, the metadata read live on 2026-11-11 (recorded in tests/ingest/fixtures/bportugal/).

BPORTUGAL_META: native series id -> (unit-of-measure label, territory label or None, periodicity
label, distinctive extra dimensions). For 12531993 there is no territory dimension at all: the
series is identified by its currency pair (Reference currency Euro / Counterparty United States
of America, Dollars) and its registry geography is EA by reviewed convention (the euro external
reference rate), NOT the PT default the legacy collector stamped on every BPORTUGAL row.
"""
from pathlib import Path

from ingest.registry import load_registry
from ingest.sources.bportugal import parse_native_code

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"

BPORTUGAL_META = {
    "13168439": ("Percentage", "Euro Area - Changing composition", "Monthly"),  # Euribor 1 month
    "13168436": ("Percentage", "Euro Area - Changing composition", "Monthly"),  # Euribor 3 months
    "13168438": ("Percentage", "Euro Area - Changing composition", "Monthly"),  # Euribor 6 months
    "13168437": ("Percentage", "Euro Area - Changing composition", "Monthly"),  # Euribor 1 year
    "12531993": ("Currency", None, "Monthly"),  # US Dollars (USD) per euro, monthly average
    "12099464": ("Percentage", "Portugal", "Monthly"),   # TB 10y yield, LSEG
    "12560098": ("Percentage", "Germany", "Monthly"),    # Bund 10y yield, LSEG
    "12557378": ("Millions of euros", "Portugal", "Monthly"),   # loans, house purchase (OMFI)
    "12557382": ("Millions of euros", "Portugal", "Monthly"),   # loans, consumer credit (OMFI)
    "12556700": ("Millions of euros", "Portugal", "Monthly"),   # deposits + similars (OMFI)
}

# BPstat unit-of-measure label -> registry units allowed for it. 'Currency' is only accepted for
# the EUR/USD pair (registry unit USD/EUR: US dollars per 1 euro); any other 'Currency' series
# must be reviewed before being added.
UNIT_LABELS = {
    "Percentage": frozenset({"%"}),
    "Millions of euros": frozenset({"MEUR"}),
    "Currency": frozenset({"USD/EUR"}),
}

# BPstat territory label -> registry geography. Corrects the legacy collector's blanket PT.
TERRITORY_LABELS = {
    "Portugal": "PT",
    "Germany": "DE",
    "Euro Area - Changing composition": "EA",
}

_PERIODICITY = {"Monthly": "M"}


def _pairs():
    for s in load_registry(REGISTRY):
        if s.source.name == "bportugal" and s.active:
            yield s, parse_native_code(s.native_code)[0]


def test_registry_units_match_bpstat_unit_of_measure():
    bad = [(s.id, sid, s.unit) for s, sid in _pairs()
           if s.unit not in UNIT_LABELS.get(BPORTUGAL_META.get(str(sid), ("", "", ""))[0],
                                            frozenset())]
    assert not bad, bad


def test_registry_geography_matches_bpstat_territory():
    bad = []
    for s, sid in _pairs():
        _, territory, _ = BPORTUGAL_META[str(sid)]
        if territory is None:
            if s.geography != "EA":  # the documented euro-external-rate convention (eur_usd)
                bad.append((s.id, "no territory dimension", s.geography))
        elif s.geography != TERRITORY_LABELS[territory]:
            bad.append((s.id, territory, s.geography))
    assert not bad, bad


def test_registry_frequency_matches_bpstat_periodicity():
    bad = [(s.id, sid) for s, sid in _pairs()
           if _PERIODICITY.get(BPORTUGAL_META[str(sid)][2]) != s.frequency]
    assert not bad, bad


def test_tables_have_no_stale_entries():
    used = {str(sid) for _, sid in _pairs()}
    assert used == set(BPORTUGAL_META)  # 10 series, no more no fewer
    units = {BPORTUGAL_META[str(sid)][0] for _, sid in _pairs()}
    assert set(UNIT_LABELS) >= units and units  # every table value is exercised by a live series
    assert {s.unit for s, _ in _pairs()} == {u for _, sid in _pairs()
                                             for u in UNIT_LABELS[BPORTUGAL_META[str(sid)][0]]}
