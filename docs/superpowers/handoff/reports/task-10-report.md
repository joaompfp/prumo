# Task 10 report — INE adapter + independent verifier (bddXplorer table channel)

Status: fix round 1 complete — adapter, verifier, registry, fixtures, legacy-scale quarantine and
tests all done; INE runs now verify and serve. The first pass's central claim ("INE has no
independent channel") was FALSE (the review found the channel); this report replaces it.

Commits on `pipeline-rebuild` (fix round 1, on top of 02205b5..2b8198a):
- `5c2c78c` M2: full INE conventional-sign mapping from the official legend (`sinais.jsp`,
  recorded fixture) — `//`→provisional, `*`→revised, `┴`→break, `“`→estimated, `§`→normal
  (quality caveat lost by decision), `…`→no-value (confidential); `o`, `∞`, `»`, `i`, `“E`
  reviewed but deliberately unmapped → raise.
- `456d36d` timeouts: `SourceSpec.timeout_s` (YAML under `sources:`, validated positive finite,
  default None), per-call `timeout=` on `Http.get`/`RequestsHttp` (None = client default; invalid
  values rejected), `INESource.fetch` forwards it and omits the kwarg when unset (older Http
  doubles with a 3-parameter `get` keep working); registry `ine: timeout_s: 300`.
- `a2ce708` I2: `NoVerifierRegistered(ValueError)` — `run_with_refetch` raises BEFORE any fetch
  when no verifier is registered (previously `verifier=None` slipped the identity check and
  crashed with AttributeError after a ~10 min fetch); `SourceSpec.verifiable: bool = True`
  machine marker; `SourceNotVerifiable` refuses a `verifiable: false` source even when a verifier
  is registered. No source is marked false today (`ine` explicitly true).
- `4162efc` I3: `LEGACY_SUSPECT_SCALE` in `ingest/legacy_import.py` quarantines legacy INE
  `exports_monthly.PT`/`imports_monthly.PT` rows 2005-01..2024-12 (inclusive) as legacy-only
  `suspect_unit_scale` (million EUR filed as EUR; live INE publishes EUR; registry unit stays
  `EUR` for live data; rows never rescaled, never served).
- `14f0aee` M1: INE attribution = authoritative Portuguese wording (terms page kept in
  `licence_url`; English variant retained as a YAML comment).
- `5efd6e3` C1: `ingest/verifiers/ine.py` — the independent verifier (below).
- `246325c` live smoke rewritten to run verified end-to-end; false "unverifiable" test assertions
  flipped.

Tests: `.venv-ci/bin/python -m pytest tests/ingest -q` → **660 passed, 2 deselected** (the two
live tests). Ruff (0.17.4, repo `ruff.toml`) clean on every touched file (pre-existing
F401/I001 in untouched files — `tests/conftest.py`, `test_verifier_eurostat.py`,
`ingest/verifiers/independence.py` — left alone).

## C1 — the independent channel and the verifier

`GET https://www.ine.pt/bddXplorer/htdocs/bddXplorer04.jsp?indOcorrCod=<varcd>&contexto=bd&lang=PT`
with header `Referer: https://www.ine.pt/` returns the full statistical table page in ~0.2 s
(a plain client without the header gets 302 + empty body — that 302 is what the first pass had
misread as "browser-only"). This is a different endpoint family AND a different format (a
server-rendered HTML table) from the collector's `pindica.jsp` JSON, showing INE's published
rendering: `,` decimal, space thousands separators, trailing zeros kept (`2,0` where the JSON
`valor` says `2`), the conventional sign appended to the figure (`5,6 &`), and the unit symbol in
the table header.

Selection protocol (derived live 2026-11-11, this fix round): the page form's hidden input
`xmlDocHidden` is a `Classificacoes` XML document — the indicator's dimensions and their category
trees with `selected` flags. To read a cell, set `selected='true'` only on the wanted period
category (matched by its PT label AND the `order` end-date, both must agree) and on the pinned
category of every other dimension — Dim2 = the `type='geo'` class, Dim3.. = the `type='dim'`
classes in ascending `order` — and send the whole form back as the GET query (12-185 kB URLs work;
Tomcat accepts them). The response is the table of exactly that cut.

