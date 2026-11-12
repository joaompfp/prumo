-- Migration 0009 (Task 17 review fix R1): honest terminal state for stale recorded replays.
--
-- The continuity guard (ingest.pipeline.run_dataset, recorded input only) refuses, INSIDE
-- the observation write transaction, a recorded run whose original collector receipts are
-- OLDER than the verified fetched data already held per series: inserting those rows would
-- let the served view's last-inserted tie-break silently replace NEWER verified data with
-- old recorded ones. The refused run ends in the NEW terminal state 'blocked-stale' (never
-- 'failed-validation': nothing failed HTTP or format validation - the input was deliberately
-- refused as outdated), its raw_fetch evidence rows stay on record for audit, and the held
-- verified rows stay byte-identical. No existing row changes state; the served view and the
-- legacy gate are recreated VERBATIM from 0007_scoped_legacy_serving.sql.
--
-- dataset_run.state's CHECK cannot be altered in place, so the table is rebuilt
-- (create-new / copy / drop / rename), exactly like 0006 rebuilt series. That is only sound
-- with foreign_keys OFF at statement time: with FK ON, SQLite would fail the DROP on the
-- immediate child references (observation/raw_fetch/quarantine/verification/event) and
-- silently rewrite child REFERENCES clauses during RENAME. `_migrate` (ingest/db.py) applies
-- every migration inside ONE transaction with foreign_keys temporarily OFF and verifies
-- PRAGMA foreign_key_check INSIDE the transaction before COMMIT.
DROP VIEW served_observation;
CREATE TABLE dataset_run_blocked_stale(
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source(id),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  state TEXT NOT NULL CHECK (state IN ('running','fetched','failed-fetch','failed-validation',
    'pending-verification','verified','failed-verification','blocked-stale')),
  dataset_key TEXT,
  input_origin TEXT NOT NULL DEFAULT 'live'
    CHECK (input_origin IN ('live','recorded','legacy'))
) STRICT;
INSERT INTO dataset_run_blocked_stale
  SELECT id, source_id, started_at, finished_at, state, dataset_key, input_origin
  FROM dataset_run;
DROP TABLE dataset_run;
ALTER TABLE dataset_run_blocked_stale RENAME TO dataset_run;
CREATE INDEX dataset_run_key ON dataset_run(dataset_key, id);

-- The refusal is recorded honestly as event kind 'stale_refusal': extend event.kind's CHECK
-- (no existing event row is rewritten; the audit trail is additive only).
CREATE TABLE event_stale_refusal(
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  dataset_run_id INTEGER REFERENCES dataset_run(id),
  kind TEXT NOT NULL CHECK (kind IN ('fetch_failure','format_change','revision',
    'cross_check_gap','verification_failure','refetch','stale_refusal')),
  detail_json TEXT
) STRICT;
INSERT INTO event_stale_refusal SELECT id, ts, dataset_run_id, kind, detail_json FROM event;
DROP TABLE event;
ALTER TABLE event_stale_refusal RENAME TO event;

-- Recreated verbatim from 0007_scoped_legacy_serving.sql (scoped legacy gate included).
CREATE VIEW served_observation AS
WITH eligible AS (
  SELECT o.* FROM observation o
  JOIN dataset_run r ON r.id = o.dataset_run_id AND r.state = 'verified'
  JOIN series s ON s.id = o.series_id
  JOIN source p ON p.id = s.source_id AND p.redistribution_ok = 1
  WHERE o.kind = 'fetched'
     OR (SELECT value FROM setting WHERE key = 'legacy_served') = '1'
     OR (o.kind = 'legacy-unverified' AND s.active = 1
         AND (SELECT value FROM setting
              WHERE key = 'legacy_served_source:' || p.name) = '1')
)
SELECT e.* FROM eligible e
WHERE NOT EXISTS (
  SELECT 1 FROM eligible n
  WHERE n.series_id = e.series_id AND n.period = e.period
    AND ((e.kind = 'legacy-unverified' AND n.kind = 'fetched')
         OR (n.kind = e.kind AND n.id > e.id)));
