# Task 16 — E-REDES/dadosgov legacy reconciliation + bounded channel discovery (read-only)

Date: 2026-11-12 (probe window 18:13–18:14 UTC, host f3nix). Branch `pipeline-rebuild` @ 03639ee, clean.
Trigger: owner rejected the earlier conditional "not applicable" disposition (registry seeded only from
`indicators.csv`), see `task-16-scope-disposition.md`. This report reconciles what the legacy system
ACTUALLY contained and probes current publisher channels. **No code, registry, ledger or handoff was
changed; nothing committed.** Fixture bytes are exact publisher responses archived under
`docs/superpowers/handoff/evidence/task-16-discovery/` (sha256 manifest digest
`1d232e30959e9065dcf272793fc943a7444d18b980569cc3defd849933fb8e71`, computed over all files there).

## 1. Legacy integration inventory (code existed, stored data did not)

| Component | State |
|---|---|
| `collectors/eredes.py` (EREDESClient, OpenDataSoft v2.1, 8 dataset IDs) | present since the repo's first public commit `47d8655` (2026-03-16); byte-identical on `main`, `pipeline-rebuild` and f0nix container `/app` (md5 `51f0f6c5f02896115df3e9dffb982a43`) |
| `collectors/dadosgov.py` (DadosGovCollector, CKAN `/api/3/action/*`, 2 hardcoded dataset ids) | present, same commit; md5 `5cb553b489f268bc617d4d13d3ca1ded` |
| `scripts/collect_scheduled.py` | `EREDES` in `SCHEDULE` at **weekly**; `collect_eredes()` calls only `get_national_production(year, month)`. `dadosgov` was **never** in the schedule |
| `scripts/collectors/cae-collect` CLI | supports `eredes` fetches (fetch+cache view tool; no EREDES entries in `fetch_log`) |
| `legacy-ui-final:SOURCES.md` | documents `E-REDES https://www.e-redes.pt/pt-pt`, "Daily / Monthly (dataset-dependent)"; dadosgov absent |

## 2. Stored-data reconciliation — zero E-REDES/dadosgov rows anywhere checked

Checked sources (all consistent):

1. `~/projects/_legacy_export/indicators.csv` (246,162 rows): sources = EUROSTAT 157,312 / WORLDBANK 52,618 /
   FRED 10,145 / INE 9,869 / DGEG 7,225 / BPORTUGAL 3,471 / REN 2,714 / OECD 2,291 / ERSE 517.
   **0 EREDES, 0 DADOSGOV rows.** Global fetched_at window: 2026-02-26T01:39:43 … 2026-04-06T01:47:04Z.
2. Live DuckDB on f0nix (`docker exec prumo … /data/cae-data.duckdb`, read-only): `indicators` 246,162 rows,
   identical per-source distribution and bounds. `collection_log` 60 rows — 7 sources, all `ok`, all from the
   single 2026-04-06 run (01:32–01:49Z), none EREDES/DADOSGOV. `fetch_log` 432 rows — 6 sources, all
   2026-02-26, none EREDES/DADOSGOV. `meta`: schema_version=1 only.
3. f0nix `/data/archive/`: 7 parquet files, all `20260406_{fred,ine,bportugal,eurostat,worldbank,dgeg,ren}_mixed_*`.
   **No eredes/dadosgov parquet ever archived.** `/data/collect-cron.log` does not exist.
4. `/data/audit-log.jsonl` (2026-03-15): catalog-drift audit lists no EREDES/dadosgov indicators.
5. Local/scratch search: no archived E-REDES JSON/CSV exists outside the repo.

Root causes, stated exactly:
- `collect_eredes()` passes the raw OpenDataSoft envelope `{source, dataset, total_count, count, data:[…]}`
  into `_flatten_dashboard`, which only consumes `{indicator: {"data": [{"period","value"}]}}` sections.
  Every key is skipped (values are str/int/list), so the wrapper **always returns 0 rows** — no parquet,
  no ingest, no `collection_log` entry. The EREDES weekly schedule existed but was structurally incapable
  of storing anything.
- `dadosgov` was never scheduled; its CKAN target `/api/3/action/*` returns HTTP 404 today (see §4), so the
  collector could not have produced rows had it run.

Consequence: there are **no stored E-REDES "April rows"** — nothing to import, nothing served, nothing to
preserve with honest fetch dates for this source. Any April-bearing claim must not be invented. The last
successful legacy collection for ANY source is the 2026-04-06 01:47:04Z run above.

## 3. Current E-REDES channel state (probed today, 11 requests, 3.46s)

All fixtures: `evidence/task-16-discovery/NN-*.body` + `.meta.json` (final URL, status, elapsed, bytes).

| Probe | Status | Facts |
|---|---|---|
| catalog list (limit=100) | 200, archived body truncated by probe at 200 KB | **70 datasets** in portal; visible licences all `CC BY 4.0` |
| `energia-produzida-total-nacional` metadata | 200 | fields: `datahora` datetime; `dgm`/`pre`/`total` double, labels "Market (kWh)", "Special Regime (kWh)", "Total (kWh)"; license **CC BY 4.0** (`https://creativecommons.org/licenses/by/4.0/`); publisher E-REDES; **modified 2026-11-12T14:35:19Z** (actively maintained) |
| records latest/earliest | 200 | **135,377 records, 2023-01-01T00:00Z … 2026-11-11T00:00Z**, 15-min cadence |
| `consumo-total-nacional` metadata | 200 | `bt`/`mt`/`at`/`mat`/`total` double, "(kWh)" labels; CC BY 4.0; modified 2026-11-12T14:35:26Z |
| records latest/earliest | 200 | **135,281 records, 2023-01-01T00:00Z … 2026-11-11T00:00Z**; JSON carries raw float tails (e.g. `1551218.9714849999`) — tokens must be preserved verbatim, never rounded |
| `energia-injetada-na-rede-de-distribuicao` metadata | 200 | 6 technology doubles "(kWh)"; CC BY 4.0; modified 2026-11-12T14:35:24Z |
| `energia-produzida-total-nacional/exports/csv?lang=pt&timezone=Europe/Lisbon` | 200, stream-capped at 150 KiB by probe (1,892 lines archived) | **genuine different format**: BOM + `;` + CRLF, header `datahora;dia;mes;ano;date;time;dgm;pre;total`, ascending order, full-precision plain decimals |

