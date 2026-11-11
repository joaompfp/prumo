# Task 10 scoped fix-round-1 review

Scope: cacfdf0..16ee533 on pipeline-rebuild. Reviewed independently after the implementation; this record closes the stale pre-fix checkpoint.

## Controller verification

Command: `.venv-ci/bin/python -m pytest tests/ingest -q`
Result: 660 passed, 2 live deselected, 96.69 s.

Command: `.venv-ci/bin/python -m pytest tests/ingest/test_live_ine.py -m live -s --basetemp=/home/joao/.hermes/cache/scratch/prumo-ine-live-current`
Result: 1 passed, 112.16 s; verified run 1, 1,399 written and served in the isolated test SQLite, 1 quarantined, 24/24 sampled comparisons matched. Included monthly provisional unemployment, manufacturing confidence, manufacturing IPI, CAE division 10 and annual births. This is not a production deployment.

## Independent specification review

Verdict: PASS. Fresh review agent (runtime model kimi-k3). Verified C1 independent HTML verifier and required tests, I2 fail-fast guards and machine marker, I3 scale quarantine, M2 sign vocabulary, M1 attribution and per-source timeouts. Independently reran the full offline suite (660 passed, 2 deselected) and real legacy import: 164,345 imported; 6,522 missing_unit, 6 non_numeric, 480 suspect_unit_scale; 74,809 not_in_registry; 0 served; idempotent. Re-fetched INE terms confirming CC BY 4.0. Owner decisions AB and duplicate IPI series unchanged.

## Independent quality review

Verdict: APPROVED. Fresh review agent (runtime model kimi-k3). No Critical or Important findings. Targeted suite: 390 passed. Concrete probes rejected wrong-period selection echoes, duplicate matching table cells, period-label/order disagreement and unit-symbol mismatch; reviewed sign/token and timeout handling. Independence tests pass.

Deferred minors: permanent regression tests for echoed XML period selection mismatch and duplicate matching grid rows; CLASS Id/tag-name coupling and hardcoded CLASS_periodo remain fail-closed template assumptions. No implementation fix round required.

## Completion boundary

Task 10 is complete in the working branch through 16ee533. The deployed f0nix app remains the maintenance page; ingest deployment belongs to Task 18. Task 11 is the next implementation gate.
