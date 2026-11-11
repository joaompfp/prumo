"""Legacy CSV import (Task 8, Rulings E/U).

Fixtures are tiny CSVs written to tmp_path in the legacy export's exact header."""
from ingest.legacy_import import import_legacy, legacy_series_id
from ingest.models import SeriesSpec, SourceSpec
from tests.ingest.legacy_csv import write_csv

SRC = SourceSpec(name="ine", licence="L", licence_url="https://x/l", attribution="INE",
                 redistribution_ok=True)


def ine_spec(indicator="ipi_yoy_cae", unit="%", frequency="M"):
    return SeriesSpec(id=legacy_series_id("INE", indicator, "PT"), source=SRC,
                      indicator_key=f"{indicator}.PT.{frequency}", role="primary",
                      theme="economy", geography="PT", frequency=frequency, unit=unit)


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


# --- legacy_import -----------------------------------------------------------------------------

def test_null_value_and_unit_quarantined(db, tmp_path):
    rows = [("INE", "ipi_yoy_cae", "PT", "2025-01", "1.5", "%"),
            ("INE", "ipi_yoy_cae", "PT", "2025-02", "", "%"),          # null value
            ("INE", "ipi_yoy_cae", "PT", "2025-03", "2.5", ""),        # null unit: registry unit
            ("INE", "ipi_yoy_cae", "PT", "2025-04", "3.5", "EUR"),     # differs from registry
            ("INE", "ipi_yoy_cae", "PT", "2025-05", "4.4e-05", "%"),   # DOUBLE text, not a token
            ("INE", "not_core", "PT", "2025-01", "9", "%")]
    # a long run of null values in one series must not abort the import
    rows += [("INE", "ipi_yoy_cae", "PT", f"{1990 + i // 12}-{i % 12 + 1:02d}", "", "")
             for i in range(60)]
    rep = import_legacy(db, write_csv(tmp_path / "l.csv", rows), [ine_spec()])
    assert rep.n_imported == 2
    assert rep.n_quarantined_by_reason == {"non_numeric": 62, "unit_mismatch": 1,
                                           "not_in_registry": 1}
    sid = legacy_series_id("INE", "ipi_yoy_cae", "PT")
    assert sorted(q(db, "SELECT period, value_text FROM observation")) == [
        ("2025-01", "1.5"), ("2025-03", "2.5")]
    quarantined = q(db, "SELECT series_id, raw_period, raw_value, reason FROM quarantine "
                        "WHERE raw_period LIKE '2025%' ORDER BY raw_period")
    assert quarantined == [(sid, "2025-02", "", "non_numeric"), (sid, "2025-04", "3.5", "unit_mismatch"),
                           (sid, "2025-05", "4.4e-05", "non_numeric")]
    assert q(db, "SELECT count(*) FROM quarantine")[0][0] == 63  # not_in_registry is not quarantined


def test_ine_free_text_period_normalized_or_quarantined(db, tmp_path):
    rows = [("INE", "ipi_yoy_cae", "PT", "Setembro de 2025", "0.5", "%"),
            ("INE", "ipi_yoy_cae", "PT", "Março de 2024", "0.7", "%"),
            ("INE", "ipi_yoy_cae", "PT", "3.º Trimestre de 2025", "0.9", "%"),
            ("INE", "ipi_yoy_cae", "PT", "2022-00", "1.1", "%")]
    rep = import_legacy(db, write_csv(tmp_path / "l.csv", rows), [ine_spec()])
    assert rep.n_imported == 2
    assert rep.n_quarantined_by_reason == {"bad_period": 2}
    assert sorted(q(db, "SELECT period, value_text FROM observation")) == [
        ("2024-03", "0.7"), ("2025-09", "0.5")]
    assert sorted(r[0] for r in q(db, "SELECT raw_period FROM quarantine")) == [
        "2022-00", "3.º Trimestre de 2025"]


def test_legacy_rows_not_in_served_view(db, tmp_path):
    rows = [("INE", "ipi_yoy_cae", "PT", "2025-01", "6770.10", "%", "2026-02-26T03:02:13.663810"),
            ("INE", "ipi_yoy_cae", "PT", "2025-02", "1.5", "%", "2026-03-15T21:35:31Z")]
    import_legacy(db, write_csv(tmp_path / "l.csv", rows), [ine_spec()])
    assert q(db, "SELECT count(*) FROM served_observation") == [(0,)]
    obs = q(db, "SELECT o.period, o.value_text, o.kind, o.raw_fetch_id, o.fetched_at, r.state, "
                "r.dataset_key, s.name FROM observation o JOIN dataset_run r ON r.id = o.dataset_run_id "
                "JOIN source s ON s.id = r.source_id ORDER BY o.period")
    assert obs == [
        ("2025-01", "6770.10", "legacy-unverified", None, "2026-02-26T03:02:13.663810Z", "verified",
         "legacy:ine", "ine"),
        ("2025-02", "1.5", "legacy-unverified", None, "2026-03-15T21:35:31Z", "verified",
         "legacy:ine", "ine")]
    assert q(db, "SELECT value FROM setting WHERE key = 'legacy_served'") == [("0",)]
    # the run is verified, so only the setting keeps them out of the served view
    db.conn.execute("UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
    assert q(db, "SELECT count(*) FROM served_observation") == [(2,)]


def test_import_is_idempotent(db, tmp_path):
    rows = [("INE", "ipi_yoy_cae", "PT", "2025-01", "1.5", "%"),
            ("INE", "ipi_yoy_cae", "PT", "2025-02", "", "%"),
            ("INE", "other", "PT", "2025-01", "1", "%")]
    path = write_csv(tmp_path / "l.csv", rows)
    first = import_legacy(db, path, [ine_spec()])
    counts = [q(db, f"SELECT count(*) FROM {t}")[0][0]
              for t in ("observation", "quarantine", "dataset_run")]
    second = import_legacy(db, path, [ine_spec()])
    assert [q(db, f"SELECT count(*) FROM {t}")[0][0]
            for t in ("observation", "quarantine", "dataset_run")] == counts == [1, 1, 1]
    assert (first.n_imported, second.n_imported) == (1, 0)
    assert first.n_quarantined_by_reason == {"non_numeric": 1, "not_in_registry": 1}
    assert second.n_quarantined_by_reason == {"not_in_registry": 1}


def test_same_period_from_two_fetches_kept_as_vintages(db, tmp_path):
    """Region aliases ('Portugal' -> 'PT') can map two legacy rows to one (series, period):
    both are kept, the later fetch gets the higher id (= latest vintage)."""
    rows = [("INE", "ipi_yoy_cae", "Portugal", "2025-01", "1.6", "%", "2026-04-06T01:47:04Z"),
            ("INE", "ipi_yoy_cae", "PT", "2025-01", "1.5", "%", "2026-02-26T03:02:13.663810")]
    import_legacy(db, write_csv(tmp_path / "l.csv", rows), [ine_spec()])
    assert q(db, "SELECT value_text FROM observation ORDER BY id") == [("1.5",), ("1.6",)]
