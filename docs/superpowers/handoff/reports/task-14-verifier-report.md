# Task 14 Part B — independent FRED verifier (report)

Part B of the Task 14 brief: the independent verification channel for source `fred`
(Part A: collector + registry + fixtures, committed by the controller). Branch
`pipeline-rebuild`; controller owns HANDOFF/ledger/brief.

## Channel decision

- **Collector** (Part A): FRED JSON API on `api.stlouisfed.org` with `api_key` query auth
  (`/fred/series` + `/fred/series/observations`; values are JSON strings, `.` = missing).
- **Verifier**: the **server-rendered data-table page** of the public site, keyless:
  `https://fred.stlouisfed.org/data/<native_code>` — a different host family, endpoint and
  format, owned by FRED's publication UI. One page carries BOTH surfaces an item's decision
  needs: the metadata table (`aria-label="metadata - <Title>" name="<Title>"`) and the
  observations table (`id="data-table-observations"`, header exactly DATE/VALUE, rows
  `<th scope="row">YYYY-MM-01</th><td>exact token</td>`).
- **Rejected**: the `fredgraph.csv` export (binary numeric tails differ from the API on
  10/12 series — controller preflight) and the JSON API itself (it is the collector's own
  channel). Neither is read by the verifier.

## What was built (all new files; no edits to Part A source/registry/fixtures, handoff,
ledger or brief)

- `ingest/verifiers/fred.py` — `FredVerifier(source_name="fred")`, ~330 lines. Own
  `html.parser` scanner (no `super()`/`__init__`/dunder — Ruling-S compliant), no regex
  scraping of numbers. Fail-closed: exactly one metadata + one observations table, no
  nesting, no markup inside cells, unique metadata keys (reviewed 10-row set), Series ID ==
  native code, Title/name/`h1#data-table-title` triple agrees, Source `International Monetary
  Fund` + Release `Primary Commodity Prices (Not a Press Release)` + `Global price of ...`
  title (the reviewed WORLD IMF concept), `Monthly`→M == spec.frequency,
  `Not Seasonally Adjusted`→NSA == spec.seasonal_adjustment, Units byte-match the registry
  (**asserted, never copied** — `observed_unit` is the HTML label), Date Range endpoints ==
  first/last row dates, month-first real dates strictly ascending with no duplicate periods,
  `.` is the only reviewed missing marker (→ honest `observed_text=None`; a period absent
  from the table likewise returns None, never invented), unknown VALUE token shapes raise.
  `observed_flag=None` (no status surface on this channel), `observed_decimal="."`.
- **Evidence envelope** (Ruling R/G7): one `fred-table-evidence`/v1 JSON envelope per item
  bundling the exact wire record — final URL, actual HTTP status, full body base64 — because
  metadata AND values come from the SAME response. `evidence_url` = page URL. Offline replay
  path: `read_table_page(body, code, spec)` re-derives unit+values from archived bytes with
  no HTTP (tested).
- `tests/ingest/fred_verifier_fixtures.py` — `TableFixtureHttp` (serves the recorded table
  pages; the channel is keyless: any query param fails, so no api_key can leak into the
  verifier channel).
- `tests/ingest/fred_verifier_entry.py` — subprocess entry for the runtime independence
  guard.
- `tests/ingest/test_verifier_fred.py` — 33 tests.
- `tests/ingest/test_live_fred.py` — marked `live` (deselected by default), env-key only.
- This report.

## Tests (TDD: written against the contract, then minimal green)

`tests/ingest/test_verifier_fred.py`, 33 passed (16.5 s, all offline, recorded originals):

- **Pins/coverage**: 9 named (series, period) pins read the exact publisher cell token
  (trailing-zero padding preserved) from the archived pages; all-12 coverage reads first and
  last month of every active series (24 items, 12 fetches — one `/data/<CODE>` per series per
  check); units asserted read-from-HTML. Active ids/codes come from the real registry via the
  shared test helper (`active_specs()`), never a hardcoded mapping.
- **Fail-closed drift** (mutations built in-test only, anchors asserted unique): non-2xx,
  error page without the reviewed tables, duplicate metadata/observations table, wrong Series
  ID, unknown/drifted Units (both directions incl. registry-side), Frequency/Seasonal
  Adjustment drift, Source/Release/Title concept drift, duplicate period, extra status
  column (body row and header), non-month-first/malformed dates, Date Range drift, truncated
  page (missing closing tag), nested table, unreviewed VALUE tokens (`N/A`, empty, grouping,
  exponent, `NaN`, multi-dot; parametrized x6); `.` marker → honest None; missing period
  (pre-1992 and interior gap) → None.
- **Registration**: `register_verifier` passes the static allowlist (also with
  `ingest.sources.fred` loaded in-process); `assert_verifier_independent` subprocess runs the
  fixture check with `collectors`, `ingest.flags`, `ingest.sources` blocked — real run, no
  source imports.
- **Through the real pipeline** (recorded 48-response fixture set): clean run of all 12
  series → 5004 written / 1728 `non_numeric` quarantine (the API's `.` cells) and
  `verified`; served stays **0** (licence gate: `redistribution_ok=false`, IMF grant
  unconfirmed); a tampered collector token on aluminum 2026-09 ends
  `failed-verification` with note `value differs`, served 0; `run_with_refetch` with the
  registered verifier (host-routed shared Http; no api_key on the table host) → verified,
  provenance asserted (observations from `api.stlouisfed.org/fred/series/observations`,
  key-free urls); every sampled item's `verification_item` evidence reloads from the raw
  store under `verify-fred/<sha>` and replays offline to the exact page bytes, unit and
  value. Regression: `test_source_fred.py` still 34 passed. `ruff check`: clean.

## Live test (not run here — no network by dispatch; controller runs from f0nix egress)

`tests/ingest/test_live_fred.py -m live -s`, `FRED_API_KEY` from env only (skip otherwise,
never a file). All 12 active series, `RequestsHttp(throttle_rps=1.0, timeout=120.0)`,
`max_attempts=1`, `size=120`, registered verifier, self-empty registry via the pytest
monkeypatch fixture only. Asserts `verified`, 417 obs/series 1992-01..2026-09, served 0,
verification (120, passed=1), quarantine non_numeric x1728, and prints states/counts plus the
offline replay count of archived evidence envelopes.

## Remaining gates (never declared complete by this task)

- Controller review, then the fresh-egress live run from f0nix.
- IMF redistribution grant unresolved: source stays withheld (served=0) regardless of
  verification.
- Task 17 CLI registration wiring is outside Task 14.
