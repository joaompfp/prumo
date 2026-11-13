# Task 11 - Banco de Portugal adapter and independent verifier

## Scope and current boundary

Repository /home/joao/projects/prumo-pipeline, branch pipeline-rebuild, implementation baseline 16ee533. Controller owns shared HANDOFF.md and progress-ledger.md. Task 10 is complete: independent spec PASS and quality APPROVED, controller suite 660 passed / 2 live deselected, real INE smoke verified 1,399 observations and 24/24 sample matches. Public app remains maintenance-only; no deploy or main merge.

Build ingest/sources/bportugal.py and ingest/verifiers/bportugal.py, recorded fixtures, source/verifier/unit-registry tests, a deselected-by-default live test and reports/task-11-report.md. Extend registry/core.yaml with the missing source and unambiguously mapped base series. Do not regenerate the registry or alter unrelated ids, units or primary roles.

There are NO Banco de Portugal series/source in current core.yaml. All 3,471 BPORTUGAL legacy CSV rows have empty units. Task 11 must derive units, multiplier, frequency, geography and definitions from current BPstat metadata, NOT fill units into legacy rows. Legacy blank-unit rows remain quarantined under Ruling V. The CSV is /home/joao/projects/_legacy_export/indicators.csv.

Legacy collector collectors/bportugal.py has these candidate publisher series (verify all identifiers and metadata live):

| Legacy indicator | BPstat series id | Domain | Dataset |
|---|---|---|---|
| euribor_1m | 13168439 | 22 | 2829cb9155cb4f6ba6906db6b204c4bc |
| euribor_3m | 13168436 | 22 | 2829cb9155cb4f6ba6906db6b204c4bc |
| euribor_6m | 13168438 | 22 | 2829cb9155cb4f6ba6906db6b204c4bc |
| euribor_12m | 13168437 | 22 | 2829cb9155cb4f6ba6906db6b204c4bc |
| eur_usd | 12531993 | 29 | 23e0cdd56bddb4ad3016a9c3ad63a539 |
| pt_10y | 12099464 | 26 | 690b7b36fd36c0dbe249c48cbbc39524 |
| de_10y | 12560098 | 26 | 690b7b36fd36c0dbe249c48cbbc39524 |
| credit_housing | 12557378 | 19 | 28b6a921e1a4a9e326e724ab3e043d97 |
| credit_consumer | 12557382 | 19 | 28b6a921e1a4a9e326e724ab3e043d97 |
| deposits | 12556700 | 19 | d5bf6198a39f1e77b0d14dda97103de0 |

Exclude spread_pt_de: the legacy collector calculates it by subtraction, and derived data is explicitly out of scope. Legacy region PT was a collector default, not evidence that German yields or Euribor measure Portugal. Use publisher metadata to choose correct geography and document corrections.

## Publisher interface discovery

Authoritative API documentation: https://bpstat.bportugal.pt/data/docs . Series metadata endpoint is /data/v1/series/?lang=EN&series_ids=<id,...> (NOT /series/<id>/). Observations endpoint is /data/v1/domains/<domain>/datasets/<dataset>/?lang=EN&series_ids=<ids>. API is public, no key. It returns JSON-stat 2.0. Respect X-Throttle and HTTP429; pace at most 1 req/s, timeout network probes explicitly, no unbounded downloads.

Confirm a genuinely different publisher channel or format for verification (CSV/download/portal vs JSON-stat collector). Do not call the same JSON endpoint with a cosmetic parameter an independent channel, do not invent CSV support. Record the actual discovery and evidence. If a channel is difficult, inspect documented exports and portal network code before claiming none (INE's initial false no-channel claim was a missed Referer header). If truly unavailable, report the evidence and leave unserved with machine verifiable:false; do not pretend verified. Research licence/attribution from publisher terms: unverified redistribution remains false and is reported.

## Acceptance criteria

Source implements current Source contract: fetch is iterable RawResponse, every actual request preserved verbatim; parse returns dict of series id to RawRow list with correct response_index. Never import a legacy collector at runtime, do DB work or write files. JSON numeric tokens stay strings via parse_float=str and parse_int=str; no float round trip or rounding. Registry declares decimal. Keep unit scaling as publisher metadata rather than multiply values. Explicit status flags normal/provisional/estimated/revised/break; unknown real status codes raise. Confidential/missing cells yield None, quarantine non_numeric. Decode declared dimension extents/order and sparse arrays correctly; reject truncated/double-mapped payloads, duplicate period labels, HTML/error JSON bodies, wrong series/unit/frequency.

Verifier independently extracts actual value, period, unit and status where exposed, never echoes expected values or copies spec.unit as evidence. Required ItemResult series_id/period, evidence_url, raw evidence bytes; observed_decimal declared. Duplicate tiny mapping/native-code helpers intentionally instead of sharing source/flags modules. Pass register_verifier static allowlist and assert_verifier_independent subprocess guard (check ingest/verifiers/__init__.py). Prefer no shared-framework edits; any necessary change must be additive, justified and separately tested.

Tests-first, with actual RED then GREEN evidence. Required tests: parse_fixture_yields_expected_rows with at least five named observations exact token/period/unit/flag checked against the publisher; parse_html_error_page_raises; parse_preserves_status_flags; verifier_detects_tampered_value; verifier_registers_and_passes_allowlist; subprocess_independence; clean end-to-end run -> verified and served; active native code uniqueness/completeness; registry unit/native-unit table covering every active series. Fixtures must be REAL responses, <=200KB each with provenance, and named cells cross-checked through a third publisher channel when available (document if not available; never invent). A @pytest.mark.live test is deselected by default.

Live fetch+parse ALL active BPstat series, not a cherry-picked subset. Report empty series, failures, observed flag vocabulary and quarantines. Run a full verified smoke using the independent channel. Verify public API access/rate-limit behaviour from f0nix (ssh f0nix) without deploying; use existing aliases for any infrastructure actions, but no infrastructure changes are part of this task. Task17 CLI does not exist yet: exercise run_with_refetch directly instead of claiming CLI smoke.

## Environment and engineering rules

Tests: /home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -q. No DuckDB (illegal instruction on f3nix). All SQL stays ingest/db.py. SourceSpec now supports timeout_s and verifiable; INE pattern omits timeout kwarg when absent to retain old Http doubles. Match existing architecture, refactor boundaries first if needed, avoid speculative abstractions. Scratch and temporary downloads only /home/joao/.hermes/cache/scratch, never system /tmp.

Load relevant implementation/testing/gitnexus skills and repository AGENTS.md. GitNexus exact worktree alias prumo-pipeline has been refreshed at 16ee533; use gitnexus query/context/impact before modifying existing symbols and detect-changes before commits. New adapter files have no existing upstream callers. Check graph caveats: tests/ingest/test_verify.py parser warning means tests remain authoritative. For HIGH or CRITICAL shared impact, stop and report to controller before changing behaviour.

Implementer owns code, registry changes, fixtures, tests and reports/task-11-report.md only. Do not change shared HANDOFF.md or progress-ledger.md, AGENTS.md, other source reports or unrelated code. Commit scoped verified increments, truthful authorship only (old Claude-specific coauthor/session trailers do not describe this runtime). Do not push, merge, open PR, deploy or send communications. Report actual commit hashes and commands. Keep a useful checkpoint report as network discovery and coding progress; controller then applies independent spec and quality review gates. Never mark your own task complete in shared tracked work.