- **Deep categories**: the shipped tree lacks CAE *divisions* for 0011889 (only sections B-E ship,
  `maxlevel=3` truncated). A missing `cod_categ` is selected by inserting one `<Categoria>` node
  as a direct child of the class's root category (`nivel` 2, `order` 999). Validated live against
  the JSON channel on divisions 08/10/35/38 (e.g. 10@2026-06: table `114,57` = JSON `114.57`;
  08@2026-06: `124,88` = JSON `124.88` fetched during recording). Injecting under a wrong deeper
  parent renders `x` dummy rows (found live; avoided) — the cut assertions make this fail-closed.
- **Assertions on the response** (anything odd raises → run fails, never a false pass): echoed
  selection equals the pinned cut per class; exactly one period offered/visible and it normalizes
  to the item's period via `spec.frequency`; exactly one matching table cell
  (row-dimension codes + period label in rows, dimension codes + period label + unit symbol in
  grid columns honouring rowspan/colspan); the table unit symbol equals the document `simbolo`
  and `potencia='0'`; the unit symbol maps fail-closed (`%`→`%`, `€`→`EUR`, `N.º`→`N.º`,
  `-`→`index_<base>=100` with the base year from the table title's `Base - 2021`); sign tokens
  are the reviewed set only (`&`,`//`,`*`,`┴`,`“`,`§`; a cell that is only `…`,`x` or `-` is a
  no-value cell → `observed_text=None`, i.e. "not found", a mismatch if sampled); thousands
  spaces kept verbatim in `observed_text` (`,` decimal — `ingest.verify` compares exact
  Decimals, Ruling AB, so `2` ≡ `2,0`).
- **evidence**: `ItemResult.evidence` = the raw selection-response HTML (kept in the raw store
  under `verify-ine/`), `evidence_url` = the full selection URL. The table's own period label (not
  the request) fills `ItemResult.period`.
- html.parser is NOT subclassed (the independence allowlist bans `super().__init__`/dunder
  attrs): the table substring is sanitized (footnote anchors and `Nota(s)` rows removed — the
  only constructs that break well-formedness there) and parsed with `xml.etree`; hidden inputs
  by template regex. Empirically, recorded pages contain only XML-native `&amp;` inside the
  table.
- Pacing: delegated to the injected `Http` — `RequestsHttp` throttles every request (≤1 req/s
  default); the verifier itself never sleeps so fixture tests stay fast. Requests: 1 indicator
  page per varcd + 1 selection per sampled item.

## Fixtures and cross-checks (all real, recorded 2026-11-11)

`tests/ingest/fixtures/ine/verify/`: 9 indicator pages + 20 selection responses (each ≤ 200 KB),
`MANIFEST.json` with per-case series/period/expected observation/provenance/cross-check note,
plus `sinais_PT.html` (official sign legend), `error_page_ora.html` (real INE 'Ocorreu um erro'
page for a malformed selection) and `home_no_referer.html` (the 302 destination without Referer).

Every recorded case was cross-checked: **20/20 agree** —
- 18 cases vs the collector's own recorded JSON fixtures (exact Decimal value + sign-mapped flag),
  including trailing-zero pairs (`140.3`/`140,30`, `2`/`2,0`), thousands-spaced EUR
  (`7 609 586 380`), a negative balance (`-31,0`), and a provisional cell (`5,6` + `&`);
- 2 vs live JSON fetches taken at recording time (CPI Continente 2025-10 = `2,32`; IPI division 08
  2026-06 = `124,88` — the deep-injection path);
- 4 additionally vs Eurostat SDMX 2.1 TSV (a third channel, this run): births 2024 = 84 642
  (Eurostat 84642), deaths 2024 = 118 396 (118 396), population 2024 = 11 387 222 (11 387 222),
  HICP 2025-10 = `2,0` (2.0).

## Live smoke (run once, 2026-11-11, f3nix)

`pytest tests/ingest/test_live_ine.py -m live -s` (deselected by default):
`run_with_refetch` over 5 series (a CAE division `ipi_seasonal_cae_10.PT` included, so the
injection path ran live) → **verified**, 1,399 written, 1 quarantined (the `x` IPI-division cell),
**served = 1,399**, verification sample 24/24 matched, 110-130 s total. Audit artifacts:
`live-audit.db` + `audit.json` + raw evidence under the session scratch dir; `replay_item` on
stored fields returns True for sampled items.

