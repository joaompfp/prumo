# Task 16 - E-REDES/dadosgov conditional scope disposition

Date: 2026-11-12. Controller scope check, no implementation or publisher requests.

## Disposition

Not applicable to the current core registry. Task 16 in the authoritative plan is conditional: E-REDES/dadosgov adapters are required only if registry-listed series are core. The registry contains no source entry and no series for either publisher. This is a conditional scope decision, not successful ingestion and not a claim that either publisher has no data or independent channel.

## Executed check

In /home/joao/projects/prumo-pipeline, branch pipeline-rebuild, at code decc048:

`.venv-ci/bin/python` loaded the authoritative `registry/core.yaml` through `ingest.registry.load_registry` and enumerated every source, including inactive series. Results:

| Source | Registry series | Active |
|---|---|---|
| bportugal | 10 | 10 |
| dgeg | 17 | 0 |
| eurostat | 697 | 329 |
| fred | 20 | 12 |
| ine | 42 | 41 |
| oecd | 6 | 6 |
| ren | 14 | 14 |
| worldbank | 982 | 930 |
| E-REDES | 0 | 0 |
| dadosgov | 0 | 0 |

Registry SHA256: `8cb91ac64a3312ca52d5afba2b71f996edac09a94a586a2e7015eac15e09fd74`.

Checks include the aliases eredes, e-redes, e_redes, dadosgov, dados.gov and dados.gov.pt; the complete actual source list above contains none. The conditional plan wording is at `docs/superpowers/plans/2026-11-10-base-data-pipeline.md`, Task 16 row (line 165), and the adapter scope remains registry-listed series.

## Changes and limits

No new source, series, registry change, adapter or verifier was added. No speculative E-REDES/dadosgov discovery, authentication, HTTP request or fixture was needed. Existing legacy collectors remain untouched until Task 17 removes superseded collection infrastructure.

Next implementation gate is Task 17: CLI, status, replay and old-collector removal. DGEG's separate blocked disposition and the World Bank fresh-live gate remain open. REN, FRED and OECD licence gates remain unchanged. No main merge or deployment.
