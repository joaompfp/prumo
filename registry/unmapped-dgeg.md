# DGEG disposition register (Task 12B, 2026-11-11) — 17 series, INACTIVE, never served

All 17 DGEG annual PT series (the complete DGEG set in `core.yaml`) keep their original ids,
units, frequencies, geographies, roles and indicator_keys but are `active: false`, and the `dgeg`
source is `verifiable: false` + `redistribution_ok: false`. This is a **safe disposition, not an
ingestion**: there is no DGEG ingest adapter and no verifier, and no new live DGEG collection
has run. Task-8 legacy imports remain unchanged; no unit conversion or display-rounding policy
is applied or implied. It is
also **not** a claim that DGEG as a source has no independent channel: the bounded 2026-11-11
follow-up research (hashes controller-verified) found real partial same-publisher channels,
recorded per row below. "Inactive" here = ineligible until the row's resumption criteria are met
and the owner signs off; nothing was deleted or remapped.

Authoritative ground truth: the publisher workbook `dgeg-iie-1995-2024.xlsx` (119,336 bytes,
sha256 5f31904ad33757ba2b52d02fd5107be4054ad94db7e97d1bc17edfda177837be), committed at
`docs/superpowers/handoff/evidence/task-12-dgeg/` with a hash manifest. Coordinates below were
verified against the workbook's raw XML (year columns E=1995 … AH=2024p on every data sheet;
header row = row 8). Raw percent rows store **fraction tokens** under percent display formats —
never to be relabelled percent-scale without an explicit owner policy decision.

Independent-channel references (same publisher, different endpoint/format):

- **APN** — "Energia em Portugal – Principais Números 2024" PDF,
  https://www.dgeg.gov.pt/media/5riiwycf/dgeg-apn-2015-2024-pt.pdf (sha256 d4490a8e…07a7,
  edition 2026-02-13; integer tables for 2015–2024 only).
- **AEN** — "Energia em Números, edição 2025" PDF,
  https://www.dgeg.gov.pt/media/b4fhd0lv/dgeg-aen-2025e.pdf (sha256 9486137e…c4db1;
  Annex 1 tables 2006–2023 as captured, base-2016 intensities; "Todos os direitos reservados").
- **arr-q** — monthly "Estatísticas rápidas das renováveis" XLSX (same format as the workbook ⇒
  weak/cosmetic independence, rejected as a verifier channel).

## Per-series matrix (exactly the 17 registry ids)