## What the fix round changed vs the first pass

- INE series are collected, verified and SERVED (the 41 active series; 1 quarantined `x` cell in
  the smoke scope). `registry/unverifiable.md` corrected — it now lists no source and explains
  the mechanism (`run_with_refetch` raises `NoVerifierRegistered` before fetching; a
  `verifiable: false` marker refuses outright). Owner decision #1 is moot.
- Legacy trade rows 2005-01..2024-12 are quarantined (I3), not imported as EUR: verified re-run of
  the real 246,162-row export into a fresh temp SQLite: **164,345 imported** (−480 vs the Task 8
  figure), quarantine **6,522 missing_unit + 6 non_numeric + 480 suspect_unit_scale**
  (exports 240 + imports 240, both exactly 2005-01..2024-12), 74,809 not_in_registry, served = 0,
  second run `n_imported = 0` (idempotent). Task 8 report amended.
- `ine.timeout_s: 300` in the registry; `INESource.fetch` uses it (the earlier concern "T17/18
  needs ≥300 s" is now resolved for fetch; the scheduler should read the same field).

## Verification semantics carried over from the first pass

- Token stays INE's `valor` ('.' decimal); the verifier compares numerically (Ruling AB) and
  additionally compares the unit symbol and the sign; `ind_string` stays in the raw payload and
  as the adapter's consistency check.
- 169/2,472 valued cells: `valor` drops trailing zeros vs the published string (`4`/`4,0`,
  `140.3`/`140,30`) — the numeric comparison absorbs it. Owner decision #4 unchanged.
- IPI `_35`≡`_D`, `_38`≡`_E` pairs untouched (owner flag). Registry units/ids/roles untouched.

## Decisions / notes for adapters 11-16 and T17-18

1. `run_with_refetch` fails fast: no registered verifier → `NoVerifierRegistered` before fetch;
   `verifiable: false` → `SourceNotVerifiable` even with a verifier. CLIs must register verifiers
   (`register_verifier(EurostatVerifier())`, `register_verifier(INEVerifier())`).
2. Sources must pass their registry `timeout_s` per call (pattern in `INESource.fetch`); the
   scheduler (T17/18) should construct/configure clients from it.
3. bddXplorer tables paginate nothing we use but every structural deviation raises — the verifier
   is deliberately strict; when INE changes a template the run fails loudly for review.
4. `sinais.jsp` descriptions are used verbatim in `ingest/flags.py`; the JSON channel's
   `sinal_conv_desc` for the newly mapped signs has never been observed live — a wording mismatch
   raises at parse, forcing review (observed vocabulary so far: `&`, `x`, `-`).
5. `§` maps to `normal` (quality caveat lost by design); `“E` (Eurostat estimate), `»` (foreseen),
   `o`, `∞`, `i` raise everywhere until first observation triggers a mapping review.

## TDD evidence — fix round 1

Each commit was written tests-first: failing tests were added and run before the implementation
(M2 sign tests RED 7 failed → GREEN; timeouts RED 11 failed → GREEN; I2 RED (import error on
`NoVerifierRegistered`) → GREEN; I3 RED 2 failed → GREEN; C1 was built from live-channel
reverse-engineering, then its 18 verifier tests ran RED (fixtures/verifier absent) → fixtures
recorded live → GREEN 18/18, subprocess independence included). The clean recorded pipeline run
ends `verified` with served rows; the tamper test fails verification with exactly
`value differs` on births 2025.

## First pass (superseded narrative)

The first pass probed channels and concluded INE had one machine-readable channel; its probing
missed the Referer-header requirement on the indicator table. Everything else from the first pass
still stands: adapter (`pindica.jsp` op=2, `valor` tokens, sign mapping, dim-pinning
`<varcd>:Dim2=..` native codes), registry INE section (42 series: successor HICP/CPI base-2025
codes, Ruling Y unemployment primary, demography trio), the full-scope live parse of all 41
active series (17-45 s per request, trade 170-236 s, 9 `x` no-value cells), licence
(CC BY 4.0, `redistribution_ok: true`).
