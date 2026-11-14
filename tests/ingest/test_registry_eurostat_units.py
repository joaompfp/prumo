"""Registry unit label <-> Eurostat unit code pairing (review I3).

The adapter and verifier locate cells by the unit code pinned in native_code; the registry `unit`
is a free-text label. This reviewed table is the authority for which labels may stand for which
Eurostat unit (and currency, where the dataset has one). It lives in tests, not adapter code: it
is a registry consistency check, re-run on every change to registry/core.yaml.

Labels inconsistent for one code (registry not edited; finding for the owner): I21 is 'I21' and
'index_2021'; I15 is 'I15', 'Index (2015=100)' and 'index_2015'; BAL is 'balance' and 'balance %';
I10 is 'I10_2010' and 'index_2010=100'.
"""
from pathlib import Path

from ingest.registry import load_registry
from ingest.sources.eurostat import parse_native_code

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"

# (Eurostat unit code, currency code or None) -> registry labels allowed for it.
# Meaning of each code from the API's dimension labels (unit.category.label).
UNIT_LABELS: dict[tuple[str, str | None], frozenset[str]] = {
    ("BAL", None): frozenset({"balance", "balance %"}),            # balance (% answers)
    ("CLV10_MEUR", None): frozenset({"M_EUR_2010"}),               # chain linked volumes (2010), million euro
    ("CP_EUR_HAB", None): frozenset({"EUR per capita"}),           # current prices, euro per capita
    ("I10", None): frozenset({"I10_2010", "index_2010=100"}),      # index, 2010=100
    # I15 (index, 2015=100): no active series since Task 22 (prc_hicp_midx frozen, C-I1)
    ("I20", None): frozenset({"index 2020=100"}),                  # index, 2020=100
    ("I21", None): frozenset({"I21", "index_2021"}),               # index, 2021=100
    ("KWH", "EUR"): frozenset({"EUR/kWh"}),                        # per kWh, in euro
    ("PC_ACT", None): frozenset({"%"}),                            # % of population in the labour force
    ("PC_GDP", None): frozenset({"% GDP"}),                        # % of gross domestic product
}


def _pairs():
    for s in load_registry(REGISTRY):
        if s.source.name == "eurostat" and s.active:
            key = dict(parse_native_code(s.native_code)[1])
            yield s, (key["unit"], key.get("currency"))


def test_registry_unit_labels_match_eurostat_unit_codes():
    bad = [(s.id, code, s.unit) for s, code in _pairs()
           if s.unit not in UNIT_LABELS.get(code, frozenset())]
    assert not bad, bad


def test_every_label_in_use_is_in_the_table():
    known = set().union(*UNIT_LABELS.values())
    assert {s.unit for s, _ in _pairs()} <= known
    # and the table has no stale code: every code is used by an active series
    assert {code for _, code in _pairs()} == set(UNIT_LABELS)  # no stale code in the table
