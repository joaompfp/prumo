# Task 18 controller release and production checkpoint

Status: runtime implementation, reviews, merge, push and installation accepted. Task 18 remains OPEN for actual 24-hour observation and review of the continuing source pass. Task 19 and final Project 1 audit/acceptance are not complete.

## Release and verification

The owner explicitly requested Task 18, merge, commit, push and deploy. Runtime changes are the prerequisite refactors 2562656/aa89fed, image/deployment contract bb6fdeb and scheduler 95b4180. Independent specification PASS and separate quality APPROVED cover bf27e36..19c6487 plus the inspected operations.md prose adjustment. Later changes before merge were reports/prose only; an executable-path diff against 19c6487 was empty.

Controller execution in the existing Python 3.12 / pytest 9.2 environment:

```bash
.venv-ci/bin/python -m pytest tests -q \
  --basetemp=/home/joao/.hermes/cache/scratch/prumo-task18-full
# 1435 passed, 7 live deselected, 3 warnings in 335.39s
.venv-ci/bin/ruff check app/ ingest/ tests/ingest/test_scheduler.py \
  tests/ingest/test_scheduler_contract.py tests/test_docker_contract.py
# All checks passed
.venv-ci/bin/python -m pytest tests/test_docker_contract.py \
  tests/ingest/test_scheduler.py tests/ingest/test_scheduler_contract.py -q \
  --basetemp=/home/joao/.hermes/cache/scratch/prumo-task18-focused-controller
# 53 passed in 20.35s
```

Main merge `49a3602b936fd05db6a2032965c4f892e39906ee` has parents a18a58a and 7ad82d1; main and pipeline-rebuild push targets were read back from origin. Hosted CI https://github.com/joaompfp/prumo/actions/runs/43342679524 completed successfully on that exact SHA: lint success; tests 1434 passed / 1 skipped / 7 deselected / 3 warnings in 307.92s, aggregate coverage 88%. This is actual GitHub Actions, distinct from the local 1435 result. Non-failing runner/action deprecation and post-job git-cleanup warnings do not change the successful job conclusions. CI metadata is archived in evidence/task-18/ci-result.json.

Infrastructure commit `6a58b51c762c4b8a57b7dd4fd8272a4c963c3dd2` was pushed and read back on origin/f0nix in joaompfp/infra. Scope: worker include/service, SQLite/raw env paths, removal of obsolete web Ollama/ai_net coupling, encrypted FRED provisioning. The nested app-repo pointer and unrelated infra work were not staged. Actual YAML files were read back and dc-web config --quiet passed.

The initial Kimi/Ollama implementer exhausted its provider quota after committing the prerequisite refactors and writing partial scheduler tests. The controller preserved that work and relaunched fresh agents through the already authenticated OpenAI route with per-invocation flags, without permanent routing changes. Scheduler/image implementation scopes were file-disjoint; the spec and quality reviews were separate and sequential. Actual CLI sessions and reports retain authorship; no Claude trailers were invented.

## Built image and installed services

Used the documented f0nix dc-web aliases only: build via dc-web build prumo-ingest, then deployment via dc-web-up prumo and dc-web-up prumo-ingest. No raw Compose/run deployment, routing restart, public UI restoration, push alert or backup was introduced.

The image built successfully; its actual packaged scheduler help ran in a temporary alias-created container. A separate in-image probe loaded/planned the registry: 25 groups, explicit blocked DGEG, migrations included; no DuckDB/pyarrow/pandas/PIL, credential files, .git, collectors/scripts/seeds. Packaged scheduler SHA-256 `51ec44ee6b44619e3df3d011a617a0436e789af7caff001cb824d744090ee9d1` matched the local tested source. The web build context was 1.89 MB. The deployed worker manifest-list image ID was `sha256:cbce2ba401f52447c93198cc8f2269a3323483ca88811212086312521d1f46e3`; the underlying image configuration remained the previously probed build.

`prumo` was healthy; `prumo-ingest` was running with memory limit 536870912 bytes, restart unless-stopped, no host-published port and inherited web healthcheck disabled. The exposed 8080/tcp image metadata is not a host binding. At the early check the worker used about 74 MiB, with zero restarts/OOM. That is an observed point, not a resource-peak or 24-hour claim.

FRED_API_KEY was transferred without logging its value, encrypted into f0nix SOPS and decrypted/read back for equality while all pre-existing keys were preserved. No plaintext secret file, committed value or changed runtime auth contract was used. Worker injection was checked without printing it; its genuine scheduled FRED run subsequently verified.

GET checks returned200 for http://100.118.19.6:8088/healthz and both public URLs https://cae.joao.date/ and https://joao.date/dados/. The health body reported ok and both public bodies contained Em manutenção.

## Original data and initial catch-up

The original CSV was installed at `/home/joao/docker/stacks/web/appdata/prumo/migration/legacy-indicators.csv`, byte-identical to the f3nix original: SHA-256 `ca4ae36f10e30028106848bdd9db13c90bc42eb358ab5ad0ba9a73d50b2a3402`. The worker was stopped during import and initial catch-up.

