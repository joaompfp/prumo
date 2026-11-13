# Task 13 - Spanish CSV language support: independent scoped spec review

2026-11-12. Read-only review of `git diff d198dc6..5e4dcf7` on branch `pipeline-rebuild`
in `/home/joao/projects/prumo-pipeline`, against design spec §6b, rulings J/N/O/R/AC and the
scoped contract (backward-compatible `WorldBankVerifier(csv_language='en')` + explicitly
configurable `'es'` same-publisher per-indicator CSV ZIP; strict en/es identity; exact tokens;
no fallback/retry/rewrite; archived original bytes/final URLs/actual statuses; collector,
channels, registry and licence untouched). Offline only; no networking, no code edits.
Skeptical read of `reports/task-13-csv-language-implementation.md` included.

**Verdict: PASS.** No spec or ruling violation found in the diff. Task 13 remains NOT complete
by design: the all-930 live gate is controller-owned and correctly not claimed.

## Independently verified (not taken from the implementer report)

1. **Diff scope** - 8 files only: `ingest/verifiers/worldbank.py`,
   `tests/ingest/test_verifier_worldbank.py`, `worldbank_verifier_fixtures.py`,
   `worldbank_verifier_entry.py`, `fixtures/worldbank/MANIFEST.json`, the 2 es ZIPs, and the
   report itself. Zero diff in `ingest/sources/`, `ingest/verifiers/independence.py`,
   `registry/`, requirements, CI (collector unchanged; no allowlist/registry/licence/channel
   widening). Baseline test count 25 → 45 (+20 new, as claimed).
2. **Fixture genuineness by hash chain** - re-computed SHA256 of both committed ZIPs:
   `d0533f8f…` (`csv-es-sl-uem-totl-zs.zip`, 42,458 B) and `0054931d…`
   (`csv-es-ny-gdp-mktp-kd-zg.zip`, 135,776 B); both ≤200 KB and = MANIFEST pins. Controller
   recovery evidence in scratch (`prumo-task13-unemp-recovery/raw/r4-f0nix-es/…body`,
   `prumo-task13-recovery-controller/probe-2.body`) is **byte-identical** (same sha256) with
   recorded actual HTTP 200, correct final `/v2/es/` URLs, `application/zip`, matching
   Content-Disposition revision numbers (13960/1937). Not invented/user-supplied bytes.
   MANIFEST entries carry only file/url/status/content_type/bytes/sha256/note - the Cloudflare
   `Set-Cookie`/trace headers exist only in the scratch manifests, confirming the sanitization
   claim.
3. **Archive shape/identity** - my own ZIP decode: each fixture has exactly 3 members
   `API_<CODE>_DS2_es_csv_v2_<rev>.csv` + both Metadata companions, one shared revision per
   archive; row 0 is `["Data Source","Indicadores del desarrollo mundial",""]`; column labels
   remain the pinned English set; no unit/status surfaces.
4. **Exact tokens** - all 8 pinned `CASES_ES` tokens and the full 24-token `ES_TRUTH` table
   re-read from the genuine archive bytes: 0 mismatches, including negative
   `-8.20463159324387` and empty-cell 1960 = `''` (not-found semantics, never zero-filled).
   Spot-checked unique country rows (PRT/ESP/GRC present once each).
5. **Contract behavior by test run** - `tests/ingest/test_verifier_worldbank.py` run fresh:
   **45 passed in 7.56 s**. This exercises: unknown languages (`fr`, `EN`, ``, `pt-BR`,
   `en,es`) rejected at construction; en→es and es→en crossed ZIPs fail closed; English title
   under es members fails (no semantic fallback); split member revisions fail; foreign
   `DS2_fr_` infix fails; non-2xx (502) fails; single-request proof (no retry/fallback,
   `http.calls` asserted); canonical-year period guard; default `en` backward compatibility;
   `register_verifier` allowlist pass; `assert_verifier_independent` subprocess guard on the
   es entrypoint; tampered value fails the run through the real `verify_run` gate
   (`failed-verification`, exact expected/observed strings, 0 served); relabelled geography
   row fails 'not found'; archived es envelopes recover offline (exact URL, actual status 200,
   byte-identical ZIP, 2 content-addressed payloads) and `replay_item` is true for all 24.
6. **Production code read** - `CSV_LANGUAGES` is a two-entry compile-time allowlist
   (`en` original template kept as `CSV_URL`); member identity is `fullmatch`ed per
   (code, locale) with one shared revision; title check is locale-pinned; no transforms,
   rounding, fallbacks or request rewriting anywhere in the diff. Ruling J (tokens as str),
   N/O (identity fields always compared; blind items only), R/AC (exact bytes + final URL +
   actual status in the versioned envelope, offline recovery) all hold.
7. **Lint** - `.venv-ci/bin/ruff check` on all four touched Python paths: all checks passed.

## Observations (non-blocking)

- The report states the es tokens were "cross-checked by the controller live against API v2
  JSON, 54/54 registry series per indicator". This review is offline: no committed/offline
  artifact of that JSON-vs-es 54/54 cross-check ships in this package (scratch manifests
  record the probes themselves, not that comparison). The report itself correctly defers the
  live re-proof to the controller gate; treat the 54/54 claim as controller-pending, not as
  reviewed evidence here.
- Report caption says commits range `d198dc6..bf827f8`; the report document is itself commit
  `5e4dcf7` (documentation nit only, content otherwise accurate).

## Not reviewed by design

All-930 live verification with `WorldBankVerifier(csv_language='es')` for the two recovered
indicators, the quality re-review, and HANDOFF/ledger state - controller-owned. No HANDOFF or
ledger edits made by this review.
