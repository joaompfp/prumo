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
