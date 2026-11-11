# Task 12 Phase A — independent QUALITY review (REN + serving licence gate)

Reviewer: fresh read-only subagent (independent of implementer and spec reviewer).
Base 731ef4d, HEAD 34abed5, branch pipeline-rebuild. Read implementer report
(`task-12-ren-report.md`), spec review (`task-12-ren-spec-review.md`) and brief; reviewed diff,
tests and fixtures on bytes; ran adversarial probes from `/home/joao/.hermes/cache/scratch/
prumo-task12-review/` (probe_source.py / probe_verifier.py / probe_gate.py, scratch DBs only).
No code/test/registry/ledger/handoff edits, no commits/push/deploy/outbound. Controller's dirty
`progress-ledger.md` and untracked briefs untouched (only this report added).

## Verdict: REQUEST_CHANGES

One Important defect (F1, JSON primitive-type blindness breaks the claimed fail-closed shape
contract), one Minor guard bug (F2). Everything else probed holds; spec review's four minors
confirmed on bytes (F5–F7). Bounded fix: `_token` type tagging + a handful of cheap tests.

## Execution evidence (fresh, this session)

- `.venv-ci/bin/python -m pytest tests/ingest/test_licence_gate.py tests/ingest/test_source_ren.py
  tests/ingest/test_registry_ren_units.py tests/ingest/test_verifier_ren.py -q` → **67 passed**.
- `.venv-ci/bin/python -m pytest tests -q` → **818 passed, 4 deselected, 1 warning** (matches
  implementer/spec-review claim; the 1 warning is baseline — pytest.ini `--disable-warnings`,
  live marker registered, deselect works).
- `ruff check` on all 10 changed/new code+test files → clean. All 6 commits authored joaompfp;
  diff touches only the 24 listed files; zero DGEG/ERSE code edits; no controller files staged.
- Fixture forensics: all 8 fixture sha256 == MANIFEST.json. Cross-channel pins re-derived from
  bytes myself: API==CSV for CONSUMO 4442, Hídrica 645, Ciclo Combinado 510, SALDO IMPORTADOR
  1616, PT 'Preço Médio' 143.9; CSV-only 2020-06 CONSUMO 3604; API-only 2010-01
  SALDO_IMPORTADOR `-263` (negative token). Discovery alt bodies show the day-pinned running-month
  balance request answers the latest COMPLETED month ('out 26') — so the verifier's pinned
  header-month check is load-bearing, and it works.
- RED basis confirmed independently (probe C5): a denied-source legacy row written under a real
  0001–0004 DB IS served by the old view; after `open_db` applies 0005 it is withheld, with the
  observation row intact. The 0005 tests therefore genuinely couple to the migration.

## Requirement sweep (all hold unless a finding cites them)

14 active monthly PT series w/ real native codes (13 GWh balance + 1 EUR/MWh price — registry diff
checked line by line, `verifiable` is an existing SourceSpec field, not invented). Explicit
`culture=pt-PT&year&month` always; undated requests archived as answering wrong-vintage data
(`api/balance-pt-noparams.body` 200 with data). Default = last 13 completed months (running month
excluded; year-boundary tests pass). Fail-closed on shape/dates/identity/duplicates/unknown status
fields/non-2xx at BOTH the adapter and the pipeline layer. `RawRow.response_index` provenance with
pipeline out-of-range guard. Verifier is a genuinely different channel (portal CSV export, own
host family), blind inputs only, value+period+GWh unit read from CSV header/rows (request echo
refused on mismatch — B5/B7 probes raise), PT/ES geography pinned for the market; `observed_unit=
None` honestly where the market CSV has no unit, `observed_flag=None`, no collector imports
(duplicated label map by design, registration + subprocess independence tests pass). Cache per
chart+month. Evidence = exact CSV bytes (sha256→raw store) + final URL per item; offline recovery
+ `replay_item` over all 14 items pass. Licence false → internally verified, served=0 (fetched AND
legacy, `legacy_served='1'` included); revoke/reapprove immediate via normal sync, history
byte-identical (probes C2/C4/C5 + tests); mixed sources serve only the allowed side; migration
idempotent on reopen (C1); missing `legacy_served` row fails closed (C2). Prices year surface is
absent by nature (declared honestly; CSV verifier pins year from evidence). DGEG untouched/OPEN.

## Findings

**F1 — Important — JSON string tokens silently accepted as number tokens; verbatim-token
invariant breaks silently.** `ingest/sources/ren.py:141` (`_loads`) combines
`parse_int=str/parse_float=str` with `_token` (147–152) checking only `isinstance(v, str)` +
regex, so a JSON string is indistinguishable from a JSON number. Repro (probe_source.py A1/A2 —
scratch, read-only): replace `{"monthly_Accumulation":4442,...}` with
`{"monthly_Accumulation":"04442",...}` in the recorded 2026-09 balance payload → `parse()` accepts
it and `RawRow.value_raw == '04442'`. That token would be stored verbatim as the publisher's
number and would still VERIFY: exact Decimal equality makes `04442 == 4442` a match against the
CSV channel, so neither layer detects the type flip. This contradicts the module's own contract
("balance: ... {"monthly_Accumulation": <number>}", docstring l.25; "Raises on: ... non-numeric
... tokens", l.39–40) and the brief's "reject malformed structures"; a test named
`test_non_numeric_value_token_raises` pins 'abc' but the quoted-number axis is untested. The same
gap applies to every `_token` call in `parse_prices_body` (PT/ES metrics, capacity, scalars).
NaN/-Infinity/null/bool/exponent probes DO raise (A4, A3) — only the str/number boundary leaks.
Fix (bounded): tag real JSON numbers, e.g. `class _Num(str)` with `parse_int=
lambda s: _Num(s), parse_float=lambda s: _Num(s)` (plus `parse_constant` left raising via the
regex) and require `type(v) is _Num` in `_token`, coercing to plain `str` for `RawRow`; add
quoted-token tests for balance and prices.

**F2 — Minor — interior blank-row guard fails open on truly empty CSV lines.**
`ingest/verifiers/ren.py:126–132`: `rows = [row for row in csv.reader(...) if row]` removes
zero-cell (empty) lines anywhere BEFORE the interior-blank check, so the guard only fires on
comma-filled blank rows. Repro (probe B9-fixed): insert `\r\n` before the `Hídrica 1` row of the
recorded balance CSV → accepted, observed 4442; the doc comment claims an interior blank "is an
unreviewed table break". Low impact (labels/header pinned; a stacked second table still fails via
the duplicate-mapped-label check) but the stated guarantee is not what the code does. One-line
fix: run the blank-suffix analysis on the unfiltered `csv.reader` output (treat `row == []` as
blank like all-empty cells) and only then filter.

