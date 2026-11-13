# Task 12 Phase A — REN adapter + licence gate report

Implementer: fresh subagent at base 731ef4d, branch pipeline-rebuild. Scope: `docs/superpowers/handoff/reports/task-12-brief.md` Phase A only. DGEG untouched (separate reconciliation); Task 12 NOT closed by this report.

## Deliverable 1 — serving licence gate (migration 0005, Ruling AD / spec §11.4)

`ingest/migrations/0005_served_licence_gate.sql` (new file; 0001–0004 untouched) replaces only the view: `served_observation` now joins observation → series → source and requires `source.redistribution_ok = 1` for BOTH `fetched` and `legacy-unverified` rows (the legacy arm also still needs `legacy_served='1'`). Verified-run, latest-vintage and legacy-never-hides-fetched precedence and the column set/order are unchanged (`SELECT o.*`). Licence revocation/reapproval goes through the normal `upsert_source_and_series` sync and takes effect immediately on existing rows; nothing is ever deleted.

RED → GREEN (actual output):

- RED (tests written before the migration existed): `5 failed, 3 passed` — failed: denied-fetched, denied-legacy(+legacy_served), revoke/reapprove toggle, mixed-sources, 0004-DB migration; passed: the 3 invariants that already held (vintage precedence, unverified hidden, view columns).
- GREEN: `8 passed`; full suite `759 passed, 3 deselected` (751 baseline + 8).

Tests (`tests/ingest/test_licence_gate.py`): denied fetched rows are `verified`-yet-unserved (run state stays 'verified', row still in `observation` — verified ≠ served); denied legacy hidden even with legacy_served='1'; revoke→served=[] immediately, reapprove→restored, row counts unchanged; mixed sources serve only the allowed side; allowed-source vintage/legacy precedence unchanged; unverified runs hidden for both; view columns == observation columns in order; real 0001–0004 database (schema from the scripts, rows incl. a leaking denied row) upgraded by `open_db`: 0005 recorded, all observation/dataset_run/quarantine rows byte-identical, gate active, latest vintage intact.

## Deliverable 2 — REN collector + independent verifier

Registry (real, no invented fields): 14 active monthly PT series get `native_code` (`ElectricityConsumptionSupplyMonthly:<TYPE>` ×13, `ElectricityMarketPricesMonthly:PT.Preço Médio` ×1), public page `url` (balanco-mensal / mercado), `active: true`. Source block: real licence wording with clause quotes, `licence_url` = datahub.ren.pt Termos Legais, `redistribution_ok: false` KEPT, `verifiable: true` (an independent channel exists). `core.proposed.yaml` mirrored (identity test). `licences-todo.md` records the clause 2/3.2 evidence and the UNRESOLVED owner decision.

Source `ingest/sources/ren.py`: one request per (endpoint, month), `culture=pt-PT` + explicit `year`/`month` always (undated requests silently answer a wrong vintage; unpublished month = HTTP 404 → fail closed via the pipeline, never skipped/relabelled). Period range constructor `RenSource(periods=...)`; default = last 13 COMPLETED months (`completed_months(today)`, running month excluded). Parse: `json.loads(parse_int=parse_float=str, object_pairs_hook=dup-reject)`; balance entry must be exactly {monthly_Accumulation, type} with numeric token; selected types unique+present per month; unmapped/retired types (CARVAO etc.) skipped, never rejected; price block single month key cross-checked against the requested month, PT/ES blocks exactly {Fora Vazio, Preço Médio, Vazio}, sibling surfaces pinned ('Separação de mercados [%]', 'Capacidade [MW]'). Rows: `unit_raw=None` (no unit surface in payload — registry unit authoritative), `flag_raw='normal'` (no status surface anywhere — declared in docstring), `response_index` per request. Period comes from the validated request params (payload has no period surface — honest declaration).

Verifier `ingest/verifiers/ren.py`: `GET https://datahub.ren.pt/service/exports/csv` modelId 1550 (balance) / 2649 (market) — different endpoint family AND CSV serialization (portal SPA export service). Balance request start=end=month last day, market start=first..end=last (exactly the archived request shapes). Period read from the CSV header ('set 26 [GWh]' / ',setembro,,2026,') — request echo refused on mismatch; geography pinned by ',PT,ES,PT,ES'; unit read from the header bracket (observed_unit='GWh'); market CSV carries no unit → observed_unit=None honest; no flag surface → observed_flag=None. Mapped labels unique-enforced (duplicates exist only among unmapped rows: Cogeração ×3, Outros ×2). Evidence = exact CSV bytes per item (one deciding response → no envelope needed), cached per chart+month inside one check. No code shared with the collector; TYPE↔label map duplicated on purpose. Passes `register_verifier` static allowlists and `assert_verifier_independent` subprocess guard (`blocked_prefixes=("collectors","ingest.flags","ingest.sources")`).

