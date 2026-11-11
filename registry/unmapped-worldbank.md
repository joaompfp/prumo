# World Bank — unmapped / inactivated series (Task 13, 2026-11-11)

Truthful dispositions for `source: worldbank`. `registry/core.yaml` stays authoritative; this file
is the documented list the registry changes refer to. Nothing here rewrites ids, units, roles,
keys or geographies.

## Native identity format (all 982 World Bank series)

`native_code: <WDI indicator code>:<publisher ISO3 country code>` — e.g.
`NY.GDP.MKTP.CD:PRT`. The indicator code is the publisher's native indicator identifier; the ISO3
country/aggregate code is the publisher's native geography identifier. The pair is the full
publisher series identity and is unique per active series (tested).

- ISO3 codes are derived from the publisher's own country metadata,
  `GET https://api.worldbank.org/v2/country?format=json&per_page=400` (HTTP 200, 113 954 bytes,
  sha256 c9acf3932785191a649cbc04c3056af4cf64a236e5c3b49d49be25ddb0440bce, archived in
  `tests/ingest/fixtures/worldbank/country-metadata.json`): every one of the 54 registry
  geography codes maps 1:1 via the metadata's `iso2Code` → `id` (ISO3). Spot-verified aggregates:
  EU → EUU ("European Union"), GR → GRC, PT → PRT, AT → AUT. No hand-guessed ISO2→ISO3 table.
- The full list of the 54 geographies and their ISO3 publisher codes:
  AO AGO · AR ARG · AT AUT · BE BEL · BG BGR · BR BRA · CA CAN · CH CHE · CL CHL · CN CHN ·
  CV CPV · CY CYP · CZ CZE · DE DEU · DK DNK · EE EST · EG EGY · ES ESP · EU EUU · FI FIN ·
  FR FRA · GB GBR · GR GRC · GW GNB · HR HRV · HU HUN · ID IDN · IE IRL · IN IND · IT ITA ·
  JP JPN · KR KOR · LT LTU · LU LUX · LV LVA · MT MLT · MX MEX · MY MYS · MZ MOZ · NG NGA ·
  NL NLD · NO NOR · PL POL · PT PRT · RO ROU · SE SWE · SI SVN · SK SVK · ST STP · TH THA ·
  TL TLS · TR TUR · US USA · ZA ZAF
- Indicator codes are the ones already recorded on the 960 entries that carried a `native_code`;
  the 22 entries that lacked one (listed below) were filled from the reviewed concept↔indicator
  map (1:1 and consistent across all 960 pre-existing entries — no interpretation):

  | concept (id segment) | indicator |
  |---|---|
  | gdp_usd | NY.GDP.MKTP.CD |
  | gdp_growth | NY.GDP.MKTP.KD.ZG |
  | gdp_per_capita | NY.GDP.PCAP.CD |
  | gdp_per_capita_ppp | NY.GDP.PCAP.PP.CD |
  | unemployment_wb | SL.UEM.TOTL.ZS |
  | employment_rate | SL.EMP.TOTL.SP.ZS |
  | female_labor_participation | SL.TLF.CACT.FE.ZS |
  | urbanization | SP.URB.TOTL.IN.ZS |
  | exports_pct_gdp | NE.EXP.GNFS.ZS |
  | imports_pct_gdp | NE.IMP.GNFS.ZS |
  | trade_balance_pct_gdp | NE.RSB.GNFS.ZS |
  | fdi_inflows_pct_gdp | BX.KLT.DINV.WD.GD.ZS |
  | gov_debt_pct_gdp_wb | GC.DOD.TOTL.GD.ZS |
  | rnd_pct_gdp | GB.XPD.RSDV.GD.ZS |
  | gini | SI.POV.GINI |
  | population | SP.POP.TOTL |
  | birth_rate | SP.DYN.CBRT.IN |
  | death_rate | SP.DYN.CDRT.IN |
  | life_expectancy | SP.DYN.LE00.IN |

- `url` per series is the canonical institution series endpoint
  `https://api.worldbank.org/v2/country/<ISO3>/indicator/<CODE>` (the publisher's own series
  address; also the identity the CSV export exposes as `Country Code` + `Indicator Code`).
- The 22 previously code-less entries (researcher claim "all EU/GR" was wrong — the set INCLUDES
  `worldbank.unemployment_wb.AT`, an AT entry, plus 21 EU/GR entries):
  worldbank.unemployment_wb.AT, worldbank.unemployment_wb.EU, worldbank.unemployment_wb.GR,
  worldbank.birth_rate.EU, worldbank.birth_rate.GR, worldbank.death_rate.EU,
  worldbank.death_rate.GR, worldbank.employment_rate.EU, worldbank.employment_rate.GR,
  worldbank.gdp_growth.EU, worldbank.gdp_growth.GR, worldbank.gdp_per_capita.EU,
  worldbank.gdp_per_capita.GR, worldbank.gdp_per_capita_ppp.EU, worldbank.gdp_usd.EU,
  worldbank.gdp_usd.GR, worldbank.life_expectancy.EU, worldbank.life_expectancy.GR,
  worldbank.population.EU, worldbank.population.GR, worldbank.urbanization.EU,
  worldbank.urbanization.GR.

## Unit-definition conflict — gdp_per_capita_ppp inactivated (52 series)