Independence sample: earliest JSON row `2023-01-01T00:00: dgm 227797.0 / pre 941173.75 / total 1168970.75`
== first CSV data row, exact. The exports/csv route is a valid independent verifier channel (different
endpoint AND format), same portal.

Unverified within the 12-request cap: the other 4 legacy dataset IDs (`02-consumos-faturados-por-codigo-postal…`,
`3-consumos-faturados-por-municipio…`, `previsao-de-consumo`, `codigo-de-atividade-economica…`) — existence not
confirmed today (the truncated catalog page shows `25-plr-producao-renovavel` still live). No per-record
status/flag surface exists on these datasets (field lists have no quality column) → verifier reports
`observed_flag=None` honestly.

## 4. dados.gov.pt — integration dead at transport, out of recommended scope

- `GET /api/3/action/package_show?id=execucao-orcamental-da-administracao-central` → **404**
- `GET /api/3/action/package_show?id=plano-de-recuperacao-e-resiliencia` → **404**
- `GET /api/3/action/package_search?q=execução+orçamental` → **404**
  (`10/11/12-dadosgov-*` fixtures). Bodies are Flask-style "URL was not found" — the CKAN API the collector
  targets does not exist on the current portal. The live API family (portal was rebuilt on a different stack)
  was NOT probed (request cap reached); re-discovery is implementation work, not assumable.

## 5. Implementation-ready scope recommendation (small, defensible from legacy actual use)

Legacy actual use attempted exactly **one** dataset (`energia-produzida-total-nacional`, weekly national
production). The defensible core scope is the three confirmed-live national 15-min datasets:

Proposed registry block (draft only — NOT written):

```
eredes:
  licence: CC BY 4.0  # per-dataset metadata, re-read 2026-11-12 (fixtures 02/05/08)
  licence_url: https://creativecommons.org/licenses/by/4.0/
  attribution: 'Source: E-REDES'
  redistribution_ok: true
  verifiable: true   # independent channel: same-portal /exports/csv (BOM+';'+CRLF), sampled exact match vs JSON
  # series (native 15-min subdaily — see blocker B1):
  #   eredes.production_market.PT   <- dataset energia-produzida-total-nacional, field dgm, unit kWh
  #   eredes.production_special.PT  <- same dataset, field pre, unit kWh
  #   eredes.consumption_total.PT   <- dataset consumo-total-nacional, field total, unit kWh
  # (optional phase 2: energia-injetada-na-rede-de-distribuicao six technology series)
```

Adapter shape: `ingest/sources/eredes.py` queries `/records` windowed by `where=datahora in [..]`
(100-record pages), `parse_float=str` token preservation; verifier `ingest/verifiers/eredes.py` uses only
`/exports/csv` (no shared helpers; subprocess independence guard). Schedule: daily (portal modified daily;
latest record currently T-1 day 00:00Z). Units are **energy per 15-min interval (kWh)**, not power — labels,
not conversion, carry this.

## 6. Blockers / owner decisions

- **B1 (scope-blocking): subdaily schema.** 15-min `datahora` does not fit the current period-style series
  shape. Recommendation: admit a subdaily frequency for these series — do NOT aggregate to daily/monthly
  (explicitly forbidden) — or keep E-REDES inactive with this report as the reason. Owner decides.
- **B2: dadosgov** needs fresh API discovery (current portal ≠ CKAN); exclude from Task 16 scope, revisit
  only if the owner wants a separate task.
- **B3: freshness gap.** Even if adopted, E-REDES coverage starts at the first new ingestion date
  (revision-history rule): there is no legacy baseline to carry over.

## 7. Manual refresh instructions (exact, for the record)

1. Portal catalog: open `https://e-redes.opendatasoft.com/explore/?sort=modified` → dataset page.
2. Production CSV: dataset `energia-produzida-total-nacional` → "Export" tab, or direct
   `https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/energia-produzida-total-nacional/exports/csv?lang=pt&timezone=Europe/Lisbon`.
3. JSON records page: `…/datasets/<id>/records?where=datahora%20%3E%3D%20%222026-11-11%22&order_by=datahora&limit=100`
   (page with `offset`).
4. Native metadata (fields/licence): `…/datasets/<id>` (no auth, CC BY 4.0 shown under "License").

## 8. Limits

Read-only. No commits, no registry/handoff/ledger edits. 12/12 request budget used (11+1), 3.46 s + 0.2 s
network time, from f3nix egress (f0nix egress not probed — World-Bank-style egress differences untested for
this host). Fixtures are genuine publisher bytes; the catalog and CSV fixtures are probe-truncated and their
`truncated_by_probe` flags are set in the sidecars. Task 16 remains **open** (not complete).
