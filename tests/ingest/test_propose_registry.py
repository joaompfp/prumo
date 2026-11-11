"""Registry proposal from the legacy CSV export (Ruling T), plus the real-export smoke test."""
import tempfile
from pathlib import Path

import pytest

from ingest.db import open_db
from ingest.legacy_import import import_legacy
from ingest.propose_registry import propose
from ingest.registry import load_registry, sync_registry
from tests.ingest.legacy_csv import REAL_EXPORT, write_csv


def _months(n, start=2020):
    return [f"{start + i // 12}-{i % 12 + 1:02d}" for i in range(n)]


def overlap_rows():
    rows = []
    for p in _months(6):
        rows += [("INE", "unemployment", "PT", p, "6.5", "%"),
                 ("EUROSTAT", "unemployment", "PT", p, "6.5", "%"),
                 ("OECD", "unemp_m", "PT", p, "6.6", "%"),
                 ("EUROSTAT", "unemployment", "DE", p, "3.1", "%")]
    for y in ("2021", "2022"):
        rows += [("EUROSTAT", "unemployment", "FR", y, "7.0", "%"),
                 ("WORLDBANK", "unemployment_wb", "FR", y, "7.9", "% pop."),
                 ("WORLDBANK", "population", "MZ", y, "33000000", "hab."),
                 ("DGEG", "energy_dependence", "PT", y, "67.1", "%")]
    return rows


def test_proposal_has_one_primary_per_indicator_key(tmp_path):
    out = tmp_path / "registry"
    propose(write_csv(tmp_path / "l.csv", overlap_rows()), out)
    for name in ("core.proposed.yaml", "core.yaml"):
        text = (out / name).read_text()
        assert text.startswith("# PROVISIONAL — owner review pending")
    assert (out / "core.yaml").read_text() == (out / "core.proposed.yaml").read_text()
    specs = load_registry(out / "core.proposed.yaml")  # enforces exactly one primary per key
    keys = {s.indicator_key for s in specs}
    assert len(keys) == len([s for s in specs if s.role == "primary"])
    assert {s.id for s in specs} == {
        "ine.unemployment.PT", "eurostat.unemployment.PT", "oecd.unemp_m.PT",
        "eurostat.unemployment.DE", "eurostat.unemployment.FR",
        "worldbank.unemployment_wb.FR", "worldbank.population.MZ",
        "dgeg.energy_dependence.PT"}
    by_id = {s.id: s for s in specs}
    assert by_id["ine.unemployment.PT"].indicator_key == by_id["oecd.unemp_m.PT"].indicator_key
    assert by_id["worldbank.population.MZ"].theme == "demography"
    assert by_id["dgeg.energy_dependence.PT"].theme == "energy"  # DGEG headline = core energy
    assert by_id["eurostat.unemployment.FR"].role == "primary"  # Eurostat for European data
    assert by_id["worldbank.unemployment_wb.FR"].role == "cross_check"
    assert by_id["worldbank.unemployment_wb.FR"].unit == "% pop."  # units kept as in the data
    db = open_db(tmp_path / "fresh.db")
    try:
        sync_registry(db, specs)
        assert db.conn.execute("SELECT count(*) FROM series").fetchone()[0] == len(specs)
    finally:
        db.close()
    overlaps = (out / "overlaps.md").read_text()
    assert "unemployment_rate.PT.M" in overlaps and "unemployment_rate.FR.A" in overlaps
    assert "LARGE" in overlaps  # 7.0 vs 7.9 is a large disagreement


def test_proposal_prefers_portuguese_institution(tmp_path):
    out = tmp_path / "registry"
    propose(write_csv(tmp_path / "l.csv", overlap_rows()), out)
    roles = {s.id: s.role for s in load_registry(out / "core.yaml")}
    assert roles["ine.unemployment.PT"] == "primary"
    assert roles["eurostat.unemployment.PT"] == "cross_check"
    assert roles["oecd.unemp_m.PT"] == "cross_check"
    assert roles["eurostat.unemployment.DE"] == "primary"  # European geography: Eurostat


