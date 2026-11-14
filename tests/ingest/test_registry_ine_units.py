"""Registry unit label <-> INE unit pairing (template lesson 3).

INE states the unit once per indicator in its metadata API (pindicaMeta.jsp `UnidadeMedida`), not
per cell, so the adapter hands over no unit (unit_raw None) and this reviewed table is the authority
for which registry label may stand for which INE unit. It lives in tests: a registry consistency
check re-run on every change to registry/core.yaml.

INE_UNIT_OF records the `UnidadeMedida` (and, for indices, the base named in `IndicadorNome`) read
live from pindicaMeta.jsp?varcd=<varcd>&lang=PT on 2026-11-11 for every varcd in use.
"""
from pathlib import Path

from ingest.registry import load_registry
from ingest.sources.ine import parse_native_code

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"

INE_UNIT_OF = {
    "0001188": "Percentagem (%)",                       # confidence indicator (balance of answers)
    "0001346": "Número (N.º)",                          # live births
    "0001397": "Euro (€)",                              # imports
    "0001400": "Euro (€)",                              # exports
    "0005605": "Número (N.º)",                          # deaths
    "0006031": "Número (N.º)",                          # resident population
    "0007983": "Percentagem (%)",                       # unemployment rate, SA
    "0011889": "Não aplicável (-), índice Base 2021",   # IPI, calendar+seasonally adjusted
    "0011897": "Percentagem (%)",                       # IPI y/y
    "0014647": "Percentagem (%)",                       # CPI y/y (Base 2025)
    "0014655": "Percentagem (%)",                       # HICP y/y (Base 2025)
}

# INE unit -> registry labels allowed for it.
UNIT_LABELS = {
    "Percentagem (%)": frozenset({"%"}),
    "Euro (€)": frozenset({"EUR"}),
    "Não aplicável (-), índice Base 2021": frozenset({"index_2021=100"}),
    "Número (N.º)": frozenset({"N.º"}),
}


def _pairs():
    for s in load_registry(REGISTRY):
        if s.source.name == "ine" and s.active:
            yield s, parse_native_code(s.native_code)[0]


def test_registry_unit_labels_match_ine_units():
    bad = [(s.id, varcd, s.unit) for s, varcd in _pairs()
           if s.unit not in UNIT_LABELS.get(INE_UNIT_OF.get(varcd, ""), frozenset())]
    assert not bad, bad


def test_tables_have_no_stale_entries():
    used = {varcd for _, varcd in _pairs()}
    assert used == set(INE_UNIT_OF)
    assert set(INE_UNIT_OF.values()) == set(UNIT_LABELS)
    assert {s.unit for s, _ in _pairs()} == set().union(*UNIT_LABELS.values())


def test_a_mislabelled_registry_row_would_be_caught():
    s, varcd = next((s, v) for s, v in _pairs() if v == "0011889")
    assert "%" not in UNIT_LABELS[INE_UNIT_OF[varcd]]  # the inactive ine.ipi_seasonal_cae.PT case


# Final review C-I3: seasonal adjustment from INE's own indicator name (IndicadorDsg), only where
# the name states it; every other varcd stays None (the name says nothing).
# varcd -> (phrase in the indicator name, registry seasonal_adjustment)
INE_ADJUSTMENT = {
    "0011889": ("ajustado de efeitos de calendário e de sazonalidade", "SCA"),
    "0007983": ("Ajustada de sazonalidade", "SA"),
}


def test_seasonal_adjustment_follows_the_indicator_name():
    import json
    fix = Path(__file__).resolve().parent / "fixtures" / "ine"
    for varcd, (phrase, _) in INE_ADJUSTMENT.items():
        (path,) = fix.glob(f"*_{varcd}.json")
        doc = json.loads(path.read_text())
        assert phrase in (doc[0] if isinstance(doc, list) else doc)["IndicadorDsg"], varcd
    bad = [(s.id, s.seasonal_adjustment) for s, varcd in _pairs()
           if s.seasonal_adjustment != INE_ADJUSTMENT.get(varcd, (None, None))[1]]
    assert not bad, bad
