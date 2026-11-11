# Sources with no independent verification channel (spec §6b) — NOT SERVED

A source listed here has an adapter (fetch → raw store → validation) but no channel independent
of the collector's own parser through which a sample can be re-read. Its runs therefore never
reach `verified` (no verifier is registered for it: `run_with_refetch` refuses it and the runs stay
`pending-verification`), so `served_observation` never shows its data. Data and raw evidence are
still collected, so revision history starts at the first ingestion. Owner decision needed.

## ine — Instituto Nacional de Estatística (Statistics Portugal)

Checked live on 2026-11-11 (Task 10; details in docs/superpowers/handoff/reports/task-10-report.md):

| channel | what it gives | usable as verifier? |
|---|---|---|
| `json_indicador/pindica.jsp?op=2` (Database API) | values | — it IS the collector |
| `json_indicador/pindica.jsp?op=1` | the latest value repeated for every period | no (wrong data) |
| `json_indicador/pindicaMeta.jsp` (Metadata API) | dimensions, units, period range | no values |
| `xml_indic.jsp?opc=1/2/3` (Catalog API) | indicator catalogue, links to the JSON API | no values |
| High-Value Datasets DCAT-AP catalogue (`catalogo_hvd_json.jsp`) | every distribution = the same `pindica.jsp?op=2` JSON | no (same channel) |
| indicator page `xurl/indx/<varcd>` → `bddXplorer04.jsp` table/export (the channel the plan named) | browser application; a plain HTTP client gets an empty body | no (needs browser emulation) |
| Short-term indicators / HVD statistics pages | Power BI embeds | no |

INE's API documentation lists exactly three APIs (Catalog, Database, Metadata); no public SDMX or
CSV bulk endpoint was found. Eurostat (and the ECB/OECD) republish some INE-produced series
(HICP, industrial production, unemployment) — that is a cross-check of the same publisher's
figures, not independence from it, so it was not built.

Options for the owner: (a) accept a cross-check against Eurostat for the INE series Eurostat
republishes (HICP, IPI by NACE, unemployment) as the "independent channel" for INE; (b) accept
browser-rendered verification of the INE indicator page (bddXplorer) in a headless browser; (c)
keep INE unserved. Until decided, every active `ine.*` series is collected but not served.
