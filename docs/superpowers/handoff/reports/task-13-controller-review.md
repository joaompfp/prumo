# Task 13 - controller verification and blocked live gate

Worktree /home/joao/projects/prumo-pipeline, branch pipeline-rebuild, implementation dcec55d..27bec72. Independent specification PASS_CODE / LIVE BLOCKED and quality APPROVED_IMPLEMENTATION / LIVE BLOCKED: task-13-spec-review.md and task-13-quality-review.md. No Critical or Important implementation findings. Task13 is NOT COMPLETE. Do not treat a healthy-channel subset as all-source acceptance.

## Controller execution

Full `.venv-ci/bin/python -m pytest tests -q`: 909 passed,5 live deselected,1 warning in159.58s. Ruff on all9 touched Python source/test/helper files: All checks passed. Full source scope982 annual series/54geographies;930 active across18 indicators;52 PPP2017-unit conflicts inactive, no unit/id/role changes. The source and verifier are not deployed.

Controller independently read exact scratch SQLite targets, not only child summaries:

Full all-active run: state failed-verification,45915 observations,930 populated series,15465 non_numeric publisher-null quarantines,930-item failed verification,served0. Healthy-channel subset: state verified,25853 observations,516 populated series,8203 non_numeric null quarantines,516-item passing verification,served25853. Every one of the516 archived evidence envelopes was reloaded and hash-checked against raw-store content, exact ZIP bytes/finalURL/actual successful status recovered. These are isolated test DBs, not production data. The subset is a diagnostic result, not a narrowed registry or completed Task13.

Fresh bounded controller reproduction used real WorldBankSource, registered WorldBankVerifier, run_with_refetch and all930 current active specs; RequestsHttp(throttle_rps=1.0,timeout=12.0,retries=0),max_attempts=1,size=50. Actual output:

active_series930,indicator_codes18,state failed-verification,run_id1,written45915,quarantined15465,populated_series930,served0,raw_responses18,verification[[930,0]],quarantine_by_reason[[non_numeric,15465]]. The verifier raised a ReadTimeout from api.worldbank.org at12s; the existing engine marked the sample failed and withheld the whole run. No result fabricated, no timeout treated as proof of incorrect values. Full earlier committed live pytest also failed after its normal refetch attempts, as documented by implementer.

## Bounded endpoint probes

Same controller client with polite UA,starts at least1.1s apart,connect timeout5s/read12s:

https://api.worldbank.org/v2/en/indicator/NY.GDP.MKTP.CD?downloadformat=csv -> HTTP200,application/zip,142909bytes,sha25648296011514a05e3183f165b7a20b5c265fd7d7ab67daf51c0ed4e17cef44018,0.13s.
https://api.worldbank.org/v2/en/indicator/NE.EXP.GNFS.ZS?downloadformat=csv -> ReadTimeout12.08s.
Same indicator URL plus &source=2 -> ReadTimeout12.16s.
https://api.worldbank.org/v2/en/country/all/indicator/NE.EXP.GNFS.ZS?downloadformat=csv&source=2 -> ReadTimeout12.10s.

The implementation report additionally records much longer probes with HTTP400 ASP.NET errors. Controller results confirm per-request unavailability, not a permanent diagnosis or an exhaustive no-alternative-channel claim. Do not freeze the incident's old list of eight failing indicators into configuration: availability varied during testing, including previously healthy indicators. No outage-driven series inactivation, verifier bypass, schema/precision relaxation, alternate-channel switch, scheduled retry or deployment was made.

## Remaining gate and deferred minors

Task13 stays BLOCKED on a successful all-active independent live verification. Recheck source availability with a bounded probe before another full live run. Separate collection from implementation/review; stop repeated network attempts once reproducible unavailability is recorded. A reviewed alternate publisher export can be considered if it persists, but no such switch has been approved here. T14-T16 not started.

Reviewers found only nonblocking issues: source/live docstrings say19 indicators while active scope is18; implementation report fixture count28 should be29 manifest entries; compressed ZIP-stream corruption may raise zlib.error rather than ValueError, still caught by the existing verification fail-closed boundary; content-addressed storage deduplicates repeated evidence envelopes. Record source docstring/exception diagnostics for a later scoped fix, not permission to bypass the live gate.

Handoff/ledger are authoritative for task status. Do not redispatch completed REN or DGEG safe-disposition work. DGEG ingestion remains separately blocked and REN remains licence-withheld.
