# Task 15 Part B - OECD verifier independent spec review

Date: 2026-11-12. Reviewer: independent spec-review subagent (read-only). Scope: verifier
commits 212cd17..5d27624 (ccaa0ed code+fixtures+tests, 5d27624 implementation report) on
pipeline-rebuild, /home/joao/projects/prumo-pipeline, against the full Task 15 brief
(docs/superpowers/handoff/reports/task-15-brief.md). NOT reviewed: source/Part-A files -
F1/F2/F3 are recorded in task-15-source-spec-review.md and are being fixed by the parallel
Part A task; they are not re-opened here. No code/registry/tests/handoff/ledger/vault edits,
no commits, no push; this report is the only authored file. Scratch probes live under
/home/joao/.hermes/cache/scratch (oecd_verifier_probes.py), mutations built from scratch in
the probes, never written to fixtures.

## Verdict: REQUEST_CHANGES

One Important gap (I1) against the controller's bounded-live-phase requirement; all other
mandatory points verified green with executed evidence. Part A source fixes stay with the
parallel source task and do not gate this verdict.

## Executed verification (real runs, this review)

- `.venv-ci/bin/python -m pytest tests/ingest/test_verifier_oecd.py tests/ingest/test_independence.py -q`
  -> 45 passed, 1 deselected (the live test) in 10.06s. No full suite, no live network.
