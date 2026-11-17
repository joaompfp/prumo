# Prumo - Editorial pages (backoffice v1.1, part 1) - Design

Date: 2026-11-16 · Status: written by the planner from the owner's instruction "quero é poder configurar séries a mostrar numa página pública, a partir do backoffice" (owner opted out of the question round; every choice below is the planner's call unless marked **[owner]**).

## 1. Intent and why

The public site's only editorial surface is the "Números em destaque" block on the home page: twelve cards whose series and order are hard-coded in `presentation/catalog/pt.py` (`CURATED_HOME`). Changing which figures the front page leads with is a code change, a review and a deploy.

The owner wants to choose those series and their order from the backoffice, without touching data, licences or reader text. That is the whole of this project: a composition (which series, in what order, with which optional calculated companion) that the backoffice edits and publishes, and the public home renders.

## 2. State this design builds on (verified 2026-11-16)

- Public site deployed (`main` `7e563b2`), server-rendered Jinja, inline SVG, no JavaScript, no cookie, reads the SQLite file through `read_db_readonly` (immutable fast path, writer detection).
- 1,308 served primary series in `public_catalogue()`; the home builds its twelve cards from `pt.CURATED_HOME`, keyed by series id, each with an optional derived key for the change line.
- Reader text lives only in `presentation/catalog/{pt,en}.py`; keys are family, geography, unit, flag, theme, frequency, source, withheld note. A missing key raises `MissingText` and renders 503.
- Rule in force since backoffice v1: SQL only in `ingest/db.py`. `backoffice/reads.py` and `app/reads.py` contain zero SQL; they compose `Db` methods.
- SQLite is WAL, `BEGIN IMMEDIATE`, `BUSY_TIMEOUT_S = 30`. `open_db()` migrates; `open_db_readonly()` never migrates and refuses a schema whose applied migrations differ from this code's (older or newer).
- The backoffice container (`prumo-backoffice`) runs uid 1000, `read_only` root, `/data:ro`, Tailscale-only bind, no Traefik route. It has no POST route today.
- Migrations 0001-0017 are deployed and frozen. 0018 is the next number.

## 3. Decisions

### D1. Pages are code, composition is data

A page is a slug the code knows: title, subtitle, section note, route and reader text stay in `presentation/catalog/`. The database holds only the ordered list of series ids (plus an optional derived key). Creating a new page is still a code change (one catalogue entry, one route); choosing what appears on a page is a backoffice operation.

Rationale: this is the only shape that satisfies the 2026-11-15 decision that reader-facing text never lives in the data layer, keeps every public sentence reviewed in git, and gives i18n for free. A page title typed into a web form would be an untranslatable, unreviewed string on a public site whose promise is trust.

Consequence the owner should see in one line: this project makes the home page's figures configurable, not the set of pages.

### D2. Exactly one page is wired now: `inicio`

`inicio` is the home page block that exists today. The mechanism is slug-keyed so a second page is a catalogue entry plus a route plus a composition row, with no migration. No second page is built in this project (YAGNI).

### D3. Draft and published are separate rows, publishing is one transaction

`editorial_slot.state` is `draft` or `published`. Editing touches only `draft`. Publishing copies `draft` over `published` in one `BEGIN IMMEDIATE` transaction, so a public page never renders half a composition. There is no scheduled publish: published means live at the next request.

### D4. Empty composition means the code default, not an empty page

If `inicio` has no published rows, the home renders `pt.CURATED_HOME` exactly as today. The deploy is therefore visually a no-op, the rollback path is "delete the rows", and a lost composition degrades to a hand-written list instead of an empty page. The backoffice says which of the two is in force.

### D5. The composition stores no text and no numbers

Only `series_id` and an optional `derived_key`. Values, units, periods, publisher, receipt date and licence are read at request time from the same sources the site already uses. A composed card is therefore exactly as trustworthy as a catalogue card, with nothing to fall out of date.

### D6. Eligibility is a written rule, enforced twice

