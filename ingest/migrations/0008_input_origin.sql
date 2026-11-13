-- Migration 0008 (Task 17B): input origin of every dataset run.
--
-- Runs must honestly distinguish fresh network input from an exact recorded bundle replay
-- (validated original files with their own receipt timestamps) and from the legacy synthetic
-- import runs. The run clock (started_at) always stays the ACTUAL attempt time; a recorded
-- run never pretends to have happened at the bundle's fetch date, and legacy runs are marked
-- 'legacy' explicitly instead of being indistinguishable from live imports.
ALTER TABLE dataset_run ADD COLUMN input_origin TEXT NOT NULL DEFAULT 'live'
  CHECK (input_origin IN ('live', 'recorded', 'legacy'));
UPDATE dataset_run SET input_origin = 'legacy' WHERE dataset_key LIKE 'legacy:%';
