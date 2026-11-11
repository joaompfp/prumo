# Task 10 report — INE adapter (+ verifier: STOPPED, no independent channel)

Status: IN PROGRESS (kept updated as work proceeds; a rate limit can cut the agent off).

## Key finding 1 — INE has ONE machine-readable data channel (spec §6b / template lesson 9)
Probed live 2026-11-11 (f3nix, polite UA, ≤1 req/s):
- `https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=..&Dim1=..` — the data API (collector).
- `pindica.jsp?op=1` — returns the LATEST value repeated for every period (0001188: '-5.2' for
  every month 1990..2026 while op=2 has the real history): unusable.
- `pindicaMeta.jsp` — metadata only (units, dimensions, categories), no values.
- `xml_indic.jsp?opc=1|2|3` — catalogue (metadata + links to the same JSON API), no values.
- INE API v2 documentation page lists exactly three APIs: Catalog, Database, Metadata.
- High-Value Datasets DCAT-AP catalogue (`catalogo_hvd_json.jsp`): every distribution's accessURL is
  the same `pindica.jsp?op=2` JSON (50/50) — not a second channel.
- Indicator page `xurl/indx/<varcd>` → `bddXplorer04.jsp` (the "indicator page export" the plan
  names): a browser-only application; a plain HTTP client gets an empty body. Not usable without
  browser emulation (not attempted further).
- Short-term indicators / HVD statistics pages: Power BI embeds.
- Web search: no public INE SDMX or CSV bulk endpoint.
Eurostat republishes some INE figures (HICP, IPI) — that is a cross-check of the same publisher's
data, not an independent channel (brief). → No verifier built; INE listed in
`registry/unverifiable.md`; INE series are NOT SERVED (no registered verifier ⇒ runs stay
`pending-verification`).