A series may occupy a slot only if all of these hold:

1. it is in the registry, `active = 1` and `role = 'primary'`;
2. its source has `redistribution_ok = 1`;
3. it has at least one served row (`served_observation` where `kind = 'fetched'`);
4. `series_title(lang, family, geography)` resolves in the language the page renders - `en.py` is deliberately empty in v1, so "both catalogues" would make every series ineligible and the editor would refuse every add;
5. no other slot on the same page renders the same title.

An optional derived key must exist in `derived_series`, be `active = 1`, have the slot's series as `base_series_id`, and resolve title and unit in the rendered language.

The rule is enforced when publishing (refusal with a per-slot reason, nothing written) and again when rendering (a slot that stopped qualifying is dropped, the rest render, and one WARNING line names the slug, the series and the reason). A licence revoked after publication must not 503 the front page and must not leave a hole.

When every published slot fails, the page renders no cards. It does not fall back to the code list: the fallback means "this page has no composition", and a page whose composition lost all its cards must not silently publish twelve series nobody chose. The distinction is carried by `page_composition` returning `None` (no rows) versus an empty tuple (rows that all failed), and it is tested.

### D7. Writes go through one narrow rw mount and one module

The backoffice keeps `/data:ro` and its read-only root filesystem. A second mount of the same host directory at `/data-w:rw` (env `PRUMO_EDITORIAL_DB=/data-w/prumo.sqlite3`) is the only writable path in the container. Only `backoffice/editorial.py` opens it, through a new `open_db_for_write()` in `db.py` that never migrates and refuses a schema that does not match this code exactly (fail closed, clear message). All other reads still use `/data`.

Why a second mount and not simply `/data:rw`: a read bug must stay unable to write, and the writable surface should be nameable in one line in the compose file.

Both writers must also run as the same uid. SQLite lets a process write only if it can write the database file, its `-wal` and its `-shm`; a worker running as root leaves `root:root 0644` files that uid 1000 cannot write, so `open_db_for_write` fails on its first `BEGIN IMMEDIATE` and the editor answers 503 for every POST while every GET keeps working - a half-broken deploy that a smoke test of `GET /editorial` would not catch. `deploy/prumo-ingest.yml` therefore runs the worker as `1000:1000`, the deployed data directory is chowned once, and `tests/test_docker_contract.py` asserts both compose files carry the same uid.

### D8. One writer at a time, with a version stamp

Every page carries `version`, incremented on every successful mutation. Every form carries the version it was rendered with; a mismatch returns 409 with "a composição mudou noutro separador" and the new state, and writes nothing. Two browser tabs cannot silently clobber each other. Contention with the worker is bounded by `BUSY_TIMEOUT_S = 30`: a write that cannot get the lock returns the same 409-style page saying the worker is writing, and changes nothing.

### D9. Every mutation is an audit row in the same transaction

One `editorial_event` row per mutation (add, move, remove, discard, publish, reset), written inside the same transaction as the change. The event carries the action, the resulting version, the operator's note (mandatory for publish, generated for micro-edits) and, for publish, the full slot list in `detail_json`. That makes any published composition reconstructible from the log without a history table.

### D10. No JavaScript, so ordering is buttons

The editor lists the draft with up/down/remove buttons and a candidate list with an "acrescentar" button. Each click is a small POST that mutates the draft and re-renders. No drag and drop, no client state.

### D11. Publish shows the change before it happens

Confirming a publish renders the diff against the currently published composition (added, removed, moved) and the actual cards as the home will draw them, plus a mandatory reason field. Reset to the code default is a separate, clearly marked action that deletes draft and published rows.

### D12. CSRF: Origin, not cookies

There is no session and no cookie in the backoffice. Every POST requires an `Origin` header whose host is in the allowed-hosts list, and rejects `Sec-Fetch-Site: cross-site`. No ambient credential exists to ride and a cross-site form cannot forge `Origin`. The perimeter remains Tailscale membership; no login is added in this project.