```bash
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
  import-legacy /data/migration/legacy-indicators.csv
```

Actual result: 161263 legacy rows imported; 73863 not_in_registry, 7468 missing_unit, 3082 unit_mismatch, 480 suspect_unit_scale and 6 non_numeric quarantines. Initially 44487 active licensed World Bank legacy rows were queryable, still legacy-unverified with original receipt dates. The complete 161263-row legacy fingerprint before and after new ingestion remained `2dbabfcd42c1a99e963459cc8d61093961e5f717e1299c7b0fa0b8a5b5b0e6b5`. The old 88879104-byte DuckDB remains unchanged, SHA-256 `75506bce135f3feb6c6325673426f397892e0ed68aa0a014181934fa2be58e82`.

The initial live E-REDES command requested 2026-04-01 through 2026-11-12 inclusive (end exclusive 2026-11-13 UTC), using the actual inclusive CLI contract. It verified run 9: 64479 observations, 24 duplicate_period quarantines and 50/50 sampled matches. The publisher's returned observations end at 2026-11-11T00:00:00+00:00; requesting later days did not invent data for them. The later rolling scheduled run 11 wrote 291 observations with 0 quarantines and 50/50 sampled matches; the served history still contained 64479 observations. Both are real production runs, not the earlier isolated fixtures.

## Automatic pass checkpoint

At 2026-11-13T01:26:35.166223+00:00:

| Source | Actual new run | Served/current disposition |
|---|---|---|
| Banco de Portugal | run 10 verified, 4318 observations, 78 missing quarantines, 50/50 samples | 4318 fetched rows queryable |
| E-REDES | bootstrap run 9 and scheduled run 11 verified, 100/100 samples combined | 64479 fetched current rows; native dates preserved |
| Eurostat | run 12 verified, 45500 observations, 62 quarantines, 329/329 samples | 45500 fetched rows queryable |
| FRED | run 13 verified, 5004 observations, 1728 publisher missing cells quarantined, 50/50 samples | 0 served under unchanged IMF licence gate |
| INE | running, started 01:23:46 UTC | No fresh production verification yet at this checkpoint |
| OECD / REN / World Bank | Queued behind INE in the serial pass | No new scheduled result yet; World Bank's 44487 eligible dated legacy rows remained usable |
| DGEG | Explicit blocked JSON record before attempted sources | Inactive/not-verifiable and legally withheld; no invented new ingestion |

No all-source-fresh or completed-pass claim is made. Later source results must be read from the live DB/logs. The scheduler uses one authoritative dataset per World Bank indicator and one registered per-source verifier; a failing indicator's retry cannot make healthy siblings due. Previously verified/approved legacy observations remain available after a failed refresh. Whole-source World Bank fresh acceptance remains unestablished at this checkpoint.

The read-only audit confirmed SQLite integrity/foreign keys, zero served rows from denied licences, every currently archived raw file's size/hash/path, all referenced verification evidence hashes and unchanged legacy observations/database. At the checkpoint it checked 278 unique raw files totaling 5747077 bytes and 126 distinct verification evidence objects. These are archival-integrity checks, not an independent reparse of every production observation. Verification sample totals come from the actual new DB. JSON receipts are in evidence/task-18; the full live raw archive remains in the production data directory.

## Actual 24-hour gate and operator handoff

Observation start: 2026-11-13T01:21:18.732242+00:00 from the actual Docker start timestamp. No full window has elapsed in this report. The loop is serial and waits 15 minutes after each completed pass; a slow source delays later groups. Worker uptime alone does not prove freshness. Its advisory lock coordinates scheduler processes, not separate manual CLI writers.

A no-agent, local-only evidence collection was created and read back as Hermes job `41f08dd25c5c`, scheduled once at 2026-11-14T01:24:32.992446+00:00. It uses `/home/joao/.hermes/scripts/prumo-task18-observe.py` to run the durable operator script `/home/joao/prumo-operations/task18-49a3602/collect-observation.py`. The script's real --snapshot path successfully read services/status/audit/logs/public maintenance and wrote/read back receipts. Default mode and wrapper both correctly refused an early window. No future 24-hour success is asserted; no model/provider or push delivery is required. A completed collection still requires controller review and cannot close the task itself.

Durable operator evidence on both machines: `/home/joao/prumo-operations/task18-49a3602`. Repository scripts and checkpoint receipts: `docs/superpowers/handoff/reports/evidence/task-18/`. Keep the worker running for observation. Before any separate manual import/catch-up, follow the stop/review/resume procedure and restart the observation window if continuity is interrupted.

Runnable instructions: `docs/data/operations.md`; original-file/manual capture authority: `docs/data/manual-refresh.md`. Commands explicitly use --db/--raw-dir because the CLI's older PRUMO_DB variable differs from the worker's PRUMO_DB_PATH. DGEG ingestion and REN/FRED/OECD redistribution permissions remain unresolved. Task 18 acceptance awaits real elapsed observation and reviewed per-source exceptions; Task 19/final project closure have not begun.
