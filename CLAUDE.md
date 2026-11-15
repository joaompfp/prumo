# Claude Agent: Prumo Codebase

## Role

Prumo is being rebuilt around a new `ingest/` data pipeline (see `docs/superpowers/specs/2026-11-10-base-data-pipeline-design.md`).
The legacy UI was removed (recoverable at git tag `legacy-ui-final`); the app currently serves an "Em manutenção" page and `/healthz`.
Repo: `joaompfp/prumo` (this directory). Live: `https://cae.joao.date`, `https://joao.date/dados`. Host: f0nix.

## Path Mapping

| Location | Container Path | Notes |
|----------|---------------|-------|
| `app/`, `static/` | `/app/...` | Bind-mounted `:ro` |
| `appdata/` | `/data` | Runtime data, gitignored, never commit |

## Deploy Workflow (on f0nix, repo in `~/docker`)

Use the `dc-web-*` aliases via `bash -lic`; never raw `docker compose` or `docker run`.

| Action | Command |
|--------|---------|
| **Build + deploy** | `bash -lic "dc-web-up prumo"` |
| **Logs** | `bash -lic "dc-web logs -f prumo"` |
| **Status** | `bash -lic "dc-web ps"` |

Compose file: `~/docker/stacks/web/compose/prumo.yml`. Code: `~/docker/stacks/web/images/prumo`.

## Testing

```bash
pytest tests/ -v
```

## Reference

- **`AGENTS.md`** — Local dev setup, coding constraints
- **`docs/superpowers/`** — Specs and plans