## 4. Data model (migration 0018)

```sql
CREATE TABLE editorial_page(
  slug                TEXT PRIMARY KEY,
  version             INTEGER NOT NULL DEFAULT 0,
  draft_saved_at      TEXT,
  published_version   INTEGER,
  published_at        TEXT
) STRICT;

CREATE TABLE editorial_slot(
  slug        TEXT NOT NULL REFERENCES editorial_page(slug) ON DELETE CASCADE,
  state       TEXT NOT NULL CHECK (state IN ('draft','published')),
  position    INTEGER NOT NULL CHECK (position BETWEEN 0 AND 11),
  series_id   TEXT NOT NULL REFERENCES series(id),
  derived_key TEXT,
  PRIMARY KEY (slug, state, series_id),
  UNIQUE (slug, state, position)
) STRICT;

CREATE TABLE editorial_event(
  id          INTEGER PRIMARY KEY,
  ts          TEXT NOT NULL,
  slug        TEXT NOT NULL,
  action      TEXT NOT NULL CHECK (action IN
                ('slot_added','slot_moved','slot_removed','draft_discarded',
                 'published','reset_to_code')),
  version     INTEGER NOT NULL,
  note        TEXT NOT NULL,
  detail_json TEXT
) STRICT;

CREATE INDEX editorial_slot_state ON editorial_slot(state, slug, position);
```

Notes that bind the implementation:

- `position` is contiguous `0..n-1`; the whole draft list is rewritten on each mutation rather than patched, so no gaps and no renumbering logic.
- `position BETWEEN 0 AND 11` makes "more than twelve cards" unrepresentable, matching the home grid. Twelve is a layout fact, not a policy knob.
- `derived_key` has no foreign key on purpose: `derived_series` is a projection that can deactivate a key, and a hard reference would block that for an editorial convenience. It is validated in code at write and read.
- `series_id` does have a foreign key: the pipeline never removes a series, it deactivates it (standing owner rule: history is never deleted).
- `slug` is not constrained to the catalogue: a row whose slug the code does not know is inert. The backoffice only ever offers code slugs.
- A page has no row until its first write: the first mutation inserts `editorial_page(slug, version 0)` and then increments, so `editorial_slot`'s foreign key always has a parent.
- The migration is additive: no existing table is rebuilt, no column changes, no `event` table touched (its `kind` CHECK is too narrow for editorial actions, which is why the audit lives in its own table).

## 5. Layers and interfaces

| Where | What |
|---|---|
| `ingest/db.py` | `open_db_for_write(path)`: WAL, `foreign_keys=ON`, no migration, refuses a schema whose applied migrations differ from this code's. `editorial_pages()`, `editorial_page(slug)`, `editorial_add/move/remove/discard/publish/reset(...)`, each bumping `version`, checking the expected version, writing its event inside the transaction. All SQL lives here. |
| `ingest/editorial_rules.py` | The eligibility rule of D6 as a pure function over (registry specs, catalogue titles, served ids), returning `(eligible, reason)`. No I/O. Called by the publish path and by the render path, so both cannot drift. |
| `backoffice/editorial.py` | Orchestration: loads candidates, applies the rule, calls the db functions, maps typed errors to pages. No SQL. |
| `backoffice/app.py` | `GET /editorial`, `GET /editorial/{slug}`, `POST /editorial/{slug}/{add,move,remove,discard,publish,reset}` with the Origin check. |
| `app/reads.py`, `app/main.py` | `page_composition(db, slug, lang)`: published slots, eligibility filter, drop-and-log, duplicate-title filter. The home builds its cards from that list when non-empty, else from `pt.CURATED_HOME`. |
| `presentation/catalog/pt.py`, `en.py` | `PAGES = {"inicio": {...}}`: section title, section note (PT and neutral), and the note rule stated below. No composition text. |

