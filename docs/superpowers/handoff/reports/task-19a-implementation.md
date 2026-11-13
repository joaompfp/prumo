# Task 19A implementation report

## Scope and ownership

Implemented only slice 19A from `task-19-brief.md`, starting on `pipeline-rebuild` at `19536716ab27d340e8ef08d67b24bb83ccf5f93f`. This report records my own implementation and checks, not an independent specification/quality approval or controller acceptance.

Owned changes:

- `ingest/docgen.py`: deterministic source catalogue renderer and registry-reading wrapper.
- `ingest/cli.py`: additive `docs` parser entry and early return before operational path resolution, registry loading for ingestion, DB/raw-store construction or HTTP setup.
- `tests/ingest/test_docgen.py`: focused offline documentation tests.
- `docs/data/sources.md`: generated from the actual core registry through the CLI.
- `docs/superpowers/handoff/reports/task-19a-implementation.md`: this report.

No registry, ingestion, verifier, parser, SQL, dependency or production behavior was changed. No 19B documentation or shared controller state was edited by me. Other work appeared concurrently in Git status, including 19B documents and controller evidence/HANDOFF changes; I left it untouched. There was no delegation, external communication, whole-suite/live run, staging, commit, push, merge or deployment.

Applicable skills loaded: `prumo-data-pipeline` (including publisher-channel reference) and `gitnexus`. Read the brief, current handoff/rulings, registry model/loader, CLI, neighbouring tests, dependency manifest and reviewed verifier module contracts.

## Implementation

`python -m ingest docs` writes Markdown to stdout only. `python -m ingest --registry PATH docs` honours a custom registry. To regenerate the committed catalogue:

```sh
python -m ingest docs > docs/data/sources.md
```

No output-path flag was added. Shell redirection is the documented explicit destination; the command itself opens no output file, database or raw store.

`render_sources` is a pure renderer, sorted by source name and exact series ID without mutating its inputs. The wrapper reads source definitions separately because the public `load_registry` contract returns series only and therefore cannot represent zero-series sources. It validates all source definitions with `SourceSpec`, retains existing series/primary validation through `load_registry`, and changes neither that contract nor the registry.

The generated catalogue includes all 9 current source definitions and all 1,791 exact registry series IDs, indicator keys and native codes. Roles/states checked against the registry: 1,340 active primary, 427 inactive primary, 5 active cross-check and 19 inactive cross-check entries. Each source includes licence, licence URL, attribution, redistribution eligibility, verifiable policy and reviewed independent-channel description. Zero-series definitions are supported and tested through custom registries; the current core has no zero-series source definition, so no ERSE entry was invented.

Reviewed channels are documentation-only strings based on the actual verifier contracts. Unknown sources remain undocumented. DGEG is explicitly scoped to the current blocked definitions, with partial PDF channels acknowledged and no fictional verifier. Metadata is HTML/Markdown escaped, including pipes, embedded markup and line breaks. Literal publisher attribution/licence typography is retained. The catalogue distinguishes registry policy from production status, technical verification from redistribution permission, and sampled verification from an all-row claim.

## Impact analysis

Before CLI edits, the exact-worktree index reported up-to-date at `1953671`.

- `build_parser`, upstream: LOW, 1 direct caller (`main`), 3 impacted nodes, 1 attributed evidence process.
- `Function:ingest/cli.py:main`, upstream: LOW, 2 non-test direct callers (`ingest/__main__.py` and the Task 17 controller-acceptance `call` helper), 1 attributed evidence process.

Full symbol context additionally exposed CLI, bundle and Task 17 tests. Existing focused CLI tests were exercised. Semantic query attempts returned empty results with the known read-only FTS initialization warnings; impact/context queries succeeded. No reindex or generated-instruction rewrite was performed.

## Fresh test-first evidence

Tests were authored before either `ingest/docgen.py` or the CLI docs branch existed.

RED:

```sh
.venv-ci/bin/python -m pytest tests/ingest/test_docgen.py -q --basetemp=/home/joao/.hermes/cache/scratch/prumo-task19a-red
```

Result: 25 failed in 0.74s, from the absent module/command (including the subprocess import check). This was a fresh run, not reused baseline evidence.

An intermediate implementation run returned 20 passed / 5 failed. The test table reader incorrectly skipped a data row because its separator filter had already excluded the separator; that helper was corrected without weakening the exact-row expectations. The remaining failures were missing generated output after a generation subprocess inherited Hermes's incompatible Python path. Regeneration with `PYTHONPATH`/`PYTHONHOME` excluded succeeded using the existing project interpreter; no package install or dependency change was needed.

GREEN:

```sh
.venv-ci/bin/python -m pytest tests/ingest/test_docgen.py -q --basetemp=/home/joao/.hermes/cache/scratch/prumo-task19a-green-final
```

Result: 25 passed in 55.03s.

Coverage includes exact complete metadata/series contents, committed-output currency, deterministic order, pure rendering, inactive and zero-series definitions, cross-check roles, unknown channels, custom/empty/invalid registries, escaping, stdout/help behavior, and early CLI isolation. The isolation test refuses operational setup and checks that configured DB/raw paths and the temporary directory remain untouched. A separate fresh subprocess blocks source/verifier imports, network connection calls and SQLite connections while importing and rendering documentation.

Focused existing CLI regression:

```sh
.venv-ci/bin/python -m pytest tests/ingest/test_cli.py -q --basetemp=/home/joao/.hermes/cache/scratch/prumo-task19a-cli-regression
```

Result: 9 passed in 6.02s. These are the existing offline fixture/seam tests, not live collection.

Other checks:

- `.venv-ci/bin/ruff check ingest/docgen.py ingest/cli.py tests/ingest/test_docgen.py`: all checks passed.
- `git diff --check -- ingest/cli.py`: passed.
- Actual `python -m ingest docs` subprocess: exit 0, empty stderr; its stdout was used for the generated file.
- Actual `python -m ingest docs --help`: exit 0, documents stdout, selected registry and no operational I/O.
- A final fresh rendering equals the generated file byte-for-byte as UTF-8 text. SHA-256: `5612508b8297ff09ab78194f84a1e79d5308b6463aa2b5e582c0b15e0b555849`.
- No staged paths; no registry or requirements diff.

## Protected files and remaining gates

Protected file hashes were identical at intake and after focused verification:

- `AGENTS.md`: `3ca4c4f363717d9dc5cf90adce6a4a6515a217ba1dab588bc04bf4f05d2f2513`
- `CLAUDE.md`: `035dbcb8ba48cafabe128e757cca08f0dd8b6d4b44f950618d375867f7843c2a`

Their existing dirty changes were neither edited nor reverted by me.

Slice 19A is implemented and left uncommitted. This does not close Task 19, the real Task 18 observation, or Project 1. Production was not queried or modified, endpoint availability and rights were not reassessed, and no full suite or independent review is claimed. Controller verification and the other documented acceptance gates remain outside this bounded slice.
