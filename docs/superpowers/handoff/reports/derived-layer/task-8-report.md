# Task 8 report: backoffice derived pages

Status: DONE

## Commits (branch pipeline-rebuild)
- `c73588f` refactor(status): one derived_state rule for status and backoffice
- `49b3ba0` feat(backoffice): derived series pages with calculado badge

## What was built
- **Refactor first (AGENTS hard rule):** `ingest/status.py` gains `derived_state(row) ->
  'no_base_data' | 'never_computed' | 'stale' | 'current'`, extracted from `_derived_status`
  (behaviour unchanged; `tests/ingest/test_status*.py` green). The backoffice list uses it,
  so the staleness rule lives in one place (it compares parsed times, not text) instead of
  being re-derived in `backoffice/`. This touches a file outside the brief's list; the reason
  is DRY.
- `backoffice/reads.py`: `derived_list(db)`, which merges `derived_series_rows(active_only=False)`
  and `derived_status_rows()` by key. It returns key, label, formula_label_pt, base_series_id,
  unit, active, served_values, stale, last_covered_at, plus a display `state`, where inactive
  series show as 'inactive'. It also adds `derived_detail(db, key) -> DerivedDetail | None`
  (frozen dataclass with series, total, served (cap `OBSERVATION_CAP`), versions (cap
  `DETAIL_LIST_CAP`) and runs (`DERIVED_RUN_CAP = 20`)). Each version's input ids are resolved
  with `Db.observations_by_ids` into `inputs` (series_id, period, observation_id; formula
  order), so non-served versions link their inputs too. There is no SQL in backoffice.
- `backoffice/app.py`: `GET/HEAD /derived` and `/derived/{key}`. An unknown key returns 404
  `error.html` ("unknown derived series: ...").
- Templates:
  - `_calc_badge.html` holds the exact badge `<span class="calc" title="Valor calculado pelo
    Prumo">calculado</span>`, included everywhere (one source).
  - `derived_list.html` puts the badge on every row and shows the label, Portuguese formula
    label, base link, unit, active, served count, state and last covered time.
  - `derived_detail.html` shows:
    - the definition: formula_label_pt plus code, params, unit, base link, attribution
      (from the served view; with no served value, the base source attribution marked
      "base source; no value served now"), and the licence.
    - the served table: stored value text plus the badge, with each input linked as
      `/series/<id>?period=<p>` and its observation id.
    - the versions table: every row with the badge, row state match/mismatch/pending, run
      state, served or not served, and input links.
    - the runs table: newest 20 runs of any scope, with a "covers this series" column and
      written/checked/mismatch counts.
  - `base.html` adds the nav link "Derivadas" and a `.calc` style (dashed, italic, info
    colour; inline CSS only).
  - `overview.html` adds one `#derived-line` from `report.derived`, which comes from the
    cached report, so the 30 s cache semantics are unchanged.
- No JavaScript, CSP/Host allow-list/cache untouched, autoescape on, no float formatting.
- `tests/backoffice/conftest.py`: `Env`/`make_env` take an optional `derived` list, written
  to the YAML and synced through `load_derived` + `sync_derived`.

## Tests
- New `tests/backoffice/test_app_derived.py` (9). The 7 named in the brief are there. I added
  `test_detail_renders_without_any_derived_data` and `test_overview_shows_derived_line`.
  Red first: all 9 failed before implementation (404/no nav link), then passed.
- `tests/backoffice`: 77 passed (including `test_all_routes_are_get_or_head_only` and the
  boundaries test). Ruff is clean.
- Full suite (`tests/ingest tests/backoffice tests/test_docker_contract.py -m "not live"`):
  see the result appended below.

## Concerns
- The detail page does not list `derived_event` rows (zero_denominator / missing_base_period
  / mismatch / compute_error). No general Db read for them exists, and the brief does not ask
  for one; failed runs and mismatch counts are visible in the runs table and versions.
  Showing events would need a new `Db` method; that is a candidate follow-up.
- The runs table shows the newest 20 derived runs of ANY scope, flagged "covers this series".
  It is not filtered per key, because `Db.derived_runs` has no key filter.
- CLAUDE.md asks for GitNexus impact/detect_changes, but the tools are not available in this
  session. I checked by hand: `_derived_status` has a single caller (`build_status`).
- The one pytest warning is Starlette's httpx TestClient deprecation and was already there.

## Full suite result
`tests/ingest tests/backoffice tests/test_docker_contract.py -m "not live"`: 1855 passed,
7 deselected (live), 3 warnings (Starlette httpx deprecation, already present), 654.95 s, exit 0.