Home section note: today it reads "Portugal. Valores publicados tal como a fonte os publica." A composed page may hold non-Portuguese series, so the page renders that note only when every visible card is Portuguese and a neutral one otherwise ("Cada número indica a instituição e a data da recolha."). Both strings live in the catalogue.

Card label: a composed card uses `series_title(lang, family, geography)`, the same title the catalogue pages use. The twelve hand-written short labels stay in `CURATED_HOME` and retire with the code fallback.

## 6. What the operator sees

- `/editorial`: one row per code page, with published count, draft count, last publish, and whether the code default is in force.
- `/editorial/inicio`: two panels, "Publicado" and "Rascunho", and a candidate list (searchable by title, filterable by source and theme, paginated) showing only eligible series. Each draft row has up, down and remove.
- Publish: diff plus rendered cards plus a mandatory reason. Discard returns the draft to the published list. Reset deletes both and returns to the code default.

## 7. Deploy, rollback, and what this release does not touch

One deploy, worker first: `dc-web-up prumo-ingest` (applies 0018), `dc-web-up prumo`, `dc-web-up prumo-backoffice`. Between the first and the second the old web image refuses the newer schema and answers 503, as in every previous migration deploy. A pre-deploy copy of the database is taken and integrity-checked as usual.

Rollback constraint stated plainly: because 0018 makes the schema newer than any previous image, rolling the web container back alone leaves the site refusing the database. The rollback is the previous commit plus the pre-deploy database copy. Nothing served is lost by that (the copy is minutes old and the worker re-fetches what it missed); any composition published after the deploy is.

The release has no migration of served data, no new source, no licence change and no write path to `observation`, `quarantine`, `dataset_run` or `derived_*`.

## 8. Proof required before it is called done

- Dry run of 0018 on a copy of production: tables created, integrity ok, zero foreign-key violations, `observation` and `quarantine` counts unchanged, `editorial_*` empty.
- No-op proof: with 0018 applied and the tables empty, the rendered home is byte-identical to the home before this project. This is the test that protects D4.
- Publishing the same twelve series that `CURATED_HOME` lists produces the same cards in the same order (labels aside, which D-consequence above explains).
- A publish whose draft contains an ineligible series is refused, and nothing is written.
- A published series that loses its licence afterwards disappears from the page, the other cards render, and one WARNING line records why.
- Two tabs: the stale one gets 409 and writes nothing.
- A POST without `Origin` or with a cross-site `Sec-Fetch-Site` gets 403 and writes nothing.
- Every mutation leaves exactly one `editorial_event` row, and a forced error mid-transaction leaves none.

## 9. Non-goals and anti-goals

Non-goals: creating pages from the UI; any reader-facing text in the database; images, colours or layout per card; scheduling a publish; a second public page; per-slot ordering by drag and drop; multiple users or roles.

Non-goals carried forward explicitly, because they were promised in the backoffice v1 design and are **not** in this project: `withdraw run`, `verify run` and review-queue acknowledgement. They write to served state and to the queue, not to a private composition, and they get their own spec and their own migration (0020+; 0019 is now reserved by the statistics CMS). Splitting them here is deliberate: this project must be deployable without any risk to data being served.

Anti-goals, failure even if it works: a public page whose figures cannot be traced to a catalogue entry; a composition that survives a licence revocation; a write path in the backoffice that can touch anything other than the three `editorial_*` tables; reader text entering the data layer through the back door of an editorial form.

## 10. Open questions for the owner (non-blocking, defaults stated)

1. Should the composition be limited to Portuguese series? Default: no, any eligible series, with the neutral note when the page mixes geographies.
2. Is twelve the right cap? Default: yes, it is the grid.
3. Do you want the home block to keep its current note when every card is Portuguese? Default: yes.

## 11. Left to the builder

Exact page copy and table layout; how the candidate list shows provenance without noise; the WARNING log format; the shape of `detail_json`; test fixtures (reuse the production-shaped copy); and whether the diff and the card preview share the home template or a partial. The rule of D6, the schema of section 4 and the deploy order of section 7 are not negotiable.
