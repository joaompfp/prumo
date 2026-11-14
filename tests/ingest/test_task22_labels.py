"""Task 22 (final review C-I2): one geography code and one unit label per unit code, made safe.

The registry `unit` is a display label: Eurostat and World Bank adapters hand over no unit
(unit_raw None) and their verifiers expose none, so fetched rows and verification are label-blind.
The ONE place a label is compared with data is the legacy CSV import (validate(): legacy unit text
must equal spec.unit). LEGACY_UNIT_SPELLINGS keeps each relabelled series accepting its former
label there, so a DB populated under the old registry re-syncs and re-imports with no change.
"""
from pathlib import Path

from ingest.db import open_db
from ingest.legacy_import import LEGACY_UNIT_SPELLINGS, import_legacy
from ingest.registry import load_registry, sync_registry
from tests.ingest.legacy_csv import write_csv

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"

# geography relabelled by Task 22 (series id -> former geography); ids are NOT changed.
FORMER_GEOGRAPHY = {
    "eurostat.electricity_price_household.EU27": "EU27",
    "eurostat.electricity_price_household.GR": "GR",
    "eurostat.gdp_quarterly.EU27": "EU27",
    "eurostat.hicp.EU27": "EU27",
    "eurostat.ipi_manufacturing.EU27": "EU27",
    "eurostat.ipi_total.EU27": "EU27",
    "eurostat.STS_INPR_M_C29C30.EU27": "EU27",
    "eurostat.STS_INPR_M_C.EU27": "EU27",
    "eurostat.unemployment.EU27": "EU27",
}


def _specs():
    return load_registry(REGISTRY)


def _key(native_code):
    return dict(kv.split("=", 1) for kv in native_code.split(":", 1)[1].split(","))


def test_eurostat_geography_is_the_pinned_geo_code():
    bad = [(s.id, s.geography) for s in _specs()
           if s.source.name == "eurostat" and s.native_code
           and _key(s.native_code).get("geo", s.geography) != s.geography]
    assert not bad, bad


def test_one_unit_label_per_eurostat_unit_code_and_per_worldbank_indicator():
    labels: dict[tuple[str, str], set[str]] = {}
    for s in _specs():
        if not s.native_code:
            continue
        if s.source.name == "eurostat":
            k = _key(s.native_code)
            code = (k["unit"], k.get("currency", ""))
        elif s.source.name == "worldbank":
            code = (s.native_code.split(":")[0], "")
            if code[0] == "NY.GDP.PCAP.PP.CD":  # inactive unit-conflict labels kept as evidence
                continue                        # (test_registry_worldbank_units)
        else:
            continue
        labels.setdefault((s.source.name, *code), set()).add(s.unit)
    assert {k: v for k, v in labels.items() if len(v) > 1} == {}


def test_relabel_never_changes_a_series_id_or_its_indicator_key():
    specs = {s.id: s for s in _specs()}
    for sid, former in FORMER_GEOGRAPHY.items():
        assert sid in specs and sid.endswith("." + former)
        assert specs[sid].indicator_key.split(".")[-2] == former  # identity key untouched
    assert set(LEGACY_UNIT_SPELLINGS) <= set(specs)


def test_legacy_spellings_name_the_former_label_of_relabelled_series_only():
    specs = {s.id: s for s in _specs()}
    for sid, former in LEGACY_UNIT_SPELLINGS.items():
        assert former != specs[sid].unit, sid


def _old(specs):
    """The registry as it was before Task 22's relabel (former units and geographies)."""
    out = []
    for s in specs:
        upd = {}
        if s.id in LEGACY_UNIT_SPELLINGS:
            upd["unit"] = LEGACY_UNIT_SPELLINGS[s.id]
        if s.id in FORMER_GEOGRAPHY:
            upd["geography"] = FORMER_GEOGRAPHY[s.id]
        out.append(s.model_copy(update=upd))
    return out


_PERIOD = {"A": "2020", "S": "2020-S1", "Q": "2020-Q1", "M": "2020-01"}


