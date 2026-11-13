# Task 13 - CSV export language configuration (implementer report)

2026-11-12, worktree `~/projects/prumo-pipeline`, branch `pipeline-rebuild`.
Scope: scoped World Bank CSV export **language configuration** with strict evidence identity,
per the controller's Task 13 continuation brief. **Task 13 remains OPEN**: this is an
offline code/test/fixture package enabling the Spanish independent channel; the full live
all-930 gate is the controller's next step.

## Commits (SHA range `d198dc6..bf827f8`)

| SHA | What |
|---|---|
| `3ebe260` | tests: genuine Spanish-locale World Bank CSV export fixtures |
| `2aea67b` | ingest: World Bank CSV verifier behind a strict per-locale export contract (refactor, en unchanged) |
| `bf827f8` | ingest: admit the Spanish locale of the World Bank CSV export channel (+ tests) |
| (this file) | docs: Task 13 CSV language implementation report |

Refactor-first per AGENTS.md: the locale contract landed while the allowlist still held only
`en` (all 25 pre-existing verifier tests green), then `es` was admitted.

## What changed

### `ingest/verifiers/worldbank.py` (the only production-code file touched)
- `CSV_LANGUAGES: dict[str, (url_template, localized_data_source_title)]` is the **exact
  allowlist** `{en, es}` (`2aea67b` shipped en-only; `bf827f8` adds es). `CSV_URL` kept as the
  English template for backward compatibility.
- `WorldBankVerifier(csv_language="en")` constructor: unknown languages (incl. `EN`, ``,
  `pt-BR`, `en,es`) raise `ValueError` at construction, **before any request**. Default `en`
  = original behavior (`test_default_language_remains_english` pins it; all pre-existing
  callers/tests unchanged, incl. `tests/ingest/test_live_worldbank.py`).
- Per (code, locale) full-name member identity: `API_<CODE>_DS2_<lang>_csv_v2_<rev>.csv` +
  both metadata companions, now `fullmatch`-ed, and **all three members must share ONE
  revision**; a split revision or crossed-locale archive is identity drift (fail closed).
  Previously the member check was prefix-only. The recorded genuine English fixtures (three
  archives, revs 265656/264687/260126, each internally consistent) satisfy the stricter rule.
- The localized Data Source title is checked against the chosen locale (`es` =
  'Indicadores del desarrollo mundial'); column labels, `Data Source`/`Last Updated Date`
  keys remain the pinned English set (the exporter does not localize them, per the genuine
  bytes). The per-row Indicator Name check stays the language-agnostic
  one-name-across-rows rule (es rows carry e.g. 'Crecimiento del PIB (% anual)').
- No fallback, no retry, no request rewriting, no collector/registry/licence/CLI/transport
  changes. Evidence envelope format unchanged ('worldbank-csv-evidence' v1; exact ZIP bytes,
  final URL, actual HTTP status from the received HttpResult).

### Fixtures (genuine evidence, byte-for-byte)
Copied unmodified from the 2026-11-12 recovery probes; sha256 verified before and after copy:

| Fixture | Indicator | Final URL | Status | Bytes | SHA256 (prefix) |
|---|---|---|---|---|---|
| `csv-es-sl-uem-totl-zs.zip` | SL.UEM.TOTL.ZS | `https://api.worldbank.org/v2/es/indicator/SL.UEM.TOTL.ZS?downloadformat=csv` | 200 | 42,458 | `d0533f8f` |
| `csv-es-ny-gdp-mktp-kd-zg.zip` | NY.GDP.MKTP.KD.ZG | `https://api.worldbank.org/v2/es/indicator/NY.GDP.MKTP.KD.ZG?downloadformat=csv` | 200 | 135,776 | `0054931d` |

MANIFEST.json entries carry sanitized request metadata only (url/status/content_type/bytes/
sha256); **ephemeral Cloudflare `Set-Cookie` auth and trace headers were deliberately NOT
recorded** (they are not evidence). Full request accounting lives in the controller recovery
manifests (scratch `prumo-task13-unemp-recovery/manifest.json` - with sibling raw body - and
`prumo-task13-recovery-controller/manifest.json`); the committed fixtures + hashes are the
durable record. Both ZIPs: 3 members `DS2_es_csv_v2_13960` / `DS2_es_csv_v2_1937` (shared rev),
title 'Indicadores del desarrollo mundial', English column labels, no unit/status cell
surface, '.'-decimal tokens.

### Tests (20 new, all in `tests/ingest/test_verifier_worldbank.py`, entry in
`tests/ingest/worldbank_verifier_entry.py`, es-aware `worldbank_verifier_fixtures.py`)
- 7 pinned Spanish token cases (≥5 required): exact tokens incl. negative
  (`-8.20463159324387`), cross-checked by the controller live against API v2 JSON, 54/54
  registry series per indicator; empty 1960 cell → honest not-found (`None`), evidence still
  archived.
- Identity/fail-closed: unknown language at construction; en→es and es→en crossed ZIPs;
  English title under Spanish member names (no semantic fallback); split member revisions;
  foreign `DS2_fr_` infix; non-2xx (502); single-request proof (no retry/fallback) on
  failure; canonical-year period guard.
- Through `verify_run` on a scripted source carrying the **genuine es-channel tokens**
  (24 observations, 4 series): clean run verifies (24/24, served), tampered value fails with
  exact expected/observed strings, tampered geography row fails 'not found', zero served.
- Evidence: archived envelopes decode offline to the exact es FINAL URL, actual status 200 and
  byte-identical ZIP; `replay_item` true for every item; 2 content-addressed payloads.
- Registration (`register_verifier`) passes the static allowlist; new
  `run_es` entrypoint exercises the subprocess independence guard
  (`assert_verifier_independent` with `ingest.sources` blocked).

## Verification performed
- RED: 20 es tests failed before the es admission (TypeError/contract ValueError);
  the refactor commit kept the 25 pre-existing tests green (then 28 passing incl. the three
  construction-level guards).
- GREEN: `tests/ingest/test_verifier_worldbank.py` → **45 passed**.
- Full suite: `.venv-ci/bin/python -m pytest tests -q` → **929 passed, 5 live deselected,
  1 warning in 163.16 s** (baseline was 909 passed; +20 new).
- `.venv-ci/bin/ruff check` on all four touched Python paths → clean.
- GitNexus (index was up-to-date at d198dc6): `impact WorldBankVerifier` LOW, 1 direct
  importer (entry module); test-module consumers confirmed by grep (impact graphs do not index
  them); `detect-changes` run before each commit (4 files, medium risk, no unexpected blast).
- Fixture byte identity re-checked against MANIFEST sha256 after copying.

## Deferred limits / explicit non-claims
- **Task 13 is NOT complete.** Not done here (controller-owned): the all-930 live blind
  verification re-run using `WorldBankVerifier(csv_language="es")` for
  SL.UEM.TOTL.ZS + NY.GDP.MKTP.KD.ZG against the fresh JSON run, plus scoped independent spec
  and quality re-reviews of this diff; live gate stays blocked until then.
- Only the 2 es indicators are backed by genuine archives; a general es sweep was not probed
  and is not assumed available.
- No retries/transports/timeouts/CLI changes; no registration wiring for the es verifier in
  any CLI (Task 17 scope); no registry/collector/licence changes; nothing deployed or pushed
  to main.
- Existing en timeout behavior of the publisher's /en/ routes is unchanged; the es channel's
  observed 200s are route/time dependent (Cloudflare) per the recovery evidence - the live
  gate will re-probe from f0nix.
