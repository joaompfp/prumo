# Sources Registry

This file documents the current external data providers used by Prumo.

| Provider / Source | API or Official Dataset Page | Update Cadence (typical) | Usage Caveats / Terms Note |
|---|---|---|---|
| INE (Instituto Nacional de Estatística) | https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_BD_tema | Monthly / Quarterly (series-dependent) | Verify table-specific methodological notes and revision policies before interpretation. |
| Eurostat | https://ec.europa.eu/eurostat/databrowser/ | Monthly / Quarterly / Annual (dataset-dependent) | Respect dataset metadata, flags, and country comparability caveats. |
| FRED (Federal Reserve Bank of St. Louis) | https://fred.stlouisfed.org | Daily / Monthly (series-dependent) | FRED redistributes upstream series; check original-source terms for each series. |
| OECD Stats | https://stats.oecd.org/ | Monthly / Quarterly / Annual (dataset-dependent) | Monitor definition changes and back revisions in OECD datasets. |
| Banco de Portugal | https://www.bportugal.pt/estatisticas/dados | Daily / Monthly (series-dependent) | Confirm usage terms and transformation notes per endpoint/table. |
| REN (Redes Energéticas Nacionais) | https://datahub.ren.pt/app/pt/producao/ | Daily / Monthly (dataset-dependent) | Data publication methods may change; validate extraction assumptions periodically. |
| E-REDES | https://www.e-redes.pt/pt-pt | Daily / Monthly (dataset-dependent) | Availability/format may vary; keep parser logic defensive. |
| DGEG (Direção-Geral de Energia e Geologia) | https://www.dgeg.gov.pt/media/ | Weekly / Monthly (dataset-dependent) | Confirm fuel/energy dataset scope and any licensing notes on publication pages. |
| World Bank Data | https://data.worldbank.org/ | Annual (most indicators) | Cross-country indicators can be revised; track indicator metadata and footnotes. |

## Notes

- Cadence values above are indicative and can vary by specific indicator.
- For any newly added source, append a row here in the same format and include explicit terms/licensing notes when available.