**F3 — Minor — `parse()` trusts response params over the constructed range; gaps silent.**
Probe A5: feeding a response whose params say `2019-05` is accepted with only 2026-09 requested
(row period_raw `2019-05`); probe A6: two requested months, one response → rows silently halved.
Not reachable through production `fetch()` (it yields exactly one response per (endpoint, month)
or raises, and the pipeline fails mid-stream exceptions as `failed-fetch`), so this is
defense-in-depth, not a live hole: assert `period ∈ self.periods` and
`seen_periods == requested` in `parse()`, or document the trust contract.

**F4 — FYI — revision events never fire for denied sources (side effect of the gate).**
`pipeline._write` compares against `db.served_fetched_values`, which reads the gated view; probe
C3: denied source token 10.5→10.6 across two verified runs → 0 `revision` events (allowed source
same change → 1). Rows/history are kept; this is consistent with the pipeline's "revision vs
currently served" definition, but the audit stream loses publisher-restatement visibility for
legally withheld data (today: REN's 14 series only; fred/oecd are also denied but have no
adapters). Recommend documenting as a known consequence or a follow-up comparing against the
latest verified fetched vintage instead (engine concern, outside 0005's contract).

**F5 — Minor (coverage) — verifier malformed-CSV guards untested.** The guards exist and all my
probes raise (B1 HTML `<!DOCTYPE`/`<html`/uppercase with whitespace, B2 binary non-UTF-8, B3
empty/header-only, B4 status 500 with valid body, B6 thousand-separated value, B8 geography
rename) — but no test feeds them; spec review's minor #2 stands, and F2 shows an untested guard
that is in fact half-broken. Add HTML/garbage/interior-blank cases.

**F6 — Minor (carried, spec review #1) — per-item evidence omits HTTP status.** Exact bytes +
final URL persisted; status absent (no `verification_item` slot; non-2xx raises before evidence
exists, so persisted evidence structurally implies 2xx; fixture statuses live in MANIFEST.json;
INE precedent identical). Blocking only if the controller reads the brief's "…body, final URL
and status" as binding per item — then it's a framework slot change, not REN-specific.

**F7 — Docs minors (spec review #3/#4), confirmed on bytes:**
(a) `completed_months` docstring (`ingest/sources/ren.py:96`) says 2026-11-11 → `['2025-11',…]`;
actual first element is `2025-10` (tests pin correctly) — off-by-one text.
(b) `ingest/verifiers/ren.py:26` claims market CSV "columns 3/4 [are] the previous year's" —
the archived bytes have header `,setembro,,2026,` over those columns (current-year block,
PT 74.08 vs month 143.9), and the code itself pins `head[3] == str(year)`; behavior right,
audit-facing comment wrong.
(c) EUR/MWh justification: the market page narrative body exists only in the expiring scratch
discovery archive (`…/prumo-task12-ren-discovery/portal/mercado.body`, €/MWh ×8 present today);
committed evidence is the quote+URL in `tests/ingest/test_registry_ren_units.py:8–11`. Acceptable
because the market CSV exposes no unit and it is never compared — but "absent permanent market
unit evidence" stands; suggest committing the page body alongside the CSV fixtures.

## What I deliberately did NOT flag

- Balance-CSV geography is request-pinned only (no geography surface exists in that export;
  `country=PT` is an echo). Not invented-ok by design: values cross-check the PT API and the
  header/unit/period all fail closed. Market geography IS evidence-read (`,PT,ES,PT,ES`).
- `type`/`month-key`/capacity/scalar type strictness, unknown-surface rejection, duplicate-key
  JSON hook, BOM-less or quoted-label CSV tolerance, day-pin vs month-span request shapes —
  all probed or code-read as correct fail-closed choices.
- Live suite intentionally not re-run (controller re-running; no redundant network). Its claimed
  numbers are internally consistent with the test's own assertions (182 = 14×13, 26 raw fetches,
  served=0) and the offline-replay assertions are exercised by non-live tests.

## Suggested controller fix batch (bounded)

1. F1 `_Num` tagging + quoted-token tests (balance + one price metric). **Blocking.**
2. F2 unfiltered blank-row analysis + interior-blank test. Cheap, same pass.
3. F5 HTML/garbage CSV tests. Cheap, same pass.
4. F7 docstring fixes; consider committing `mercado.body` as durable unit evidence.
5. F3/F4: decide document-vs-fix; neither should block Phase A after 1–4.