| # | series id (unit kept) | workbook coordinate / native unit | reason category | what the bounded research actually found | resumption criteria |
|---|---|---|---|---|---|
| 1 | dgeg.co2_emissions_energy.PT (Mton CO2e) | sheet1 row 24, `Emissões Totais do setor energético`, Mton CO2e, 1995–2023 (2024p = `nd`) | precision/coverage | AEN Annex 1 (unit spelled CO2eq) matches at 1-dp **display** precision 18/18 for 2006–2023 only; raw tokens carry binary-float tails (e.g. 2023 `35.299999999999997`); 1995–2005 + 2024p have no channel | owner-approved display-precision comparison policy + coverage acceptance, then a verifier |
| 2 | dgeg.co2_emissions_total.PT (Mton CO2e) | sheet1 row 22, `Emissões Totais(2)`, Mton CO2e, 1995–2023 (2024p = `nd`) | precision/coverage | same AEN Annex 1 surface, display-exact 18/18 at 0.1 Mton, same coverage gap | same as #1 |
| 3 | dgeg.consumption_industry.PT (ktep) | sheet2 row 32, `Indústria(3)`, ktep, 1995–2024p | no-established-current-channel (rounding-scale only) | AEN Tab.1/Anexo 2 publish **tep** for 2023 only (e.g. `4 660 856` tep → ktep needs ÷1000 + rounding); APN sector values are charts without text values; arr-q has no sector rows | an exact same-unit (ktep) same-precision channel, or owner-approved rounding policy + multi-year channel |
| 4 | dgeg.consumption_primary_total.PT (ktep) | sheet2 row 9 (≡ sheet1 row 17, token-identical all 30 years), ktep, 1995–2024p | vintage drift + coverage (partial channel — NOT "no channel") | APN total-primary table is a genuine exact channel for 8/10 years of its 2015–2024 window, but 2021 `20812`≠`20822` and 2022 `21313`≠`21315` are real publication-vintage drift, and APN does not cover pre-2015 → fails a strict 100% sample today | next APN edition aligning vintages, or an owner-documented verification window rule |
| 5 | dgeg.consumption_transport.PT (ktep) | sheet2 row 40, `Transportes`, ktep, 1995–2024p | no-established-current-channel (rounding-scale only) | same shape as #3 (AEN tep, 2023 only, needs ÷1000 + rounding) | same as #3 |
| 6 | dgeg.electricity_consumption.PT (TWh) | registry unit maps to sheet1 row 20 `TWh(1)` (1995 `29.2` … 2024p `51.357999999999997`; footnote: includes refinery/power-plant network consumption); the publisher's ktep row is sheet2 row 21 | unit conflict (with a real partial channel) | APN's electricity table is **ktep** (sheet2-row-21 values: token-exact 10/10, 2024 `4349`) — exact for the ktep representation, NOT the registry's TWh unit; no same-unit external TWh channel found | owner decision: track a registry unit correction to ktep (not a conversion) or pin sheet1-row-20 TWh(1) tokens collector-only; then verify |
| 7 | dgeg.energy_dependence.PT (%) | sheet1 row 10, `Real`, %, raw tokens are fractions under `0.0%` format (2024p `0.64312837828385205`) | representation/precision policy | APN row-1 dependence table display-exact 10/10 at `0.0%` (64.3%); AEN annex display-exact 18/18 (`66,7%`); APN row-2 variant matches neither IIE row 10 nor 11 (6/10 display diffs) — unusable; no channel carries the raw fraction tokens | owner representation policy (fraction stored as-is vs publisher display) + display-precision verification policy |
| 8 | dgeg.energy_intensity.PT (tep/M€) | — duplicate of registry `energy_intensity_primary` (sheet1 row 28) with a lossy unit string; no distinct native mapping exists | duplicate concept | nothing independent can map to an ambiguous duplicate; legacy values equal row 28's | owner reconciliation (retire-alias or redefine); until then inactive |
| 9 | dgeg.energy_intensity_final.PT (tep/M€'2021) | sheet1 row 29, base 2021, 1995–2024p | base-year/definition mismatch | AEN annex intensities are base **2016**; APN publishes index form `2021=100` — neither matches the current base-2021 workbook definition | a same-base (2021) same-unit independent channel |
| 10 | dgeg.energy_intensity_industry.PT (tep/M€'2021) | sheet1 row 38, base 2021, 1995–2024p | base-year/definition mismatch | same as #9 | same as #9 |
| 11 | dgeg.energy_intensity_primary.PT (tep/M€2021) | sheet1 row 28, base 2021, 1995–2024p (publisher cell C28 and registry both print `tep/M€2021`; rows 29/38/39 include an apostrophe, an original publisher spelling inconsistency) | base-year/definition mismatch | same as #9 | same as #9 |
| 12 | dgeg.energy_intensity_services.PT (tep/M€'2021) | sheet1 row 39, base 2021, 1995–2024p | base-year/definition mismatch | same as #9 | same as #9 |
| 13 | dgeg.final_energy_consumption.PT (Mtep) | publisher row is sheet2 row 17 `Consumo Total de Energia Final` in **ktep** (2024 `16713`; sheet1 row 18 2024p holds unrounded `16712.810000000001`), 1995–2024p | registry-unit conflict (Mtep vs publisher ktep) with a real exact channel | APN total-final table is token-exact 10/10 in **ktep** (2015–2024): the channel exists but validates the publisher-unit representation, not the registry's Mtep unit — inactivate for the conflict, not for "no channel" | owner unit reconciliation (Mtep→ktep correction), then an APN-PDF verifier is implementable |
| 14 | dgeg.primary_energy_consumption.PT (Mtep) | legacy values are actually sheet1 row 13 `% da produção doméstica no CEP` (unit %, publisher pre-rounded 2-dp fractions, 2024p `0.39405298811534401`) — a domestic-production share, NOT an Mtep consumption | legacy misassignment (wrong concept/scale) | AEN annex %-production row conflicts with workbook row 13 even at display precision (17/18 mismatches) — the surfaces disagree and neither is the registry concept | owner concept/scale reconciliation and an explicit approved remap; preserved (not silently corrected) per quarantine rules |
| 15 | dgeg.renewable_share_electricity.PT (%) | sheet3 row 12 (FER-E), %, fraction tokens under `0.0%`, 2004–2024p (`-` before 2004) | no established series channel | arr-q Quadro 18 carries a Eurostat EU-27 table whose PT 2023 `0.63` token-matches — single year and Eurostat-sourced (other publisher, outside the same-publisher bar); AEN narrative 2023 only | a multi-year independent exact channel + representation policy |
| 16 | dgeg.renewable_share_total.PT (%) | sheet3 row 11 (FER-Global), %, fraction tokens under `0.0%`, 2004–2024p | channel independence too weak + representation policy | arr-q quick-stats workbook Quadro 24 is token-exact 9/9 for 2015–2023 **but is the same publisher, same XLSX format, same statistics division** → cosmetic independence (cf. the rejected BPstat format=csv channel); AEN single-year narrative otherwise | owner representation policy + a genuinely different-format/endpoint channel |
| 17 | dgeg.renewable_share_transport.PT (%) | sheet3 row 13 (FER-T), %, fraction tokens under `0.0%`, 2004–2024p; 2004 token is scientific notation `4.0000000000000001E-3` | no established series channel | AEN narrative 2023 only | a multi-year independent exact channel + representation policy |

Series count check: rows 1–17 are the complete DGEG set in `core.yaml` — nothing unmapped from
the registry, and no source declared nonexistent.

## What would make DGEG eligible again (source level)

1. Owner decisions on the open policy questions: percent-fraction representation
   (fraction-as-stored vs publisher display rounding), the Mtep/TWh unit reconciliations (#6,
   #13), the duplicate (#8), the misassignment (#14), and the #4 vintage/window rule.
2. A reviewable DGEG ingest adapter (pinned workbook coordinates above) AND an independent
   verifier meeting the unchanged exact-token bar for the approved subset.
3. A written DGEG reuse grant or counsel's LADA opinion (registry/licences-todo.md) before any
   serving; `redistribution_ok` stays false regardless of adapter work.
