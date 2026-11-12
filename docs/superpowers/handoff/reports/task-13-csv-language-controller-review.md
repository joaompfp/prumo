# Task 13 - CSV recovery, scoped reviews and full recorded-response gate

Controller checkpoint, 2026-11-12. Branch `pipeline-rebuild`; implementation through `5e4dcf7`, following base `d198dc6`. Task 13 remains OPEN on full-source fresh live acceptance. Task 14 has not started under the owner's requested order. No merge, deployment, scheduling or precision relaxation.

## Recovery result

The owner supplied an extracted directory, not a ZIP archive:
`/home/joao/.hermes/webui/attachments/37da5128f130/API_NY.GDP.MKTP.KD.ZG_DS2_en_csv_v2_255547`.
It contains the genuine-shaped main GDP-growth CSV and both metadata CSVs. Main CSV: 303,340 bytes, SHA256 `3ee4af1faa264816cdab2dafafae4ff669cd3ec88d82fa20b17042fe2d1f386b`, Last Updated Date 2026-10-08; all 54 latest-per-series diagnostic comparisons matched the recorded JSON exactly. The files were preserved unchanged as extracted user-provided CSVs. No reconstructed ZIP or invented HTTP status was substituted into verification.

Original publisher ZIPs were independently recovered from the same World Bank exporter in Spanish, via f0nix:

| Indicator | Actual status | Bytes | SHA256 |
|---|---|---|---|
| SL.UEM.TOTL.ZS | 200 | 42,458 | d0533f8f2c23dcfe838b588663479478f7bbd6efe3a83ae4d6649e0a6e7c6872 |
| NY.GDP.MKTP.KD.ZG | 200 | 135,776 | 0054931ddc3db0f9e2c94a8abe8f2c8b417be5888b695379e8ee91c8257527e8 |

Exact URLs are `https://api.worldbank.org/v2/es/indicator/<CODE>?downloadformat=csv`. Both ZIPs have the localized Data Source title `Indicadores del desarrollo mundial`, English column labels and dot-decimal tokens. All 54 registry geographies are present in each. Latest diagnostic comparisons were 54/54 exact for each indicator. The unemployment ZIP was retrieved again at 10:47 UTC with identical SHA256 and HTTP 200.

No missing original export remains in the recorded evidence set. The remaining blocker is reproducible live availability, not an outstanding user upload.

## Scoped implementation and review

A fresh implementer added explicit `WorldBankVerifier(csv_language='es')`; default `en` is unchanged. Refactoring the locale/identity contract preceded admission of Spanish. Only `en` and `es` are accepted. Full ZIP member identity and shared revision, locale-specific title, numeric tokens, duplicate identities, missing cells and malformed responses remain fail-closed. No automatic language fallback, request rewriting, rounding or new publisher/channel was added.

Independent specification review: PASS (`task-13-csv-language-spec-review.md`).
Independent quality review: APPROVED, no Critical or Important findings (`task-13-csv-language-quality-review.md`). Deferred minors: the locale allowlist is a mutable dict in the same trusted process, and no test pins its exact key set. These do not waive any live gate.

Controller verification after implementation:

- `.venv-ci/bin/python -m pytest tests/ingest/test_verifier_worldbank.py -q`: 45 passed in 7.65 s.
- `.venv-ci/bin/ruff check` on the four changed Python paths: all checks passed.
- `.venv-ci/bin/python -m pytest tests -q`: 929 passed, 5 live deselected, 1 warning in 166.97 s.

## Full-scope recorded-response gate

The actual registered `WorldBankVerifier` and `run_with_refetch` were exercised using exact, hash-checked original HTTP response bodies. Collector responses came from the fresh all-source JSON fetch at about 10:40 UTC; independent evidence comprised the 16 original English ZIPs recovered earlier on the same date and the original Spanish GDP/unemployment ZIP responses. Stored statuses and final URLs are those captured from the origin, never assigned to user files. This was explicitly a RECORDED-RESPONSE run, not a new successful all-source network run.

Disjoint datasets were chosen before running: English verification for the 822 series covered by the 16 original English exports; Spanish verification for the remaining 108 series. Each dataset ran in its own process, with normal verifier registration. This does not bypass or replace the registry: registering another verifier for an already registered source correctly raises; a controller diagnostic earlier encountered that guard and is not counted as success. Task 17 must resolve deterministic dataset/locale orchestration through supported contracts, not private registry mutation.

| Dataset | State | Written | Quarantined | Sample matches |
|---|---|---|---|---|
| 822 series / en | verified | 40,940 | 13,312 | 1,200 / 1,200 |
| 108 series / es | verified | 4,975 | 2,153 | 300 / 300 |

The explicit union equals all 930 active registry series, with no omissions or duplicates. Every active series has observations. Total: 45,915 observations, 15,465 publisher-null quarantines, 1,500/1,500 exact sampled matches; 18 distinct evidence envelopes recovered from raw bytes, all 1,500 stored comparisons replayed offline. The sample includes the latest period of every populated series plus randomly chosen historical periods. The isolated recorded-response test DB serves 45,915 rows. That is neither production data nor proof of current export availability.

Durable evidence: `reports/evidence/task-13-csv-language/full-recorded-run.tar.gz` (3,865,309 bytes, SHA256 `10a4fca3ea302adbf170020a326be36459546167dfaf1c9b50c44bc123e8deff`). This controller-created audit capsule contains the isolated database, all 36 raw content-addressed payloads, comparison records, request provenance, probe scripts/failure manifests and the unchanged extracted user CSVs. It is expressly NOT an original publisher ZIP. The capsule was reopened and checked against the source files; path safety, required members, raw payload membership and readable machine reports were checked. `capsule-manifest.json` and `report.json` are alongside it.

## Fresh live gates remain blocked

A real all-930 `run_with_refetch`, using f0nix HTTP egress and the es verifier, fetched all 18 JSON responses and wrote 45,915 observations / 15,465 null quarantines. Verification failed on an unavailable Spanish export; the whole dataset stayed unserved. Selecting Spanish globally is not established as an operational solution.

An explicit grouped live attempt then re-fetched the 822-series English dataset (16 real JSON responses) but the first verification request, `https://api.worldbank.org/v2/en/indicator/SP.DYN.CBRT.IN?downloadformat=csv`, read-timed out at 15 seconds with zero response bytes. A separate curl probe reproduced the zero-byte 15-second timeout. A later bounded check of canonical/default-language, source=2 parameter-order and HTTP variants also timed out at 10 seconds. Distinct `/v2/country/all/indicator/SP.DYN.CBRT.IN?downloadformat=csv` and `/v2/en/country/all/indicator/SP.DYN.CBRT.IN?downloadformat=csv` requests at 10:53 UTC returned real HTTP 502 / 16-byte bodies. Their manifest and body are preserved alongside the audit capsule. This is an observed current failure, not a proven permanent or publisher-wide cause. The Spanish unemployment route still returned 200.

No failed live run was promoted using the successful recorded-response run. No cached response was described as a fresh network response. The original all-source fresh live criterion therefore remains BLOCKED. Retrying more variants or starting Task 14 out of order needs an explicit decision; no further probe loop, Task 14 implementation, main merge or deploy was started.
