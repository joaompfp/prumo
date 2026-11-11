# SDD ledger — plan: docs/superpowers/plans/2026-11-10-base-data-pipeline.md
Spec: docs/superpowers/specs/2026-11-10-base-data-pipeline-design.md (reachable). Worktree ~/projects/prumo-pipeline, branch pipeline-rebuild (base a18a58a). Test python: .venv-ci/bin/python -m pytest.
Deploy target: f0nix (ssh f0nix; its prumo checkout at ~/docker/stacks/web/images/prumo; infra repo ~/docker on branch f0nix).

## Pre-flight scan (task pairs sharing a file/interface; each task's self-consistency)
| Tasks | Produces vs consumes | Finding |
|---|---|---|
| 1 vs 17 | T1 keeps collectors/scripts; T17 deletes them | consistent (collectors reused by T9-16 in between) |
| 1 self | test_no_claude_references greps whole repo for 'anthropic' but OPENSOURCE.md/static/i18n and scripts/enrich_new_indicators.py contain it | CONFLICT -> Ruling A, B |
| 1 vs infra | T1 deletes templates/, but f0nix compose prumo.yml bind-mounts templates | CONFLICT -> Ruling C |
| 2 vs 6 | view served_observation (verified runs only) vs T6 identical-payload short-circuit | CONFLICT -> Ruling D |
| 2 vs 8 | UNIQUE(series,period,raw_fetch_id) with NULL raw_fetch_id (legacy) does not dedupe in SQLite | Ruling E |
| 3 vs 5 | RawRow defined in T5, used by T6 parse | consistent (fixed in plan) |
| 5 vs 6 | validate() per spec/rows; run_dataset passes dict[series_id, list[RawRow]] | consistent |
| 6 vs 7 | run_dataset result state pending-verification consumed by verify_run | consistent |
| 7 vs 9-16 | Verifier/Source protocols; register_verifier rejects shared parser imports | consistent |
| 8 vs 17 | import_legacy used by CLI import-legacy; duckdb only in migration reqs | consistent |
| 14 | FRED key: web.enc.env key list has no FRED key | Ruling F |
| 17 vs 18 | status.report used by scheduler logs; due() uses registry schedule field | T3 registry model needs optional `schedule` + `throttle_rps` fields -> Ruling G |
Each task text agrees with itself otherwise.