- `.venv-ci/bin/ruff check` on the 3 new code/test files -> clean.
- Fixture provenance: sha256-rehashed all 6 tests/ingest/fixtures/oecd/verify/*.csv against
  (a) their own MANIFEST.json pins and (b) the discovery bodies
  docs/superpowers/handoff/evidence/task-15-oecd/discovery/{02,04,06,08,10,12}-*.body ->
  6/6 byte-identical, status 200 in the discovery manifest. The "sha256-pinned byte copies"
  claim in the Part B report is true; no fixture is presented as anything it is not. The
  windowed subsets the CsvFixtureHttp double serves are explicitly derived (row filter,
  oecd_verifier_fixtures.py:78-101, asserted in-test at test_verifier_oecd.py:153-164) and
  are never archived as "original" - combined-run samples span the full extent, so the 40
  archived envelopes carry the pinned original bytes (test_verifier_oecd.py:439-458).
  No invented archive provenance found.
- 17 from-scratch bypass probes against `read_csv_evidence` (scratch script): ALL fail closed
  as designed - dimension pair swap REF_AREA<->MEASURE (coordinate mismatch, P1), lowercase
  OBS_STATUS (P2), unit label trailing space (P3), periods '2026-1'/'2026-13'/'2026-00'/
  full-width digits (P5), values full-width digits/NaN/Infinity/'1,5' (P6), inverted window
  (P7), foreign series row (P9, clean ValueError STRUCTURE_ID drift), blank body (P10).

## Mandatory checklist (all verified unless flagged)

- Independent family + no helper sharing: csvfilewithlabels SDMX-CSV vs the collector's
  SDMX-JSON; ingest/verifiers/oecd.py imports only stdlib + allowlisted ingest.http/
  ingest.models/ingest.verifiers names; register_verifier static allowlist and closure check
  pass (test_verifier_oecd.py:340-348), assert_verifier_independent subprocess guard passes
  with collectors/ingest.flags/ingest.sources blocked (:351-356). Duplicated native-code
  shape rule (oecd.py:98-112) is the intended intentional duplication.
- Exact tokens, no conversion: OBS_VALUE preserved verbatim, ASCII-decimal regex
  (oecd.py:74,236-238); no floats/rounding anywhere; the CSV '-6.0'->'-6' trailing-zero
  difference is pinned by a dedicated test (:144-150) and absorbed by exact-Decimal engine
  policy. Probes P6 confirm NaN/Infinity/non-ASCII tokens rejected.
- Complete pinned 9-dimension identities: all 9 key code cells must equal the registry pins
  in header order (oecd.py:216-219), labels non-blank; BCICP/LI and REF_AREA mutations fail
  (suite) and full column-pair swap fails closed (probe P1). Column positions are never
  assumed - header-name parsing with duplicate/unknown/width fail-closed (oecd.py:121-159);
  unemp fixture's BASE_PER-before-OBS_STATUS layout (item 12) handled via the order-free
  remaining-pair loop (:148-158).
- Unit/multiplier/adjustment/status publisher-derived, never echoed: UNIT_MEASURE narrow map
  asserted AGAINST spec.unit (oecd.py:262-269), registry drift raises (test:265-272);
  UNIT_MULT must be '0'/'Units' with spec.multiplier 0 (:247-253); ADJUSTMENT AA/Y asserted
  vs spec.seasonal_adjustment (:270-277); FREQ vs spec.frequency (:278-282). OBS_STATUS: only
  'A'->'normal', every other code fails closed (:241-246) - documented codelist-404
  limitation stands.
- Unknown/malformed fail closed: non-2xx, HTML, blank, UTF-8, width, duplicates, out-of-window
  rows (oecd.py:203-233,322-323) - suite + probes green.
- Canonical periods: strict YYYY-MM regex on request window AND decoded rows
  (oecd.py:73,115-118,224-225); probes P5/P7 green.
- Missing period -> observed None, honest mismatch (oecd.py:330-335; test:167-172).
- Evidence envelope: oecd-csv-evidence v1 {url, status, body_b64} of the exact bytes parsed
  (oecd.py:287-295); url is the RequestsHttp FINAL url after redirects and status is the
  actual response status (ingest/http.py:63-66) - they pertain to the parsed response, not an
  arbitrary URL. Offline replay recovers value AND unit AND flag from the body alone via
  read_csv_evidence (test:324-335,439-458); raw store is content-addressed, store.load raises
  RawIntegrityError on any byte alteration (ingest/rawstore.py:39-45), so tampered evidence is
  detected at load, before replay. Structure/version/multiplier/flags are re-VALIDATED on
  replay, so all compared metadata is recoverable and enforced offline.
- Registration/scope: no allowlist change was needed (imports fit VERIFIER_INGEST_IMPORTS);
  frozen-range commits touch no registry/HANDOFF/ledger (verified via git diff --stat);
  truthful authorship kimi-k3-subagent; report file landed as its own commit 5d27624.
- Live test non-staleness: rolling collector window, per-series counts/ranges re-derived from
  THIS run's archived bytes re-parsed offline, verifier expectations re-read from archived CSV
  envelopes, served==0 under redistribution_ok=false (test:486-573). No frozen counts/dates.

## Findings

### I1 (Important, blocking): the live test's whole-phase bounds are post-hoc assertions, not executable enforcement

test_verifier_oecd.py:511-536 wraps RequestsHttp(throttle_rps=0.25, timeout=30.0, retries=0)
in a `_Counting` shim and asserts `http.n <= 18 and elapsed <= 150.0` ONLY AFTER
`run_with_refetch` returns (:536). During the run nothing is bounded:

- a request budget is never enforced - a regression that fans out requests (e.g. per-item
  instead of per-series, or a retrying client) burns 4s-paced requests indefinitely; the <=18
  assertion fires only after they all complete;
- the 150s "whole-phase deadline" never aborts anything - the test merely fails afterwards.
  Worst case with retries=0 is already ~12 requests x (4s pacing + 30s) ~= 408s, and
  RequestsHttp applies the 30s timeout PER REDIRECT HOP (ingest/http.py:63-71 loops up to
  MAX_REDIRECTS+1=6 hops, each with its own session.get(timeout)), so one logical request can
  take ~180s; the requests-library read timeout is also per socket read, so a trickling
  server is not bounded at all;
- `_Counting` does not even see redirect hops or retry attempts (it wraps the outer get), so
  the counted budget silently undercounts real wire traffic.

The controller requirement is a whole network phase that is bounded while it runs (per-request
timeout AND client retries AND max_attempts AND a real deadline/counter), not a per-request
30s plus a report afterwards. max_attempts=1 and retries=0 are correctly set (:511,515) and
run_with_refetch honours them (ingest/verify.py:283-288), but they bound attempts, not time.

Precise fix (test-local; the production verifier correctly keeps no timing policy per
contract): replace `_Counting` with a deadline/budget-enforcing wrapper that raises inside
get(), e.g.

    class _Bounded:
        def __init__(self, base, max_requests=18, deadline_s=150.0):
            self.base, self.n = base, 0
            self.max_requests = max_requests
            self.deadline = time.monotonic() + deadline_s
        def get(self, url, params=None, headers=None, timeout=None):
            if time.monotonic() > self.deadline:
                raise RuntimeError("live phase deadline exceeded")
            self.n += 1
            if self.n > self.max_requests:
                raise RuntimeError("live request budget exhausted")
            remaining = self.deadline - time.monotonic()
            return self.base.get(url, params=params, headers=headers,
                                 timeout=min(timeout or 30.0, max(1.0, remaining)))

used as `_Bounded(RequestsHttp(throttle_rps=0.25, retries=0))` (per-call timeout capped to
the remaining budget so one hanging request cannot overrun the deadline; the Http protocol
already supports per-call timeout, ingest/http.py:30-31,56-61). Keep the existing post-hoc
assertions as the acceptance signal. Residual to note in the fix test: redirect hops still
each get up to `remaining`, and socket-read trickle can exceed it; a stricter bound needs a
wall-clock wrapper around the whole run (e.g. pytest-timeout / signal alarm) - optional, the
wrapper above satisfies the counter+deadline requirement for realistic failure modes.

### Minor limitations (non-blocking, for the ledger)

- M1 Quoted numeric framing: csv.reader strips quotes, so an OBS_VALUE written as "99.6"
  (with literal quotes on the wire) is accepted as the token 99.6 (probe P4). The six
  originals are unquoted; exact-Decimal comparison cannot be bypassed this way, but the
  archived wire token and the compared token differ in framing. Note only.
- M2 STRUCTURE_ID accepts any version digits (oecd.py:186-187); agency+dataflow are pinned to
  the request, the version is not (probe P8 ACCEPTED). Consistent with the brief's
  "<agency>:<dataflow>(<version>) pinned to the request"; a version-only drift would pass here
  and is caught by value/unit comparison. Design note, not a gap.
- M3 Rolling-window math in the live test is off by one year when the runtime month is Jan or
  Feb (test_verifier_oecd.py:496-497: the else branch yields year-1/month+10, i.e. 2 months
  back instead of 14; correct is year-2/month+10; e.g. 2027-02 yields '2026-12' instead of
  '2025-12'). Latent post-2027-01; window stays bounded and valid, expectations are non-stale
  regardless. Fix together with I1 since both touch the live test.
- M4 `_Counting` misses redirect hops/retry attempts (folded into I1's fix rationale).
- M5 Dimension identity is pinned by code cells in header order, not dimension ids
  (column reordering fails closed, probe P1) - the documented intentional shape, parallel to
  source-side F3 handled by the Part A fix. Dimension labels other than the mapped
  unit/adjustment/freq/status ones are required non-blank but not content-pinned; identity
  rests on the code pins, which the brief's "meaningful labels where used" permits.

## Limits of this review

Live test not executed (deselected; controller's f0nix gate). OBS_STATUS codelist remains
unenumerated publisher-side (discovery item 13 404) - fail-closed stands. Probes are static
mutations of genuine fixtures; no adversarial live endpoint behaviour was exercised. Verifier
registration in the production CLI path is Task 17 scope, correctly absent here.