def test_proposal_leaves_out_tail_mixed_units_and_unknowns(tmp_path):
    rows = [("DGEG", "price_diesel_pvp", "PT", p, "1.7", "EUR/litro") for p in _months(3)]
    rows += [("EUROSTAT", "hicp", "PT", "2020-01", "100", "index_2015"),
             ("EUROSTAT", "hicp", "PT", "2020-02", "101", "Index (2015=100)"),
             ("INE", "mystery_indicator", "PT", "2020-01", "1", "%"),
             ("BPORTUGAL", "euribor_3m", "PT", "2020-01", "0.1", ""),
             ("EUROSTAT", "unemployment_m", "PT", "2020-01", "347.0", "PC_ACT"),
             ("INE", "gdp_yoy", "PT", "2024-10", "2.6", "%"),
             ("INE", "gdp_yoy", "PT", "2025-01", "1.6", "%"),
             ("INE", "gdp_yoy", "PT", "2025-04", "1.7", "%"),
             ("INE", "gdp_yoy", "PT", "2025-07", "2.2", "%")]
    out = tmp_path / "registry"
    propose(write_csv(tmp_path / "l.csv", rows), out)
    assert load_registry(out / "core.yaml") == []
    tail = (out / "deferred-tail.md").read_text()
    assert "price_diesel_pvp" in tail
    unclassified = (out / "unclassified.md").read_text()
    for ind in ("hicp", "mystery_indicator", "euribor_3m", "gdp_yoy", "unemployment_m"):
        assert ind in unclassified


def test_proposal_licences_not_invented(tmp_path):
    out = tmp_path / "registry"
    propose(write_csv(tmp_path / "l.csv", overlap_rows()), out)
    sources = {s.source.name: s.source for s in load_registry(out / "core.yaml")}
    assert sources["eurostat"].licence == "CC BY 4.0" and sources["eurostat"].redistribution_ok
    for name in ("ine", "oecd"):
        assert sources[name].licence.startswith("UNVERIFIED")  # INE, OECD: not confirmed
        assert not sources[name].redistribution_ok
        assert name in (out / "licences-todo.md").read_text().lower()



def test_overlap_gap_uses_only_rows_with_an_explicit_unit(tmp_path):
    """Unitless legacy rows (another base-year vintage) never enter the gap; they are listed as
    quarantined in unclassified.md instead."""
    rows = []
    for p in _months(3, 2010):  # unitless Eurostat vintage: far from INE
        rows += [("EUROSTAT", "ipi", "PT", p, "98.7", ""),
                 ("INE", "ipi_seasonal_cae_TOT", "PT", p, "105.96", "index_2021=100")]
    for p in _months(3, 2018):  # explicit I21: agrees with INE
        rows += [("EUROSTAT", "ipi", "PT", p, "108.2", "I21"),
                 ("INE", "ipi_seasonal_cae_TOT", "PT", p, "108.16", "index_2021=100")]
    out = tmp_path / "registry"
    propose(write_csv(tmp_path / "l.csv", rows), out)
    overlaps = (out / "overlaps.md").read_text()
    line = next(x for x in overlaps.splitlines() if x.startswith("| ipi_total.PT.M"))
    assert "| 3 |" in line and "LARGE" not in line  # only the 3 explicit-unit periods compared
    unclassified = (out / "unclassified.md").read_text()
    section = unclassified.split("## Legacy rows quarantined: unit missing")[1]
    assert "eurostat.ipi.PT" in section and "2010-01 .. 2010-03" in section


def test_series_without_any_explicit_unit_not_core_and_listed(tmp_path):
    rows = [("BPORTUGAL", "euribor_3m", "PT", p, "0.1", "") for p in _months(4)]
    out = tmp_path / "registry"
    propose(write_csv(tmp_path / "l.csv", rows), out)
    assert load_registry(out / "core.yaml") == []
    section = (out / "unclassified.md").read_text().split("## Legacy rows quarantined: unit missing")[1]
    assert "bportugal.euribor_3m.PT" in section and "| 4 |" in section


def test_why_is_truthful(tmp_path):
    rows = []
    for p in _months(4):
        rows += [("EUROSTAT", "cci", "PT", p, "-10", "balance"),
                 ("EUROSTAT", "consumer_confidence", "PT", p, "-10", "balance %")]
    rows += [("EUROSTAT", "cci", "PT", "2021-01", "-9", "balance")]
    out = tmp_path / "registry"
    propose(write_csv(tmp_path / "l.csv", rows), out)
    line = next(x for x in (out / "overlaps.md").read_text().splitlines()
                if x.startswith("| consumer_confidence.PT.M"))
    assert "Portuguese institution" not in line
    assert "tie broken by row count (5 vs 4)" in line


# --- the real export, when present (slow) ------------------------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(not REAL_EXPORT.exists(), reason="legacy export not on this machine")
def test_real_export_proposal_and_import():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "registry"
        propose(REAL_EXPORT, out)
        specs = load_registry(out / "core.yaml")
        db = open_db(Path(d) / "legacy.db")
        try:
            rep = import_legacy(db, REAL_EXPORT, specs)
            total = rep.n_imported + sum(rep.n_quarantined_by_reason.values())
            assert total == 246162
            assert db.conn.execute("SELECT count(*) FROM served_observation").fetchone()[0] == 0
        finally:
            db.close()