Fixtures: byte-identical copies of the controller-reviewed 2026-11-11 discovery archive, sha256 re-verified against its MANIFEST (5 API responses incl. the 404/400 error bodies, 3 CSV exports 2026-09 + 2020-06), manifest in `tests/ingest/fixtures/ren/MANIFEST.json`. Pinned samples cross-checked channel-vs-channel at recording: CONSUMO 2026-09 API 4442 == CSV 4442; HIDRICA 645 == 645; CCGT 510 == 510; SALDO_IMPORTADOR 1616 == 1616; price 'Preço Médio' 143.9 == 143.9; 2010-01 SALDO_IMPORTADOR −263 negative token preserved.

Tests: 35 adapter tests (tokens/flags/index/order + malformed/missing/duplicate/month-mismatch/unknown-surface/non-2xx/HTML/bad-JSON probes + pipeline write + gate withholds a verified run) + 4 registry unit-table tests (`GWh` from CSV '[GWh]' header; `EUR/MWh` from market page narrative; label map exercised) + 20 verifier tests (recorded cases, cache, evidence bytes, tampered value→'value differs' through verify_run, tampered '[GWh]'→'[MWh]'→13×'unit differs', header month/year/geography drift, duplicate/missing row, 404, registration ×2, subprocess independence, offline evidence recovery + `replay_item`).

## Live smoke (real network, 2026-11-11)

`.venv-ci/bin/python -m pytest tests/ingest/test_live_ren.py -m live -s`:

```
requested periods: 2025-10..2026-10 (13 completed months, today 2026-11-11)
final state: verified  run_id=1  written=182  quarantined=0  served=0  verifications=[(5698517318452557401, 50, 1)]
  ren.electricity_{biomass,consumption,exports,hydro,imports,natural_gas,natural_gas_ccgt,
    net_imports,price_mibel,production_non_renewable,production_renewable,production_total,
    solar,wind}.PT: 13 observations 2025-10..2026-10  (each)
1 passed in 42.54s
```

All 14 series × 13 completed months parsed live; seeded sample 50/50 matched through the independent CSV channel; 26 ok raw_fetch rows; per-item evidence reloaded from the raw store offline. **served=0 with the real registry** (source redistribution_ok=0) while technically verified — exactly the required withheld-data outcome; the licence was never enabled to pass. f0nix read-only probe: servicebus balance API and portal CSV export both HTTP 200 from f0nix, 2026-11-11 (no deployment).

Full suite after all chunks: **818 passed, 4 live deselected, 1 warning** (751 baseline + 67 new).

## Licence blocker (recorded, unresolved)

REN Termos Legais (https://datahub.ren.pt/pt/termos-legais-e-condicoes-gerais/, HTTP 200, archived `terms/datahub-termos.body` in the discovery package): clause 2 reserves all exploitation rights; clause 3.2 forbids reproduction/copying/distribution/public communication/transformation except as authorized by law or express REN consent, and extraction/reuse of the whole or a substantial part of contents/databases. No open grant. → registry keeps `redistribution_ok: false`; serving needs the owner (consent request or legal review). The adapter and verifier are built, proven and gated — not blocked.

## Tooling notes

GitNexus: `impact open_db` LOW by CLI this session (controller pre-recorded MEDIUM/13 direct); `sync_registry` untouched per brief; `detect-changes --scope staged -r prumo-pipeline` answered "No changes detected" for each chunk (SQL/new-file scope). Graph parser warnings for test_verify.py and collectors/ine.py acknowledged — coverage is by tests, not the graph. No existing Python symbols were modified.

## Commits (branch pipeline-rebuild, scoped to owned files)

- `19b1c91` serve: gate serving on source redistribution licence (migration 0005) — migrations/0005_served_licence_gate.sql, tests/ingest/test_licence_gate.py
- `37afa38` registry: REN native ids, URLs and documented restrictive licence — registry/core.yaml, registry/licences-todo.md
- `5d73f91` registry: mirror REN updates into core.proposed.yaml (identity test) — registry/core.proposed.yaml
- `36c74c8` source: REN DataHub servicebus JSON adapter + recorded fixtures — ingest/sources/ren.py, tests/ingest/fixtures/ren/**, tests/ingest/ren_fixtures.py, test_source_ren.py, test_registry_ren_units.py
- `4070306` verify: REN portal CSV-export verifier (independent channel) — ingest/verifiers/ren.py, tests/ingest/ren_verifier_fixtures.py, ren_verifier_entry.py, test_verifier_ren.py, test_live_ren.py
- (report commit) this document

Controller-owned brief/ledger/HANDOFF untouched and unstaged; DGEG entries untouched; no main merge, push, deploy or secret edits.