## Rulings
Ruling A: T1's no-claude test scans only code/config files (*.py, *.sh, *.yml, *.yaml, *.txt, *.toml, Dockerfile, requirements*) excluding .git, venv, .venv-ci, docs, tests, static — spec says remove Claude *code/env*, not prose — cost if wrong: prose mentions of Anthropic remain in OPENSOURCE.md.
Ruling B: T1 also deletes scripts/enrich_new_indicators.py (uses Anthropic API) — spec: all Claude code removed — cost if wrong: loses an AI enrichment script (git-recoverable).
Ruling C: T1 also edits infra f0nix compose (~docker/stacks/web/compose/prumo.yml on f0nix, branch f0nix) to drop the templates bind mount and keep app/static; deploy requires f0nix to fetch+checkout branch pipeline-rebuild of the prumo repo (branch pushed to origin, main untouched) — cost if wrong: root-owned empty dir created by docker.
Ruling D: T6 idempotent short-circuit applies only if the previous run of that dataset is `verified`; after failed-verification/failed-* a re-fetch with identical bytes still re-parses and re-verifies — otherwise a failed dataset could never be retried — cost if wrong: stuck unserved dataset.
Ruling E: T8 legacy idempotency is enforced in code (one synthetic legacy run; skip if exists), not by the UNIQUE constraint — cost if wrong: duplicate legacy rows.
Ruling F: T14 implementer checks FRED auth (fred.py env var / keyless fredgraph.csv); if a key is needed and missing from SOPS, report NEEDS_CONTEXT/BLOCKED to controller (secrets are the owner's) — cost if wrong: FRED delayed.
Ruling G: T3 SeriesSpec/registry includes optional `schedule: str | None` (interval like "1d"/"7d", default by frequency) and `throttle_rps: float = 1.0`, used by T17/T18 — cost if wrong: small rework.

## Execution
Task 1: implemented (commits a18a58a..031eb3b; infra f0nix 63b0af1); implementer concerns: audit_nightly.py in entrypoint cron fails nightly until T17; ci.yml ANTHROPIC key removed; requirements trimmed (pandas, Pillow, pytest-asyncio, jinja2); static/i18n, OPENSOURCE.md, tests/README.md still mention anthropic (excluded by Ruling A). Task review dispatched.
Task 1: minor (deferred): GET-only catch-all returns 405 on HEAD (uptime probes) -> consider fixing in T18 or final review
Task 1: minor (deferred): scripts/audit_nightly.py + entrypoint cron fail nightly until T17 removes them (tracked, T17 must delete audit_nightly.py and the cron block; T18 rewrites entrypoint)
Task 1: minor (deferred): ci.yml still runs create_seed_db.py/--cov=app; pytest.ini + tests/README.md + tests/conftest.py stale DuckDB-era -> clean in T17/T19
Task 1: complete (commits a18a58a..031eb3b, review clean)
Task 2: implemented a564c80; note for later tasks: 'latest' vintage = highest observation.id so insert in fetch order; legacy dedupe in code (Ruling E). Review dispatched (opus).
Task 2: review (opus): spec ❌ — I-1 legacy row can hide verified fetched data in served_observation; I-2 value_text nullable/empty. Minor (deferred): M-1 no trigger when series.frequency updated; M-2 inf value / year 0000 accepted; M-3 no same-source check across run/raw_fetch/series; M-5 test gaps (now partly covered by fix); M-6 f-string version in db.py.
Note for T6/T17 (reviewer's cannot-verify): UNIQUE(series_id,period,raw_fetch_id) means re-parsing an existing raw_fetch into a new run is rejected; each fetch must create its own raw_fetch row; G7 replay must rebuild a FRESH DB. T8 must create the legacy synthetic run in state 'verified' (else never served at legacy_served=1).
Task 2: fix round 1/5 dispatched (resumed implementer): I-1, I-2.
Task 2: fix round 1/5 (2 addressed, 0 open; commits a564c80..d4afded)
Task 2: minor (deferred): add tests legacy-before-fetched order and fetched-run-flipped-to-failed; 0001 edited in place (no DB deployed yet — if any DB gets migrated before T3+ changes, add 0002)
Task 2: complete (commits 031eb3b..d4afded, review clean)
Task 3: implemented 5bef97e (52 tests); review dispatched (sonnet).
Task 3: review: spec ✅/quality approved w/ 2 Important: I-1 Observation.value not tied to value_text; I-2 parse_number guesses locale ("1.234"). Minor (deferred): unicode digits in normalize_period (\d) (parse_number part fixed in round 1); `202509` accepted for M; Observation.period not validated in model; registry.py unhashable/missing `source` gives TypeError/odd message; sync doesn't deactivate series removed from YAML.
Ruling H: decimal separator is declared per series in the registry (SeriesSpec.decimal '.'|',' default '.'), parse_number(text, decimal) strict, never guesses — cost if wrong: registry entries must set decimal for comma-decimal sources (INE, BdP, REN...); T5 validate() must pass spec.decimal (T5's "1 234,5" test needs a spec with decimal=',').
Task 3: fix round 1/5 dispatched (I-1, I-2).
Task 3: fix round 1/5 (2 addressed, 0 open; commits 5bef97e..797a792)
Task 3: minor (deferred): Observation reload from storage for decimal=',' series needs context={"decimal": ","}; whitespace-padded value_text kept padded (normalise upstream in T5 validate: strip before building Observation? decide in T5); ".5"/"5." rejected; no validate_assignment.
Task 3: complete (commits d4afded..797a792, review clean)
Task 4: implemented 257793b (103 tests); review dispatched.
Task 4: review: spec ✅/quality approved; Important I-1: save trusts existing (possibly corrupt) file. Minor (deferred): symlinked <root>/<source> lets save write outside root; source-name blacklist vs allowlist; no parent-dir fsync; missing tests (symlinks, NUL, concurrency).
Task 4: fix round 1/5 dispatched (I-1).
Task 4: fix round 1/5 (1 addressed, 0 open; commits 257793b..c6483ac)
Task 4: complete (commits 797a792..c6483ac, review clean)
Ruling I: validate() (T5) strips surrounding whitespace from value_raw before building Observation, so value_text is the publisher's token without padding (padding carries no data and would break verification comparison) — cost if wrong: value_text differs from raw bytes only by whitespace; raw payload preserved anyway.
Task 5: implemented f121f48 (122 tests); review dispatched.
Task 5: review: spec ✅/quality approved; gap I-1: non-str/None input raises, aborting whole payload. Minor (deferred): flag_raw passed through unstripped; redundant unit.strip.
Ruling J: validate() maps None value->non_numeric, None period->bad_period; other non-str types raise TypeError at RawRow construction. SOURCE ADAPTERS (T9-16) MUST hand over the publisher's number TOKEN as str (json.loads(parse_float=str, parse_int=str) or equivalent) — never a Python float — and must not coerce; carry this into every adapter dispatch. Cost if wrong: "1.10" -> "1.1" would break verbatim value_text.
Task 5: fix round 1/5 dispatched (I-1 + pin duplicate-semantics tests).
Task 5: fix round 1/5 (1 addressed, 0 open; commits f121f48..b66e249)
Task 5: complete (commits c6483ac..b66e249, review clean)
Ruling K: dataset_run needs a dataset identity for "previous run of the same dataset": T6 adds migration 0002_dataset_key.sql (ALTER TABLE dataset_run ADD COLUMN dataset_key TEXT, nullable; = source name + ':' + sha256 of sorted series ids) — 0001 untouched — cost if wrong: small migration rework.
Ruling L: plan lacked a real HTTP client; T6 adds ingest/http.py (Http protocol + HttpResult(status, body, url) + RequestsHttp(throttle_rps, timeout=30, retries on 5xx/timeouts max 3 with backoff, UA 'prumo-ingest/1.0 (+https://cae.joao.date)')) — cost if wrong: minor.
Task 6: implemented 48a1709, e1dfaeb, 59e1337 (170 tests). Implementer concerns: (1) all observations link to run's FIRST raw_fetch (multi-page traceability) — candidate Important; (2) revisions compared on value_text; (3) zero-row series fails run, all-quarantined series ends pending-verification; (5) T7 must not sample/verify a run returned already 'verified' (identical-payload) and must handle empty runs; `now` defaults to UTC now; RequestsHttp returns 5xx after last retry. Review dispatched (opus).
Task 6: review (opus): spec ❌ narrowly; no Critical (no probe served unverified data/hid verified). Important: I1 observations all link to run's first raw_fetch (G1 violation); I2 all-quarantined series unflagged. Gap P2: pages before mid-pagination exception never stored. Minor (deferred): M1 some HTML error shapes (XHTML prolog, <head>, leading comment, BOM-only) mislabelled format_change vs fetch_failure; M2 storage failure leaves run 'running' forever; M3 nested transaction misclassified as format_change; M4 revision events re-emitted by each pending run; M5 RequestsHttp: redirect forwards caller headers cross-host, 429/Retry-After not honoured, SSLError retried, timeout per-read not total; M6 short-circuit keyed on bytes only -> after parser fix identical bytes never re-parsed (document; replay builds fresh DB); M7 overlapping datasets can leave an older value served.
Ruling M: a series with zero valid observations (no rows or all quarantined) -> format_change event for that series and the run continues; run fails-validation only if EVERY series is empty (or parse raises) — a discontinued series must not block siblings — cost if wrong: a dead series is only flagged by event/status, not by failing the dataset.
Task 6: fix round 1/5 dispatched (I1 response_index provenance, I2 Ruling M, P2 incremental fetch).
Task 6: fix round 1/5 (3 addressed, 0 open; commits 59e1337..1d16e86)
Task 6: minor (deferred): in every-series-empty case no quarantine rows written; M2 orphaned 'running' on storage error; per-page storage widens window.
Task 6: complete (commits b66e249..1d16e86, review clean)
Task 7: implemented cc71d21, 795445f, 39b31de (230 tests). Implementer concerns: draw_sample/verify_run require keyword specs= (spec.decimal not in SQL); ItemResult optional echo fields series_id/period (adapters should always set them; consider making required); migration 0003 adds observed_decimal/observed_unit/observed_flag/note to verification_item; DB failure mid-write leaves run pending-verification (loud); import-rule checks only verifier's own module (not transitive/dynamic); pre-existing ResourceWarning in test_pipeline.py fails 2 tests under -W error. Review dispatched (opus).
Task 7: review (opus): spec ✅ w/ gaps; no Critical. Important: I1 concurrent verify_run race can end verified with failed verification on record; I2 echo fields optional -> period never compared; I3 verifier can echo expected_text back; I4 independence rule only runs if register_verifier is called; I5 AST import rule bypassable (importlib, __import__, from ingest import sources, shared helper modules); I6 replay incomplete (spec.decimal not stored; evidence only a URL).
Ruling N: ItemResult.series_id/period REQUIRED and always compared. Ruling O: verifiers get BlindItem(series_id, period, spec) only — expected value/unit/flag never shown. Ruling Q: register_verifier = strict AST rules + TRANSITIVE shared-module check vs parser module (allow-list: ingest.models, ingest.http, ingest.sources pkg, ingest.verifiers pkg, ingest.rawstore); run_with_refetch must use the registered verifier. Ruling R: migration 0004 adds expected_decimal/unit/flag + evidence_sha256 to verification_item; ItemResult.evidence bytes saved in RawStore under "verify-<source>"; replay_item() helper re-compares from stored fields only.
ADAPTER TASKS 9-16 MUST: (a) set ItemResult series_id/period, (b) provide observed_unit/observed_flag whenever the channel exposes them and say in their report if not, (c) pass evidence bytes, (d) include a subprocess independence test (import verifier with a meta_path hook that blocks ingest.sources.* and run check() on fixtures; assert no collector module loaded), (e) hand number TOKENS as str (Ruling J), (f) use no shared helper between parser and verifier.
Noted for owner: short-circuit (identical bytes to previous verified run) is not re-sampled — spec 6b says 'every run'; documented; revisit if wanted. T17: CLI status must list stale pending-verification runs.
Task 7: fix round 1/5 dispatched (I1-I6).
Task 7: fix round 1/5 (5 addressed, 1 open — I5 attribute-access + alias bypasses of register_verifier; commits 39b31de..3a2dee8). Re-review minors (deferred): case-sensitive registry keys; verify_run itself accepts unregistered verifier (only run_with_refetch enforces — any CLI must call run_with_refetch/get_verifier); orphan evidence files from losing concurrent worker; BlindItem.spec.unit exposure accepted (adapter reviews must confirm unit read from evidence).
Task 7: fix round 2/5 dispatched (I5 + str-subclass `type(x) is str` + replay_item legacy rows).
Task 7: fix round 2/5 (I5 partial: listed bypasses closed, hardening a/b addressed; commit a4bc4e1) — re-review: 3 more bypass paths open (A re-exported module attrs via `from ingest import verifiers as v`; B dunder walks `__globals__`; C `from ingest.verifiers import <anything>`/star imports).
Ruling S: denylist cannot converge -> register_verifier switches to ALLOWLISTS (per-module name allowlist for ingest.*, stdlib allowlist, no dunder attrs, no getattr/type/etc.) and is documented as lint-level; the guarantee is a reusable runtime check `ingest/verifiers/independence.py::assert_verifier_independent(...)` (subprocess + meta_path blocker + loaded-module subset check) that EVERY adapter task (9-16) must call in its tests — cost if wrong: a verifier needing an extra name/stdlib module must extend the allowlist constant explicitly.
Task 7: fix round 3/5 dispatched.
Task 7: fix round 3/5 (A,B,C addressed; commits a4bc4e1..0f766b2; 341 tests) — re-review residual: typing.get_type_hints/ForwardRef string-eval gadget loading parser under non-ingest name passes static AND guard (adversarial only). Deferred minors: io.open/gzip.open/zipfile readable though bare open forbidden; guard checks module names not file origin (fixed in round 4); entrypoint module not statically checked.
Task 7: fix round 4/5 dispatched: guard also checks file origins of every loaded module (parser file or ingest/sources/* under any name) + static forbids eval-gadget names/string annotations.
Task 7: fix round 4/5 (1 addressed, 0 open; commit 0f766b2..5de6053; 366 tests)
Task 7: minor (deferred): nested quoted annotations list["x"] pass static; hardlink/copy of parser under another path evades open check (needs os/shutil, not allowlisted); static check doesn't follow non-ingest helpers (documented lint); only top-level quoted annotations rejected; `register`/`evaluate` generic names forbidden.
Task 7: complete (commits 1d16e86..5de6053, review clean)
Ruling T: Task 8 does NOT stop for owner review of the registry; spec §11.3 says the pipeline proceeds on provisional assignments — registry files (registry/core.yaml, overlaps.md) are surfaced to the owner in the final report. Cost if wrong: adapters built on provisional primaries may need rework.
Ruling U: legacy import/proposal read the old DB via a one-off CSV export (~/projects/_legacy_export/indicators.csv, produced on f0nix with the container's duckdb, columns source,indicator,region,period,value,unit,category,detail,fetched_at,source_id) using stdlib csv; duckdb is NOT a dependency of ingest/ (it crashes with Illegal instruction on f3nix's CPU) — cost if wrong: none (CSV is lossless for this table; value text preserved as exported).
