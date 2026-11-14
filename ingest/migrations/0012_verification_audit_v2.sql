-- Migration 0012 (Task 21, final-review fixes B-I1..B-I4, B-M1, B-M3).
--
-- 1. verification: how the sample was drawn and what the verifier read.
--    sample_procedure  'prumo-sample-v2' (ingest/sampling.py); rows verified before this
--                      migration used Python's random.Random(seed).sample with a fixed target
--                      of 50 and are labelled 'v1-python-random-sample'.
--    sample_design     JSON summary of the draw (policy, population, counts per reason, cap).
--    input_origin      the verified run's input ('live' | 'recorded'), copied at verification.
--    verifier_channel  'live' = the verifier read the publisher over live HTTP;
--                      'pinned-bundle' = it read operator-captured bundle responses
--                      (NOT audit-grade: only behind the explicit CLI flag). Every recorded
--                      run verified before this migration read the same bundle as its
--                      collector, so it is backfilled as 'pinned-bundle'.
-- 2. verification_item: why the item was drawn (reason) and which fields were compared
--    (compared, comma list), with the verifier's recorded reason when unit or flag were not
--    compared. NULL on rows from before this migration (not recorded then).
-- 3. verification_spec: the exact registry spec each verified series was handed to the
--    verifier with, so replay_item can re-read archived evidence without the registry.
-- 4. event kinds: 'new_periods' (periods a run added to a series that already had verified
--    fetched data; with 'revision' this is the run's changed set), 'verifier_outage' (the
--    verifier channel was unavailable: no dataset re-download) and 'verification_escalated'
--    (the bounded verification loop gave up). event is rebuilt like 0011; the withdrawal
--    trigger that reads event is dropped first and recreated unchanged.
ALTER TABLE verification ADD COLUMN sample_procedure TEXT;
ALTER TABLE verification ADD COLUMN sample_design TEXT;
ALTER TABLE verification ADD COLUMN input_origin TEXT
  CHECK (input_origin IN ('live', 'recorded'));
ALTER TABLE verification ADD COLUMN verifier_channel TEXT
  CHECK (verifier_channel IN ('live', 'pinned-bundle'));
UPDATE verification SET
  sample_procedure = 'v1-python-random-sample',
  input_origin = (SELECT r.input_origin FROM dataset_run r WHERE r.id = dataset_run_id),
  verifier_channel = CASE (SELECT r.input_origin FROM dataset_run r WHERE r.id = dataset_run_id)
                       WHEN 'recorded' THEN 'pinned-bundle' ELSE 'live' END;

ALTER TABLE verification_item ADD COLUMN reason TEXT
  CHECK (reason IN ('latest', 'changed', 'series-stratum', 'random', 'same-response'));
ALTER TABLE verification_item ADD COLUMN compared TEXT;
ALTER TABLE verification_item ADD COLUMN unit_not_compared TEXT;
ALTER TABLE verification_item ADD COLUMN flag_not_compared TEXT;

CREATE TABLE verification_spec(
  verification_id INTEGER NOT NULL REFERENCES verification(id),
  series_id TEXT NOT NULL REFERENCES series(id),
  spec_json TEXT NOT NULL,
  PRIMARY KEY (verification_id, series_id)
) STRICT;

DROP TRIGGER dataset_run_withdraw_reviewed;
CREATE TABLE event_0012(
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  dataset_run_id INTEGER REFERENCES dataset_run(id),
  kind TEXT NOT NULL CHECK (kind IN ('fetch_failure','format_change','revision',
    'cross_check_gap','verification_failure','refetch','stale_refusal',
    'operational_failure','withdrawal','series_deactivated','new_periods',
    'verifier_outage','verification_escalated')),
  detail_json TEXT
) STRICT;
INSERT INTO event_0012 SELECT id, ts, dataset_run_id, kind, detail_json FROM event;
DROP TABLE event;
ALTER TABLE event_0012 RENAME TO event;
CREATE TRIGGER dataset_run_withdraw_reviewed BEFORE UPDATE OF state ON dataset_run
WHEN NEW.state = 'withdrawn' AND OLD.state <> 'withdrawn'
  AND (OLD.state <> 'verified' OR OLD.input_origin = 'legacy'
       OR NOT EXISTS (SELECT 1 FROM event e
                      WHERE e.dataset_run_id = NEW.id AND e.kind = 'withdrawal'))
BEGIN
  SELECT RAISE(ABORT, 'withdraw only a verified non-legacy run through Db.withdraw_run');
END;
