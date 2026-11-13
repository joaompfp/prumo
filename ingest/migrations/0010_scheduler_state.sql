-- Scheduler-owned attempt history, separate from dataset_run. In particular, a synthetic
-- legacy 'verified' run must never postpone a fresh fetch. No existing data/view is changed.
-- Keys may outlive registry membership; source/group are audit labels, not foreign keys.
CREATE TABLE scheduler_state(
  dataset_key TEXT PRIMARY KEY NOT NULL,
  source_name TEXT NOT NULL,
  group_label TEXT NOT NULL,
  last_attempt_at TEXT NOT NULL,
  last_attempt_state TEXT NOT NULL,
  last_success_at TEXT,
  failure_streak INTEGER NOT NULL DEFAULT 0 CHECK (failure_streak >= 0),
  last_finished_at TEXT
) STRICT;
