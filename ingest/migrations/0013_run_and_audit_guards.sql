-- Migration 0013 (Task 24, re-review fixes: re-review 1 M-2, M-5; re-review 2 I1).
--
-- 1. A withdrawn run id cannot be resurrected by INSERT OR REPLACE (re-review 1 M-2). REPLACE
--    deletes the conflicting row without firing DELETE/UPDATE triggers and the foreign-key
--    check passes because the id reappears, so `dataset_run_withdrawn_ins` now also refuses an
--    insert whose id belongs to a withdrawn row. A BEFORE INSERT trigger runs before REPLACE
--    removes the old row, so it still sees it.
-- 2. Fetched observation rows carry exactly the UTC spelling ingest.pipeline writes
--    (datetime.isoformat() of an aware UTC time): 'YYYY-MM-DDTHH:MM:SS+00:00' or
--    'YYYY-MM-DDTHH:MM:SS.ffffff+00:00' (re-review 1 M-5). The served view (0011) compares
--    fetched_at as text, which is chronological only within that spelling. Legacy rows
--    ('legacy-unverified', mixed 'Z'/fractional spellings from the old export) are exempt.
--    Only new inserts/updates are checked; no existing row is touched. All 263,429 fetched
--    rows of the 2026-11-14 production copy already use the 32-char '+00:00' form.
-- 3. verification_item.reason accepts 'previously-failed' (re-review 2 I1): a cell that
--    mismatched in an earlier failed verification of the same dataset (since its last
--    verified run) is forced into the next attempt's sample, so a deterministic defect fails
--    every attempt instead of passing on a lucky redraw. The CHECK cannot be altered in place,
--    so the table is rebuilt (create-new / copy / drop / rename) with identical columns and
--    rows, like 0009/0011; nothing references verification_item and it has no index.
DROP TRIGGER dataset_run_withdrawn_ins;
CREATE TRIGGER dataset_run_withdrawn_ins BEFORE INSERT ON dataset_run
WHEN NEW.state = 'withdrawn'
  OR EXISTS (SELECT 1 FROM dataset_run d WHERE d.id = NEW.id AND d.state = 'withdrawn')
BEGIN
  SELECT RAISE(ABORT, 'a run is withdrawn only through Db.withdraw_run, and a withdrawn run is never replaced');
END;

CREATE TRIGGER observation_fetched_at_ins BEFORE INSERT ON observation
WHEN NEW.kind = 'fetched' AND NOT (
     (length(NEW.fetched_at) = 25 AND NEW.fetched_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]+00:00')
  OR (length(NEW.fetched_at) = 32 AND NEW.fetched_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00'))
BEGIN
  SELECT RAISE(ABORT, 'fetched observation.fetched_at must be UTC ISO-8601 ending +00:00');
END;

CREATE TRIGGER observation_fetched_at_upd BEFORE UPDATE OF kind, fetched_at ON observation
WHEN NEW.kind = 'fetched' AND NOT (
     (length(NEW.fetched_at) = 25 AND NEW.fetched_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]+00:00')
  OR (length(NEW.fetched_at) = 32 AND NEW.fetched_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00'))
BEGIN
  SELECT RAISE(ABORT, 'fetched observation.fetched_at must be UTC ISO-8601 ending +00:00');
END;

CREATE TABLE verification_item_0013(
  id INTEGER PRIMARY KEY,
  verification_id INTEGER NOT NULL REFERENCES verification(id),
  series_id TEXT NOT NULL REFERENCES series(id),
  period TEXT NOT NULL,
  expected_text TEXT,
  observed_text TEXT,
  evidence_url TEXT,
  match INTEGER NOT NULL CHECK (match IN (0,1)),
  observed_decimal TEXT CHECK (observed_decimal IN ('.', ',')),
  observed_unit TEXT,
  observed_flag TEXT,
  note TEXT,
  expected_decimal TEXT CHECK (expected_decimal IN ('.', ',')),
  expected_unit TEXT,
  expected_flag TEXT,
  observed_series_id TEXT,
  observed_period TEXT,
  evidence_sha256 TEXT,
  reason TEXT CHECK (reason IN ('latest', 'previously-failed', 'changed', 'series-stratum',
                                'random', 'same-response')),
  compared TEXT,
  unit_not_compared TEXT,
  flag_not_compared TEXT
) STRICT;
INSERT INTO verification_item_0013 SELECT id, verification_id, series_id, period,
  expected_text, observed_text, evidence_url, match, observed_decimal, observed_unit,
  observed_flag, note, expected_decimal, expected_unit, expected_flag, observed_series_id,
  observed_period, evidence_sha256, reason, compared, unit_not_compared, flag_not_compared
  FROM verification_item;
DROP TABLE verification_item;
ALTER TABLE verification_item_0013 RENAME TO verification_item;