Publisher metadata for `NY.GDP.PCAP.PP.CD`
(`GET https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.PP.CD?format=json`, HTTP 200, 2 659
bytes, sha256 a95c4834552a80e2c6b755c22e887d401d7930c2b97453f76fc063108a4a1a8d, archived in
`tests/ingest/fixtures/worldbank/meta-NY.GDP.PCAP.PP.CD.json`) publishes the name
**"GDP per capita, PPP (current international $)"** and its sourceNote states explicitly: "This
indicator is expressed in current prices, meaning no adjustment has been made to account for
price changes over time."

The registry unit on all 52 `gdp_per_capita_ppp` series is `USD (2017 PPC)` (51 series) or
`USD (2017)` (worldbank.gdp_per_capita_ppp.EU): both declare **constant 2017** prices. Current
international dollars are not constant-2017 international dollars, so the registry definition
contradicts what the publisher serves. Per the standing rule (never reinterpret/swap/convert
silently), ALL 52 series are `active: false` with this entry as their documented reason. The
owner may re-add a freshly defined series under a correct unit (or re-establish these ids under a
correct definition) in a separate reviewed change; no such change was made here. Note the
publisher also publishes `NY.GDP.PCAP.PP.KD` ("GDP per capita, PPP (constant 2021 international
$)") — a *different* indicator with a 2021 base, which is NOT a substitute for "USD (2017)"; it
was deliberately not substituted.

The 52 inactivated series (ids preserved, units/roles/keys untouched):

- worldbank.gdp_per_capita_ppp.AO
- worldbank.gdp_per_capita_ppp.AR
- worldbank.gdp_per_capita_ppp.AT
- worldbank.gdp_per_capita_ppp.BE
- worldbank.gdp_per_capita_ppp.BG
- worldbank.gdp_per_capita_ppp.BR
- worldbank.gdp_per_capita_ppp.CA
- worldbank.gdp_per_capita_ppp.CH
- worldbank.gdp_per_capita_ppp.CL
- worldbank.gdp_per_capita_ppp.CN
- worldbank.gdp_per_capita_ppp.CV
- worldbank.gdp_per_capita_ppp.CY
- worldbank.gdp_per_capita_ppp.CZ
- worldbank.gdp_per_capita_ppp.DE
- worldbank.gdp_per_capita_ppp.DK
- worldbank.gdp_per_capita_ppp.EE
- worldbank.gdp_per_capita_ppp.EG
- worldbank.gdp_per_capita_ppp.ES
- worldbank.gdp_per_capita_ppp.EU
- worldbank.gdp_per_capita_ppp.FI
- worldbank.gdp_per_capita_ppp.FR
- worldbank.gdp_per_capita_ppp.GB
- worldbank.gdp_per_capita_ppp.GW
- worldbank.gdp_per_capita_ppp.HR
- worldbank.gdp_per_capita_ppp.HU
- worldbank.gdp_per_capita_ppp.ID
- worldbank.gdp_per_capita_ppp.IE
- worldbank.gdp_per_capita_ppp.IN
- worldbank.gdp_per_capita_ppp.IT
- worldbank.gdp_per_capita_ppp.JP
- worldbank.gdp_per_capita_ppp.KR
- worldbank.gdp_per_capita_ppp.LU
- worldbank.gdp_per_capita_ppp.LV
- worldbank.gdp_per_capita_ppp.MT
- worldbank.gdp_per_capita_ppp.MX
- worldbank.gdp_per_capita_ppp.MY
- worldbank.gdp_per_capita_ppp.MZ
- worldbank.gdp_per_capita_ppp.NG
- worldbank.gdp_per_capita_ppp.NL
- worldbank.gdp_per_capita_ppp.NO
- worldbank.gdp_per_capita_ppp.PL
- worldbank.gdp_per_capita_ppp.PT
- worldbank.gdp_per_capita_ppp.RO
- worldbank.gdp_per_capita_ppp.SE
- worldbank.gdp_per_capita_ppp.SI
- worldbank.gdp_per_capita_ppp.SK
- worldbank.gdp_per_capita_ppp.ST
- worldbank.gdp_per_capita_ppp.TH
- worldbank.gdp_per_capita_ppp.TL
- worldbank.gdp_per_capita_ppp.TR
- worldbank.gdp_per_capita_ppp.US
- worldbank.gdp_per_capita_ppp.ZA

No further unit/definition conflicts were found among the other 18 indicators (audit of all 19
indicator metadata endpoints, 2026-11-11, archived under `tests/ingest/fixtures/worldbank/meta-*.json`):
units are registry declarations checked against `sourceNote` prose; the unit cross-label table
(English/Portuguese spellings of the same publisher unit — e.g. `%`/`% PIB`, `hab.`/`persons`,
`/1000`/`per_1000`, `anos`/`years`, Gini `0-100`) is codified and justified in
`tests/ingest/test_registry_worldbank_units.py`. Registry unit labels are NOT normalized.

## Licence

CC BY 4.0 as recorded (`redistribution_ok: true`), re-confirmed 2026-11-11: the WDI public.license
is CC BY 4.0 (licence_url); reviewed indicator metadata (`sourceOrganization`) cites originators
(national statistical offices, OECD, UNESCO/UIS, IMF, UN) as data provenance only — no per-series
licence exception found. Attribution string kept: `Source: World Bank`.