def _legacy_rows(by_id):
    """Legacy CSV rows of relabelled series, in the legacy store's own (former) spellings,
    plus a row whose unit is wrong under both labels (must stay unit_mismatch)."""
    rows = []
    for sid, former in sorted(LEGACY_UNIT_SPELLINGS.items()):
        src, ind, region = sid.split(".", 2)
        rows.append(("Eurostat" if src == "eurostat" else "WorldBank", ind, region,
                     _PERIOD[by_id[sid].frequency], "1.5", former))
    rows.append(("WorldBank", "population", "GR", "2019", "7", "kg"))
    return rows


def test_db_built_with_old_registry_resyncs_and_reimports_unchanged(tmp_path):
    new = _specs()
    by_id = {s.id: s for s in new}
    legacy = _legacy_rows(by_id)
    csv_path = write_csv(tmp_path / "legacy.csv", legacy)
    db = open_db(tmp_path / "p.sqlite3")
    try:
        before = import_legacy(db, csv_path, _old(new))  # syncs the OLD registry first
        n_obs = db.conn.execute("SELECT count(*) FROM observation").fetchone()[0]
        n_q = db.conn.execute("SELECT count(*) FROM quarantine").fetchone()[0]

        sync_registry(db, new)
        rows = dict(((r[0], (r[1], r[2])) for r in db.conn.execute(
            "SELECT id, unit, geography FROM series")))
        for sid in set(LEGACY_UNIT_SPELLINGS) | set(FORMER_GEOGRAPHY):
            assert rows[sid] == (by_id[sid].unit, by_id[sid].geography), sid
        assert db.conn.execute(
            "SELECT count(*) FROM event WHERE kind = 'series_deactivated'").fetchone()[0] == 0
        assert db.conn.execute("SELECT count(*) FROM series WHERE active = 1").fetchone()[0] \
            == sum(s.active for s in new)

        again = import_legacy(db, csv_path, new)  # same CSV under the NEW labels
        assert again.n_imported == 0
        assert {k: v for k, v in again.n_quarantined_by_reason.items()
                if k != "not_in_registry"} == {}
        assert db.conn.execute("SELECT count(*) FROM observation").fetchone()[0] == n_obs
        assert db.conn.execute("SELECT count(*) FROM quarantine").fetchone()[0] == n_q
        assert before.n_imported == len(legacy) - 1
        assert before.n_quarantined_by_reason.get("unit_mismatch") == 1
    finally:
        db.close()


def test_fresh_import_under_new_registry_accepts_former_spellings(tmp_path):
    new = _specs()
    by_id = {s.id: s for s in new}
    legacy = _legacy_rows(by_id)
    db = open_db(tmp_path / "p.sqlite3")
    try:
        rep = import_legacy(db, write_csv(tmp_path / "l.csv", legacy), new)
        assert rep.n_imported == len(legacy) - 1
        assert rep.n_quarantined_by_reason.get("unit_mismatch") == 1
    finally:
        db.close()


def test_former_spelling_is_not_accepted_for_other_series(tmp_path):
    new = _specs()
    rows = [("WorldBank", "population", "PT", "2020", "10", "persons")]  # PT was always 'hab.'
    db = open_db(tmp_path / "p.sqlite3")
    try:
        rep = import_legacy(db, write_csv(tmp_path / "l.csv", rows), new)
        assert rep.n_imported == 0 and rep.n_quarantined_by_reason == {"unit_mismatch": 1}
    finally:
        db.close()


def test_former_label_table_is_exactly_the_reviewed_relabel():
    # 15 Eurostat (BAL x5, I10 x6, I15 x2, I21 x2) + 8 World Bank (/1000 x4, anos x2, hab. x2)
    # series; geography-only relabels need no legacy spelling (ids are unchanged).
    assert sum(s.startswith("eurostat.") for s in LEGACY_UNIT_SPELLINGS) == 15
    assert sum(s.startswith("worldbank.") for s in LEGACY_UNIT_SPELLINGS) == 8
