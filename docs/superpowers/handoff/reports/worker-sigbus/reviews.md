# Worker SIGBUS hardening: independent review gates

## Specification review

Initial candidate `4fd8508` failed the gate. The reviewer reproduced sidecar recreation in a writable directory, symlink-based stale reads and sidecar writes after the old forced plain retry. Checking whether the shm pathname exists before choosing `readonly_shm` was a TOCTOU (time-of-check/time-of-use) bug, not a valid safety guarantee. A missing pathname does not establish that no mapping exists.

The corrected candidate `fe13837` passed scoped specification re-review. Canonical database targets now govern sidecar checks and URI construction. `readonly_shm=1` is unconditional. Missing shared memory is a refusal, never reader recovery. Immutable reads are repeated only with evidence of a writer, their mode is re-evaluated, and every repeated immutable result is validated. A second race fails closed. The reviewer ran 20 affected tests and independently reproduced a missing-shm refusal without any file mutation.

## Code quality

An independent quality reviewer approved `fe13837`. Its probes compared old-style stale-WAL reads, which rewrote the shared-memory index, against the accepted reader, which returned the same committed rows without changing any sidecar bytes. It also exercised canonical symlink access and repeated writer races. Four independently selected tests passed.

Non-blocking diagnostic limitation: a refusal on the second open is labelled changed-during-read even if a schema mismatch became visible during the first writer race. It remains fail-closed and the next fresh call reports the specific refusal.

## Evidentiary boundary

The safety regressions are deterministic file-effect tests, not a claim that the historical live DMS (dead-man-switch) lock loss was observed. The SIGBUS race probe deliberately removes a lock to demonstrate a mechanism. Both reviewers retained that limitation. Neither reviewer accessed production or approved closing the operational root-cause/elapsed-observation gate.

The controller separately runs whole-suite, committed-checkout and installed checks. Review approvals do not substitute for those results.

## Final integration review for the installed phase B base

A fresh read-only reviewer approved the integration with main `4719f55`, now runtime `3ab1fdc`. It confirmed that the accepted persistence implementation/tests match `fe13837` exactly and that no phase B file in app/backoffice/static/presentation was lost. Its independent probes observed the baseline reader rewrite a copied shm, the accepted reader leave bytes unchanged, an actual read-only shm descriptor without truncation, stable transactions and fail-closed missing-sidecar behavior. Its focused tests were review evidence only; authoritative release gates remain the controller's 71 clean-commit tests and exact-main CI 3,206, followed by installed checks in [installed.md](installed.md).

The review retained the existing non-blocking fail-closed diagnostic limitation on a writer that checkpoints/exits during an immutable schema read. It did not assert the live historical trigger was captured or close the 24-hour gate.
