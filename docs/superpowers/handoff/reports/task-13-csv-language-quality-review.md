# Task 13 - Spanish CSV language support: independent scoped quality review

2026-11-12. Read-only quality re-review of `git diff d198dc6..5e4dcf7` on branch
`pipeline-rebuild` in `/home/joao/projects/prumo-pipeline`, after spec review PASS
(`reports/task-13-csv-language-spec-review.md`). Own probes only; implementer self-report
not relied upon. Offline, targeted tests only (controller owns full suite + live 930 gate).
No code/HANDOFF/ledger edits; this report is the only file written.

**Verdict: APPROVED (scoped).** 0 Critical, 0 Important, 2 Minor + 1 nit. This approval
covers only the diff's code/test/fixture quality. **Task 13 as a whole is NOT accepted here:**
the all-930 live gate, full-suite run and HANDOFF/ledger state remain controller-owned.

## Independently re-verified (own probes, not the implementer's)

1. **Scope discipline** - 8 files, 4 commits (`3ebe260` fixtures, `2aea67b` strict contract
   en-only refactor, `bf827f8` es admission + tests, `5e4dcf7` report). Zero diff in
   `ingest/sources/`, `ingest/verifiers/independence.py`, `registry/`, CI, deps.
2. **Fixtures genuine & pinned** - own sha256: `csv-es-sl-uem-totl-zs.zip` 42,458 B
   `d0533f8f…`, `csv-es-ny-gdp-mktp-kd-zg.zip` 135,776 B `0054931d…` - both = MANIFEST.json
   pins, both ≤200 KB, status 200, `/v2/es/` final URLs recorded. Own ZIP decode: exactly 3
   members each, one shared revision per archive (`DS2_es_csv_v2_13960` / `_1937`), row 0
   `["Data Source","Indicadores del desarrollo mundial",""]`, column labels the pinned
   English set, `Last Updated Date` 2026-11-11. Own token reads from the genuine bytes match
   the test pins (PRT 2025: `6.164` unemployment, `1.86448007464475` GDP growth).
3. **Contract behavior** - own run `tests/ingest/test_verifier_worldbank.py`:
   **45 passed in 7.51 s** (baseline at `d198dc6`: 25 tests; +20 new, matches claim). Covers
   construction-time rejection (`fr`,`EN`,`","pt-BR"","en,es"`), crossed-locale ZIPs both
   directions, English-title-under-es-members (no semantic fallback), split revisions,
   foreign `DS2_fr_` infix, 502 fail-closed, single-request proof (no retry/fallback,
   `http.calls` asserted), canonical-year guard, default-en backward compat,
   `register_verifier` allowlist, subprocess independence guard on `run_es`, tampered value →
   `failed-verification` with exact expected/observed strings and 0 served, relabelled `PRT`→
   `XXX` row → not-found, offline evidence recovery (exact es URL, actual status 200,
   byte-identical ZIP, 2 content-addressed payloads, `replay_item` true ×24).
4. **Lint** - `.venv-ci/bin/ruff check` on all four touched Python paths: clean.
5. **Blindness / integrity** - `check()` reads only `item.spec.native_code`, `item.period`,
   `item.series_id`; value compare stays in `verify_run` (exact Decimal). `_envelope` records
   final URL + ACTUAL status from the received `HttpResult` + raw ZIP bytes (base64);
   schema/version unchanged (`worldbank-csv-evidence` v1). No transforms, rounding,
   zero-filling, or empty-cell suppression (empty 1960 → honest `observed_text=None`).
6. **Default unchanged / pre-existing vs new** - the only behavioral tightening is the member
   check: prefix-only → `fullmatch` + one-shared-revision. The three genuine en fixtures
   (revs 265656/264687/260126, each internally consistent) still satisfy it;
   `WorldBankVerifier()` = original en path, pinned by `test_default_language_remains_english`
   and the 25 kept tests incl. `test_live_worldbank.py` (constructor call site unchanged).
7. **Own adversarial runtime probes** (module imported in `.venv-ci`):
   - P2: mutating `CSV_LANGUAGES["en"]` after construction does NOT retarget an existing
     instance (URL/title snapshotted in `__init__`). Good.
   - P3: setting `v.csv_language = "en"` on an es instance post-construction (URL/title stay
     es, patterns become en) fails closed on member identity against the genuine es ZIP. Good.
   - P1/P4: findings M1/M2 below.

## Findings

### Critical
None.

### Important
None.

### Minor

- **M1 - the "exact allowlist" is a plain mutable module dict.** Probe P1:
  `CSV_LANGUAGES["fr"] = ("https://evil.example/{code}", "x")` then
  `WorldBankVerifier(csv_language="fr")` **succeeds**. The module docstring sells this as the
  security boundary ("never a runtime parameter"). Impact is bounded - injection requires
  in-process code execution (same trust domain as editing the file), instances snapshot at
  construction (P2), and all real callers pass literal strings - so this is defense-in-depth,
  not a reachable vulnerability in scoped usage. A `types.MappingProxyType` wrap (or a frozen
  tuple structure) would make the documented guarantee true at ~2 lines' cost.
- **M2 - no test pins the allowlist key set.** Probe P4: zero test references to
  `CSV_LANGUAGES`. A future commit adding a locale (even a careless/unreviewed one) leaves the
  whole suite green. One assertion (`sorted(CSV_LANGUAGES) == ["en", "es"]` in the
  construction-rejection test) would make the explicit-review contract executable.

### Nit / FYI (no action needed)

- `_member_patterns(...) -> tuple`: loose annotation; `tuple[re.Pattern, ...]` would document
  the triple. Ruff is clean; cosmetic only.
- `CASES_ES` is duplicated between the test module and `worldbank_verifier_entry.py`. This is
  deliberate (the subprocess independence entry must be self-contained); both copies assert
  against the same genuine fixture bytes, so drift between copies is caught. FYI.
- `test_es_verifier_registers_and_passes_allowlist` mutates the global verifier registry -
  identical pattern to every other verifier module (`bportugal`/`eurostat`/`ren`/`ine`), the
  only later worldbank consumer in-file is the fresh-subprocess guard, and the full suite
  placement follows the pre-existing convention. No new isolation hazard. FYI.

## Not claimed / controller-owned

Full-suite run, the all-930 live verification with `WorldBankVerifier(csv_language="es")`
from f0nix for SL.UEM.TOTL.ZS + NY.GDP.MKTP.KD.ZG, and Task 13 completion/HANDOFF/ledger
transitions. The implementer's "54/54 live JSON-vs-es cross-check" remains controller-pending
evidence, as the spec review already noted.
