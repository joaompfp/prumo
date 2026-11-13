# Sources and primary indicators

Generated from the selected registry by `python -m ingest docs`. Do not edit by hand.
Regenerate the committed catalogue: `python -m ingest docs > docs/data/sources.md`.
Select another registry: `python -m ingest --registry PATH docs` (stdout only).

This is registry policy and reviewed channel documentation, not a production status report.
The core registry remains provisional pending owner review. Inactive definitions and
cross-checks are retained below; a primary role does not imply active ingestion.
Licence eligibility is the registry's redistribution_ok flag, not a new legal assessment.
Serving also requires the pipeline's verification and row-eligibility gates.
Channel descriptions document reviewed code, not a fresh endpoint check or independent
verification of every unsampled observation. Unknown channels stay undocumented.

## bportugal

Licence: BPstat legal notices — free use with attribution &#40;exact reproduction, modifications must be marked&#41;
Licence URL: https://bpstat.bportugal.pt/avisos-legais
Attribution: Fonte: Banco de Portugal
Licence eligibility: allowed by registry (redistribution_ok=true).
Independent verification policy: verifiable=true.
Registry entries: 10 (10 active, 0 inactive).

Independent verification channel: Collector: BPstat public JSON-stat API /data/v1/. Independent channel: portal JSON row records at https://bpstat.bportugal.pt/api/observations/ plus /api/series/?view&#95;full=true metadata. Latest publication vintage is selected. No observation-status surface. Reviewed implementation: ingest/verifiers/bportugal.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| bportugal.credit&#95;consumer.PT | credit&#95;consumer.PT.M | primary | active | 12557382:19/28b6a921e1a4a9e326e724ab3e043d97 |
| bportugal.credit&#95;housing.PT | credit&#95;housing.PT.M | primary | active | 12557378:19/28b6a921e1a4a9e326e724ab3e043d97 |
| bportugal.de&#95;10y.DE | de&#95;10y.DE.M | primary | active | 12560098:26/690b7b36fd36c0dbe249c48cbbc39524 |
| bportugal.deposits&#95;households.PT | deposits&#95;households.PT.M | primary | active | 12556700:19/d5bf6198a39f1e77b0d14dda97103de0 |
| bportugal.eur&#95;usd.EA | eur&#95;usd.EA.M | primary | active | 12531993:29/23e0cdd56bddb4ad3016a9c3ad63a539 |
| bportugal.euribor&#95;12m.EA | euribor&#95;12m.EA.M | primary | active | 13168437:22/2829cb9155cb4f6ba6906db6b204c4bc |
| bportugal.euribor&#95;1m.EA | euribor&#95;1m.EA.M | primary | active | 13168439:22/2829cb9155cb4f6ba6906db6b204c4bc |
| bportugal.euribor&#95;3m.EA | euribor&#95;3m.EA.M | primary | active | 13168436:22/2829cb9155cb4f6ba6906db6b204c4bc |
| bportugal.euribor&#95;6m.EA | euribor&#95;6m.EA.M | primary | active | 13168438:22/2829cb9155cb4f6ba6906db6b204c4bc |
| bportugal.pt&#95;10y.PT | pt&#95;10y.PT.M | primary | active | 12099464:26/690b7b36fd36c0dbe249c48cbbc39524 |

## dgeg

Licence: UNVERIFIED — builder must confirm before serving
Licence URL: https://www.dgeg.gov.pt/
Attribution: Source: DGEG
Licence eligibility: withheld by registry (redistribution_ok=false).
Independent verification policy: verifiable=false.
Registry entries: 17 (0 active, 17 inactive).

Independent verification channel: Undocumented for current core definitions: no accepted exact independent channel and no ingest adapter/verifier. Partial APN/AEN PDF channels exist, but coverage, units, concepts and publication vintages remain unresolved. Scoped disposition and per-series evidence: registry/unmapped-dgeg.md.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| dgeg.co2&#95;emissions&#95;energy.PT | dgeg&#95;co2&#95;emissions&#95;energy.PT.A | primary | inactive | energy-data.db |
| dgeg.co2&#95;emissions&#95;total.PT | dgeg&#95;co2&#95;emissions&#95;total.PT.A | primary | inactive | energy-data.db |
| dgeg.consumption&#95;industry.PT | dgeg&#95;consumption&#95;industry.PT.A | primary | inactive | energy-data.db |
| dgeg.consumption&#95;primary&#95;total.PT | dgeg&#95;consumption&#95;primary&#95;total.PT.A | primary | inactive | energy-data.db |
| dgeg.consumption&#95;transport.PT | dgeg&#95;consumption&#95;transport.PT.A | primary | inactive | energy-data.db |
| dgeg.electricity&#95;consumption.PT | dgeg&#95;electricity&#95;consumption.PT.A | primary | inactive | energy-data.db |
| dgeg.energy&#95;dependence.PT | dgeg&#95;energy&#95;dependence.PT.A | primary | inactive | energy-data.db |
| dgeg.energy&#95;intensity.PT | dgeg&#95;energy&#95;intensity.PT.A | primary | inactive | energy-data.db |
| dgeg.energy&#95;intensity&#95;final.PT | dgeg&#95;energy&#95;intensity&#95;final.PT.A | primary | inactive | energy-data.db |
| dgeg.energy&#95;intensity&#95;industry.PT | dgeg&#95;energy&#95;intensity&#95;industry.PT.A | primary | inactive | energy-data.db |
| dgeg.energy&#95;intensity&#95;primary.PT | dgeg&#95;energy&#95;intensity&#95;primary.PT.A | primary | inactive | energy-data.db |
| dgeg.energy&#95;intensity&#95;services.PT | dgeg&#95;energy&#95;intensity&#95;services.PT.A | primary | inactive | energy-data.db |
| dgeg.final&#95;energy&#95;consumption.PT | dgeg&#95;final&#95;energy&#95;consumption.PT.A | primary | inactive | energy-data.db |
| dgeg.primary&#95;energy&#95;consumption.PT | dgeg&#95;primary&#95;energy&#95;consumption.PT.A | primary | inactive | energy-data.db |
| dgeg.renewable&#95;share&#95;electricity.PT | dgeg&#95;renewable&#95;share&#95;electricity.PT.A | primary | inactive | energy-data.db |
| dgeg.renewable&#95;share&#95;total.PT | dgeg&#95;renewable&#95;share&#95;total.PT.A | primary | inactive | energy-data.db |
| dgeg.renewable&#95;share&#95;transport.PT | dgeg&#95;renewable&#95;share&#95;transport.PT.A | primary | inactive | energy-data.db |

## eredes

Licence: CC BY 4.0
Licence URL: https://creativecommons.org/licenses/by/4.0/
Attribution: Source: E-REDES — Distribuição de Eletricidade, "E-REDES Open Data Portal"
Licence eligibility: allowed by registry (redistribution_ok=true).
Independent verification policy: verifiable=true.
Registry entries: 3 (3 active, 0 inactive).

Independent verification channel: Collector: OpenDataSoft explore v2.1 JSON records. Independent channel: https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/energia-produzida-total-nacional/exports/csv?lang=pt&amp;timezone=UTC, one CSV per sampled UTC day, plus dataset metadata for units. Native quarter-hour timestamps are retained; no observation-status surface. Reviewed implementation: ingest/verifiers/eredes.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| eredes.production&#95;market.PT | eredes&#95;production&#95;market.PT.PT15M | primary | active | energia-produzida-total-nacional:dgm |
| eredes.production&#95;special.PT | eredes&#95;production&#95;special.PT.PT15M | primary | active | energia-produzida-total-nacional:pre |
| eredes.production&#95;total.PT | eredes&#95;production&#95;total.PT.PT15M | primary | active | energia-produzida-total-nacional:total |

## eurostat

Licence: CC BY 4.0
Licence URL: https://ec.europa.eu/eurostat/web/main/help/copyright-notice
Attribution: Source: Eurostat
Licence eligibility: allowed by registry (redistribution_ok=true).
Independent verification policy: verifiable=true.
Registry entries: 697 (329 active, 368 inactive).

Independent verification channel: Collector: Statistics API 1.0 JSON-stat. Independent channel: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/&lt;dataset&gt;/&lt;key&gt;?format=TSV &#40;SDMX 2.1 TSV&#41;. Values and flags are read independently; unit identity is pinned by the native key, not a separate observed unit label. Reviewed implementation: ingest/verifiers/eurostat.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| eurostat.STS&#95;INPR&#95;M&#95;BD.CZ | ipi&#95;total.CZ.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=B-D,s&#95;adj=SCA,unit=I21,geo=CZ |
| eurostat.STS&#95;INPR&#95;M&#95;BD.DE | ipi&#95;total.DE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=B-D,s&#95;adj=SCA,unit=I21,geo=DE |
| eurostat.STS&#95;INPR&#95;M&#95;BD.PT | ipi&#95;total.PT.M | cross&#95;check | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=B-D,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.STS&#95;INPR&#95;M&#95;C.AT | ipi&#95;manufacturing.AT.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=AT |
| eurostat.STS&#95;INPR&#95;M&#95;C.BE | ipi&#95;manufacturing.BE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=BE |
| eurostat.STS&#95;INPR&#95;M&#95;C.BG | ipi&#95;manufacturing.BG.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=BG |
| eurostat.STS&#95;INPR&#95;M&#95;C.CY | ipi&#95;manufacturing.CY.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=CY |
| eurostat.STS&#95;INPR&#95;M&#95;C.CZ | ipi&#95;manufacturing.CZ.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=CZ |
| eurostat.STS&#95;INPR&#95;M&#95;C.DE | ipi&#95;manufacturing.DE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=DE |
| eurostat.STS&#95;INPR&#95;M&#95;C.DK | ipi&#95;manufacturing.DK.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=DK |
| eurostat.STS&#95;INPR&#95;M&#95;C.EE | ipi&#95;manufacturing.EE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=EE |
| eurostat.STS&#95;INPR&#95;M&#95;C.EL | ipi&#95;manufacturing.EL.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=EL |
| eurostat.STS&#95;INPR&#95;M&#95;C.ES | ipi&#95;manufacturing.ES.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=ES |
| eurostat.STS&#95;INPR&#95;M&#95;C.EU27 | ipi&#95;manufacturing.EU27.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=EU27&#95;2020 |
| eurostat.STS&#95;INPR&#95;M&#95;C.FI | ipi&#95;manufacturing.FI.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=FI |
| eurostat.STS&#95;INPR&#95;M&#95;C.FR | ipi&#95;manufacturing.FR.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=FR |
| eurostat.STS&#95;INPR&#95;M&#95;C.HR | ipi&#95;manufacturing.HR.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=HR |
| eurostat.STS&#95;INPR&#95;M&#95;C.HU | ipi&#95;manufacturing.HU.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=HU |
| eurostat.STS&#95;INPR&#95;M&#95;C.IE | ipi&#95;manufacturing.IE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=IE |
| eurostat.STS&#95;INPR&#95;M&#95;C.IT | ipi&#95;manufacturing.IT.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=IT |
| eurostat.STS&#95;INPR&#95;M&#95;C.LT | ipi&#95;manufacturing.LT.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=LT |
| eurostat.STS&#95;INPR&#95;M&#95;C.LU | ipi&#95;manufacturing.LU.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=LU |
| eurostat.STS&#95;INPR&#95;M&#95;C.LV | ipi&#95;manufacturing.LV.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=LV |
| eurostat.STS&#95;INPR&#95;M&#95;C.MT | ipi&#95;manufacturing.MT.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=MT |
| eurostat.STS&#95;INPR&#95;M&#95;C.NL | ipi&#95;manufacturing.NL.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=NL |
| eurostat.STS&#95;INPR&#95;M&#95;C.PL | ipi&#95;manufacturing.PL.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=PL |
| eurostat.STS&#95;INPR&#95;M&#95;C.PT | ipi&#95;manufacturing.PT.M | cross&#95;check | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.STS&#95;INPR&#95;M&#95;C.RO | ipi&#95;manufacturing.RO.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=RO |
| eurostat.STS&#95;INPR&#95;M&#95;C.SE | ipi&#95;manufacturing.SE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=SE |
| eurostat.STS&#95;INPR&#95;M&#95;C.SI | ipi&#95;manufacturing.SI.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=SI |
| eurostat.STS&#95;INPR&#95;M&#95;C.SK | ipi&#95;manufacturing.SK.M | primary | inactive | Not specified |
| eurostat.STS&#95;INPR&#95;M&#95;C20C21.CZ | ipi&#95;c20&#95;c21.CZ.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I21,geo=CZ |
| eurostat.STS&#95;INPR&#95;M&#95;C20C21.DE | ipi&#95;c20&#95;c21.DE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I21,geo=DE |
| eurostat.STS&#95;INPR&#95;M&#95;C20C21.PT | ipi&#95;c20&#95;c21.PT.M | cross&#95;check | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.CZ | ipi&#95;c29&#95;c30.CZ.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=CZ |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.DE | ipi&#95;c29&#95;c30.DE.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=DE |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.ES | ipi&#95;c29&#95;c30.ES.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=ES |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.EU27 | ipi&#95;c29&#95;c30.EU27.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=EU27&#95;2020 |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.FR | ipi&#95;c29&#95;c30.FR.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=FR |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.HU | ipi&#95;c29&#95;c30.HU.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=HU |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.PL | ipi&#95;c29&#95;c30.PL.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=PL |
| eurostat.STS&#95;INPR&#95;M&#95;C29C30.PT | ipi&#95;c29&#95;c30.PT.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.cci.AT | consumer&#95;confidence.AT.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=AT |
| eurostat.cci.BE | consumer&#95;confidence.BE.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=BE |
| eurostat.cci.BG | consumer&#95;confidence.BG.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=BG |
| eurostat.cci.CY | consumer&#95;confidence.CY.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=CY |
| eurostat.cci.CZ | consumer&#95;confidence.CZ.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=CZ |
| eurostat.cci.DE | consumer&#95;confidence.DE.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=DE |
| eurostat.cci.DK | consumer&#95;confidence.DK.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=DK |
| eurostat.cci.EE | consumer&#95;confidence.EE.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=EE |
| eurostat.cci.EL | consumer&#95;confidence.EL.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=EL |
| eurostat.cci.ES | consumer&#95;confidence.ES.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=ES |
| eurostat.cci.EU27&#95;2020 | consumer&#95;confidence.EU27&#95;2020.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=EU27&#95;2020 |
| eurostat.cci.FI | consumer&#95;confidence.FI.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=FI |
| eurostat.cci.FR | consumer&#95;confidence.FR.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=FR |
| eurostat.cci.HR | consumer&#95;confidence.HR.M | primary | inactive | Not specified |
| eurostat.cci.HU | consumer&#95;confidence.HU.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=HU |
| eurostat.cci.IE | consumer&#95;confidence.IE.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=IE |
| eurostat.cci.IT | consumer&#95;confidence.IT.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=IT |
| eurostat.cci.LT | consumer&#95;confidence.LT.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=LT |
| eurostat.cci.LU | consumer&#95;confidence.LU.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=LU |
| eurostat.cci.LV | consumer&#95;confidence.LV.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=LV |
| eurostat.cci.MT | consumer&#95;confidence.MT.M | primary | inactive | Not specified |
| eurostat.cci.NL | consumer&#95;confidence.NL.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=NL |
| eurostat.cci.PL | consumer&#95;confidence.PL.M | primary | inactive | Not specified |
| eurostat.cci.PT | consumer&#95;confidence.PT.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=PT |
| eurostat.cci.RO | consumer&#95;confidence.RO.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=RO |
| eurostat.cci.SE | consumer&#95;confidence.SE.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=SE |
| eurostat.cci.SI | consumer&#95;confidence.SI.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=SI |
| eurostat.cci.SK | consumer&#95;confidence.SK.M | primary | active | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=SK |
| eurostat.chemicals&#95;pharma.PT | ipi&#95;c20&#95;c21.PT.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.construction&#95;index.AT | eurostat&#95;construction&#95;index.AT.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=AT |
| eurostat.construction&#95;index.BE | eurostat&#95;construction&#95;index.BE.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.construction&#95;index.BG | eurostat&#95;construction&#95;index.BG.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.construction&#95;index.CZ | eurostat&#95;construction&#95;index.CZ.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.construction&#95;index.DE | eurostat&#95;construction&#95;index.DE.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=DE |
| eurostat.construction&#95;index.DK | eurostat&#95;construction&#95;index.DK.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.construction&#95;index.ES | eurostat&#95;construction&#95;index.ES.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=ES |
| eurostat.construction&#95;output.AT | eurostat&#95;construction&#95;output.AT.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=AT |
| eurostat.construction&#95;output.BE | eurostat&#95;construction&#95;output.BE.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.construction&#95;output.BG | eurostat&#95;construction&#95;output.BG.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.construction&#95;output.CZ | eurostat&#95;construction&#95;output.CZ.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.construction&#95;output.DE | eurostat&#95;construction&#95;output.DE.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=DE |
| eurostat.construction&#95;output.DK | eurostat&#95;construction&#95;output.DK.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.construction&#95;output.ES | eurostat&#95;construction&#95;output.ES.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=ES |
| eurostat.construction&#95;output.EU27&#95;2020 | eurostat&#95;construction&#95;output.EU27&#95;2020.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.construction&#95;output.FI | eurostat&#95;construction&#95;output.FI.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=FI |
| eurostat.construction&#95;output.FR | eurostat&#95;construction&#95;output.FR.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=FR |
| eurostat.construction&#95;output.HR | eurostat&#95;construction&#95;output.HR.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=HR |
| eurostat.construction&#95;output.HU | eurostat&#95;construction&#95;output.HU.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.construction&#95;output.IT | eurostat&#95;construction&#95;output.IT.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=IT |
| eurostat.construction&#95;output.LU | eurostat&#95;construction&#95;output.LU.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=LU |
| eurostat.construction&#95;output.NL | eurostat&#95;construction&#95;output.NL.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.construction&#95;output.PL | eurostat&#95;construction&#95;output.PL.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.construction&#95;output.RO | eurostat&#95;construction&#95;output.RO.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.construction&#95;output.SE | eurostat&#95;construction&#95;output.SE.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.construction&#95;output.SI | eurostat&#95;construction&#95;output.SI.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=SI |
| eurostat.construction&#95;output.SK | eurostat&#95;construction&#95;output.SK.M | primary | inactive | sts&#95;copr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=F,s&#95;adj=SCA,unit=I15,geo=SK |
| eurostat.consumer&#95;confidence.BG | consumer&#95;confidence.BG.M | cross&#95;check | inactive | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=BG |
| eurostat.consumer&#95;confidence.CY | consumer&#95;confidence.CY.M | cross&#95;check | inactive | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=CY |
| eurostat.consumer&#95;confidence.HR | consumer&#95;confidence.HR.M | cross&#95;check | inactive | Not specified |
| eurostat.consumer&#95;confidence.LT | consumer&#95;confidence.LT.M | cross&#95;check | inactive | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=LT |
| eurostat.consumer&#95;confidence.LU | consumer&#95;confidence.LU.M | cross&#95;check | inactive | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=LU |
| eurostat.consumer&#95;confidence.MT | consumer&#95;confidence.MT.M | cross&#95;check | inactive | Not specified |
| eurostat.consumer&#95;confidence.PL | consumer&#95;confidence.PL.M | cross&#95;check | inactive | Not specified |
| eurostat.consumer&#95;confidence.RO | consumer&#95;confidence.RO.M | cross&#95;check | inactive | ei&#95;bsco&#95;m:freq=M,indic=BS-CSMCI,s&#95;adj=SA,unit=BAL,geo=RO |
| eurostat.current&#95;account&#95;pct&#95;gdp.AT | eurostat&#95;current&#95;account&#95;pct&#95;gdp.AT.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.BE | eurostat&#95;current&#95;account&#95;pct&#95;gdp.BE.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.BG | eurostat&#95;current&#95;account&#95;pct&#95;gdp.BG.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.CY | eurostat&#95;current&#95;account&#95;pct&#95;gdp.CY.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.CZ | eurostat&#95;current&#95;account&#95;pct&#95;gdp.CZ.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.DE | eurostat&#95;current&#95;account&#95;pct&#95;gdp.DE.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.DK | eurostat&#95;current&#95;account&#95;pct&#95;gdp.DK.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.EE | eurostat&#95;current&#95;account&#95;pct&#95;gdp.EE.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.EL | eurostat&#95;current&#95;account&#95;pct&#95;gdp.EL.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.ES | eurostat&#95;current&#95;account&#95;pct&#95;gdp.ES.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.FI | eurostat&#95;current&#95;account&#95;pct&#95;gdp.FI.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.FR | eurostat&#95;current&#95;account&#95;pct&#95;gdp.FR.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.HR | eurostat&#95;current&#95;account&#95;pct&#95;gdp.HR.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.HU | eurostat&#95;current&#95;account&#95;pct&#95;gdp.HU.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.IE | eurostat&#95;current&#95;account&#95;pct&#95;gdp.IE.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.IT | eurostat&#95;current&#95;account&#95;pct&#95;gdp.IT.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.LT | eurostat&#95;current&#95;account&#95;pct&#95;gdp.LT.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.LU | eurostat&#95;current&#95;account&#95;pct&#95;gdp.LU.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.LV | eurostat&#95;current&#95;account&#95;pct&#95;gdp.LV.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.MT | eurostat&#95;current&#95;account&#95;pct&#95;gdp.MT.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.NL | eurostat&#95;current&#95;account&#95;pct&#95;gdp.NL.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.PL | eurostat&#95;current&#95;account&#95;pct&#95;gdp.PL.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.PT | eurostat&#95;current&#95;account&#95;pct&#95;gdp.PT.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.RO | eurostat&#95;current&#95;account&#95;pct&#95;gdp.RO.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.SE | eurostat&#95;current&#95;account&#95;pct&#95;gdp.SE.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.SI | eurostat&#95;current&#95;account&#95;pct&#95;gdp.SI.Q | primary | inactive | Not specified |
| eurostat.current&#95;account&#95;pct&#95;gdp.SK | eurostat&#95;current&#95;account&#95;pct&#95;gdp.SK.Q | primary | inactive | Not specified |
| eurostat.electricity&#95;price&#95;household.AT | eurostat&#95;electricity&#95;price&#95;household.AT.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=AT |
| eurostat.electricity&#95;price&#95;household.BE | eurostat&#95;electricity&#95;price&#95;household.BE.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=BE |
| eurostat.electricity&#95;price&#95;household.BG | eurostat&#95;electricity&#95;price&#95;household.BG.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=BG |
| eurostat.electricity&#95;price&#95;household.CY | eurostat&#95;electricity&#95;price&#95;household.CY.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=CY |
| eurostat.electricity&#95;price&#95;household.CZ | eurostat&#95;electricity&#95;price&#95;household.CZ.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=CZ |
| eurostat.electricity&#95;price&#95;household.DE | eurostat&#95;electricity&#95;price&#95;household.DE.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=DE |
| eurostat.electricity&#95;price&#95;household.DK | eurostat&#95;electricity&#95;price&#95;household.DK.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=DK |
| eurostat.electricity&#95;price&#95;household.EE | eurostat&#95;electricity&#95;price&#95;household.EE.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=EE |
| eurostat.electricity&#95;price&#95;household.EL | eurostat&#95;electricity&#95;price&#95;household.EL.S | primary | inactive | Not specified |
| eurostat.electricity&#95;price&#95;household.ES | eurostat&#95;electricity&#95;price&#95;household.ES.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=ES |
| eurostat.electricity&#95;price&#95;household.EU27 | eurostat&#95;electricity&#95;price&#95;household.EU27.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=EU27&#95;2020 |
| eurostat.electricity&#95;price&#95;household.EU27&#95;2020 | eurostat&#95;electricity&#95;price&#95;household.EU27&#95;2020.S | primary | inactive | Not specified |
| eurostat.electricity&#95;price&#95;household.FI | eurostat&#95;electricity&#95;price&#95;household.FI.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=FI |
| eurostat.electricity&#95;price&#95;household.FR | eurostat&#95;electricity&#95;price&#95;household.FR.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=FR |
| eurostat.electricity&#95;price&#95;household.GR | eurostat&#95;electricity&#95;price&#95;household.GR.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=EL |
| eurostat.electricity&#95;price&#95;household.HR | eurostat&#95;electricity&#95;price&#95;household.HR.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=HR |
| eurostat.electricity&#95;price&#95;household.HU | eurostat&#95;electricity&#95;price&#95;household.HU.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=HU |
| eurostat.electricity&#95;price&#95;household.IE | eurostat&#95;electricity&#95;price&#95;household.IE.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=IE |
| eurostat.electricity&#95;price&#95;household.IT | eurostat&#95;electricity&#95;price&#95;household.IT.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=IT |
| eurostat.electricity&#95;price&#95;household.LT | eurostat&#95;electricity&#95;price&#95;household.LT.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=LT |
| eurostat.electricity&#95;price&#95;household.LU | eurostat&#95;electricity&#95;price&#95;household.LU.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=LU |
| eurostat.electricity&#95;price&#95;household.LV | eurostat&#95;electricity&#95;price&#95;household.LV.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=LV |
| eurostat.electricity&#95;price&#95;household.MT | eurostat&#95;electricity&#95;price&#95;household.MT.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=MT |
| eurostat.electricity&#95;price&#95;household.NL | eurostat&#95;electricity&#95;price&#95;household.NL.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=NL |
| eurostat.electricity&#95;price&#95;household.PL | eurostat&#95;electricity&#95;price&#95;household.PL.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=PL |
| eurostat.electricity&#95;price&#95;household.PT | eurostat&#95;electricity&#95;price&#95;household.PT.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=PT |
| eurostat.electricity&#95;price&#95;household.RO | eurostat&#95;electricity&#95;price&#95;household.RO.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=RO |
| eurostat.electricity&#95;price&#95;household.SE | eurostat&#95;electricity&#95;price&#95;household.SE.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=SE |
| eurostat.electricity&#95;price&#95;household.SI | eurostat&#95;electricity&#95;price&#95;household.SI.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=SI |
| eurostat.electricity&#95;price&#95;household.SK | eurostat&#95;electricity&#95;price&#95;household.SK.S | primary | active | nrg&#95;pc&#95;204:freq=S,siec=E7000,nrg&#95;cons=KWH2500-4999,unit=KWH,tax=I&#95;TAX,currency=EUR,geo=SK |
| eurostat.employment&#95;rate.AT | eurostat&#95;employment&#95;rate.AT.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.BE | eurostat&#95;employment&#95;rate.BE.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.BG | eurostat&#95;employment&#95;rate.BG.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.CY | eurostat&#95;employment&#95;rate.CY.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.CZ | eurostat&#95;employment&#95;rate.CZ.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.DE | eurostat&#95;employment&#95;rate.DE.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.DK | eurostat&#95;employment&#95;rate.DK.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.EE | eurostat&#95;employment&#95;rate.EE.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.EL | eurostat&#95;employment&#95;rate.EL.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.ES | eurostat&#95;employment&#95;rate.ES.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.EU27&#95;2020 | eurostat&#95;employment&#95;rate.EU27&#95;2020.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.FI | eurostat&#95;employment&#95;rate.FI.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.FR | eurostat&#95;employment&#95;rate.FR.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.HR | eurostat&#95;employment&#95;rate.HR.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.HU | eurostat&#95;employment&#95;rate.HU.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.IE | eurostat&#95;employment&#95;rate.IE.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.IT | eurostat&#95;employment&#95;rate.IT.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.LT | eurostat&#95;employment&#95;rate.LT.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.LU | eurostat&#95;employment&#95;rate.LU.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.LV | eurostat&#95;employment&#95;rate.LV.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.MT | eurostat&#95;employment&#95;rate.MT.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.NL | eurostat&#95;employment&#95;rate.NL.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.PL | eurostat&#95;employment&#95;rate.PL.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.PT | eurostat&#95;employment&#95;rate.PT.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.RO | eurostat&#95;employment&#95;rate.RO.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.SE | eurostat&#95;employment&#95;rate.SE.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.SI | eurostat&#95;employment&#95;rate.SI.A | primary | inactive | Not specified |
| eurostat.employment&#95;rate.SK | eurostat&#95;employment&#95;rate.SK.A | primary | inactive | Not specified |
| eurostat.gdp&#95;per&#95;capita&#95;eur.AT | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.AT.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=AT |
| eurostat.gdp&#95;per&#95;capita&#95;eur.BE | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.BE.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=BE |
| eurostat.gdp&#95;per&#95;capita&#95;eur.BG | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.BG.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=BG |
| eurostat.gdp&#95;per&#95;capita&#95;eur.CY | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.CY.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=CY |
| eurostat.gdp&#95;per&#95;capita&#95;eur.CZ | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.CZ.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=CZ |
| eurostat.gdp&#95;per&#95;capita&#95;eur.DE | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.DE.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=DE |
| eurostat.gdp&#95;per&#95;capita&#95;eur.DK | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.DK.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=DK |
| eurostat.gdp&#95;per&#95;capita&#95;eur.EE | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.EE.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=EE |
| eurostat.gdp&#95;per&#95;capita&#95;eur.EL | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.EL.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=EL |
| eurostat.gdp&#95;per&#95;capita&#95;eur.ES | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.ES.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=ES |
| eurostat.gdp&#95;per&#95;capita&#95;eur.EU27&#95;2020 | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.EU27&#95;2020.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=EU27&#95;2020 |
| eurostat.gdp&#95;per&#95;capita&#95;eur.FI | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.FI.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=FI |
| eurostat.gdp&#95;per&#95;capita&#95;eur.FR | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.FR.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=FR |
| eurostat.gdp&#95;per&#95;capita&#95;eur.HR | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.HR.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=HR |
| eurostat.gdp&#95;per&#95;capita&#95;eur.HU | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.HU.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=HU |
| eurostat.gdp&#95;per&#95;capita&#95;eur.IE | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.IE.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=IE |
| eurostat.gdp&#95;per&#95;capita&#95;eur.IT | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.IT.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=IT |
| eurostat.gdp&#95;per&#95;capita&#95;eur.LT | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.LT.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=LT |
| eurostat.gdp&#95;per&#95;capita&#95;eur.LU | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.LU.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=LU |
| eurostat.gdp&#95;per&#95;capita&#95;eur.LV | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.LV.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=LV |
| eurostat.gdp&#95;per&#95;capita&#95;eur.MT | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.MT.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=MT |
| eurostat.gdp&#95;per&#95;capita&#95;eur.NL | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.NL.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=NL |
| eurostat.gdp&#95;per&#95;capita&#95;eur.PL | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.PL.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=PL |
| eurostat.gdp&#95;per&#95;capita&#95;eur.PT | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.PT.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=PT |
| eurostat.gdp&#95;per&#95;capita&#95;eur.RO | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.RO.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=RO |
| eurostat.gdp&#95;per&#95;capita&#95;eur.SE | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.SE.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=SE |
| eurostat.gdp&#95;per&#95;capita&#95;eur.SI | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.SI.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=SI |
| eurostat.gdp&#95;per&#95;capita&#95;eur.SK | eurostat&#95;gdp&#95;per&#95;capita&#95;eur.SK.A | primary | active | nama&#95;10&#95;pc:freq=A,unit=CP&#95;EUR&#95;HAB,na&#95;item=B1GQ,geo=SK |
| eurostat.gdp&#95;per&#95;capita&#95;pps.DE | eurostat&#95;gdp&#95;per&#95;capita&#95;pps.DE.A | primary | inactive | Not specified |
| eurostat.gdp&#95;per&#95;capita&#95;pps.ES | eurostat&#95;gdp&#95;per&#95;capita&#95;pps.ES.A | primary | inactive | Not specified |
| eurostat.gdp&#95;per&#95;capita&#95;pps.EU27&#95;2020 | eurostat&#95;gdp&#95;per&#95;capita&#95;pps.EU27&#95;2020.A | primary | inactive | Not specified |
| eurostat.gdp&#95;per&#95;capita&#95;pps.FR | eurostat&#95;gdp&#95;per&#95;capita&#95;pps.FR.A | primary | inactive | Not specified |
| eurostat.gdp&#95;per&#95;capita&#95;pps.PL | eurostat&#95;gdp&#95;per&#95;capita&#95;pps.PL.A | primary | inactive | Not specified |
| eurostat.gdp&#95;per&#95;capita&#95;pps.PT | eurostat&#95;gdp&#95;per&#95;capita&#95;pps.PT.A | primary | inactive | Not specified |
| eurostat.gdp&#95;quarterly.EU27 | eurostat&#95;gdp&#95;quarterly.EU27.Q | primary | active | namq&#95;10&#95;gdp:freq=Q,unit=CLV10&#95;MEUR,s&#95;adj=SCA,na&#95;item=B1GQ,geo=EU27&#95;2020 |
| eurostat.gdp&#95;quarterly.EU27&#95;2020 | eurostat&#95;gdp&#95;quarterly.EU27&#95;2020.A | primary | inactive | Not specified |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.AT | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.AT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=AT |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.BE | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.BE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=BE |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.BG | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.BG.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=BG |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.CY | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.CY.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=CY |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.CZ | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.CZ.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=CZ |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.DE | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.DE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=DE |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.DK | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.DK.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=DK |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.EE | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.EE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=EE |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.EL | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.EL.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=EL |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.ES | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.ES.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=ES |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.EU27&#95;2020 | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.EU27&#95;2020.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=EU27&#95;2020 |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.FI | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.FI.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=FI |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.FR | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.FR.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=FR |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.HR | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.HR.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=HR |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.HU | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.HU.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=HU |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.IE | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.IE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=IE |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.IT | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.IT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=IT |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.LT | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.LT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=LT |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.LU | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.LU.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=LU |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.LV | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.LV.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=LV |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.MT | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.MT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=MT |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.NL | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.NL.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=NL |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.PL | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.PL.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=PL |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.PT | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.PT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=PT |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.RO | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.RO.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=RO |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.SE | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.SE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=SE |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.SI | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.SI.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=SI |
| eurostat.gov&#95;debt&#95;pct&#95;gdp.SK | eurostat&#95;gov&#95;debt&#95;pct&#95;gdp.SK.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=GD,geo=SK |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.AT | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.AT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=AT |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.BE | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.BE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=BE |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.BG | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.BG.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=BG |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.CY | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.CY.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=CY |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.CZ | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.CZ.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=CZ |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.DE | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.DE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=DE |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.DK | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.DK.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=DK |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.EE | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.EE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=EE |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.EL | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.EL.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=EL |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.ES | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.ES.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=ES |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.EU27&#95;2020 | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.EU27&#95;2020.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=EU27&#95;2020 |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.FI | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.FI.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=FI |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.FR | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.FR.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=FR |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.HR | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.HR.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=HR |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.HU | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.HU.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=HU |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.IE | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.IE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=IE |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.IT | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.IT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=IT |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.LT | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.LT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=LT |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.LU | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.LU.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=LU |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.LV | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.LV.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=LV |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.MT | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.MT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=MT |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.NL | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.NL.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=NL |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.PL | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.PL.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=PL |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.PT | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.PT.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=PT |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.RO | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.RO.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=RO |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.SE | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.SE.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=SE |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.SI | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.SI.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=SI |
| eurostat.gov&#95;deficit&#95;pct&#95;gdp.SK | eurostat&#95;gov&#95;deficit&#95;pct&#95;gdp.SK.A | primary | active | gov&#95;10dd&#95;edpt1:freq=A,unit=PC&#95;GDP,sector=S13,na&#95;item=B9,geo=SK |
| eurostat.hicp.EU27 | eurostat&#95;hicp.EU27.M | primary | inactive | prc&#95;hicp&#95;midx:freq=M,unit=I15,coicop=CP00,geo=EU27&#95;2020 |
| eurostat.hicp.EU27&#95;2020 | eurostat&#95;hicp.EU27&#95;2020.M | primary | active | prc&#95;hicp&#95;midx:freq=M,unit=I15,coicop=CP00,geo=EU27&#95;2020 |
| eurostat.hourly&#95;labour&#95;cost&#95;index.DE | eurostat&#95;hourly&#95;labour&#95;cost&#95;index.DE.A | primary | active | lc&#95;lci&#95;r2&#95;a:freq=A,unit=I20,nace&#95;r2=B-N,lcstruct=D1&#95;D4&#95;MD5,geo=DE |
| eurostat.hourly&#95;labour&#95;cost&#95;index.ES | eurostat&#95;hourly&#95;labour&#95;cost&#95;index.ES.A | primary | active | lc&#95;lci&#95;r2&#95;a:freq=A,unit=I20,nace&#95;r2=B-N,lcstruct=D1&#95;D4&#95;MD5,geo=ES |
| eurostat.hourly&#95;labour&#95;cost&#95;index.EU27&#95;2020 | eurostat&#95;hourly&#95;labour&#95;cost&#95;index.EU27&#95;2020.A | primary | active | lc&#95;lci&#95;r2&#95;a:freq=A,unit=I20,nace&#95;r2=B-N,lcstruct=D1&#95;D4&#95;MD5,geo=EU27&#95;2020 |
| eurostat.hourly&#95;labour&#95;cost&#95;index.FR | eurostat&#95;hourly&#95;labour&#95;cost&#95;index.FR.A | primary | active | lc&#95;lci&#95;r2&#95;a:freq=A,unit=I20,nace&#95;r2=B-N,lcstruct=D1&#95;D4&#95;MD5,geo=FR |
| eurostat.hourly&#95;labour&#95;cost&#95;index.PL | eurostat&#95;hourly&#95;labour&#95;cost&#95;index.PL.A | primary | active | lc&#95;lci&#95;r2&#95;a:freq=A,unit=I20,nace&#95;r2=B-N,lcstruct=D1&#95;D4&#95;MD5,geo=PL |
| eurostat.hourly&#95;labour&#95;cost&#95;index.PT | eurostat&#95;hourly&#95;labour&#95;cost&#95;index.PT.A | primary | active | lc&#95;lci&#95;r2&#95;a:freq=A,unit=I20,nace&#95;r2=B-N,lcstruct=D1&#95;D4&#95;MD5,geo=PT |
| eurostat.ipi.PT | ipi&#95;total.PT.M | cross&#95;check | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=B-D,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.ipi&#95;chemicals&#95;pharma.AT | eurostat&#95;ipi&#95;chemicals&#95;pharma.AT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=AT |
| eurostat.ipi&#95;chemicals&#95;pharma.BE | eurostat&#95;ipi&#95;chemicals&#95;pharma.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;chemicals&#95;pharma.BG | eurostat&#95;ipi&#95;chemicals&#95;pharma.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;chemicals&#95;pharma.CZ | eurostat&#95;ipi&#95;chemicals&#95;pharma.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;chemicals&#95;pharma.DE | eurostat&#95;ipi&#95;chemicals&#95;pharma.DE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=DE |
| eurostat.ipi&#95;chemicals&#95;pharma.DK | eurostat&#95;ipi&#95;chemicals&#95;pharma.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;chemicals&#95;pharma.EE | eurostat&#95;ipi&#95;chemicals&#95;pharma.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;chemicals&#95;pharma.EL | eurostat&#95;ipi&#95;chemicals&#95;pharma.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;chemicals&#95;pharma.ES | eurostat&#95;ipi&#95;chemicals&#95;pharma.ES.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=ES |
| eurostat.ipi&#95;chemicals&#95;pharma.EU27&#95;2020 | eurostat&#95;ipi&#95;chemicals&#95;pharma.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;chemicals&#95;pharma.FR | eurostat&#95;ipi&#95;chemicals&#95;pharma.FR.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=FR |
| eurostat.ipi&#95;chemicals&#95;pharma.HU | eurostat&#95;ipi&#95;chemicals&#95;pharma.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;chemicals&#95;pharma.IE | eurostat&#95;ipi&#95;chemicals&#95;pharma.IE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=IE |
| eurostat.ipi&#95;chemicals&#95;pharma.IT | eurostat&#95;ipi&#95;chemicals&#95;pharma.IT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=IT |
| eurostat.ipi&#95;chemicals&#95;pharma.LT | eurostat&#95;ipi&#95;chemicals&#95;pharma.LT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=LT |
| eurostat.ipi&#95;chemicals&#95;pharma.LV | eurostat&#95;ipi&#95;chemicals&#95;pharma.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;chemicals&#95;pharma.NL | eurostat&#95;ipi&#95;chemicals&#95;pharma.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;chemicals&#95;pharma.PL | eurostat&#95;ipi&#95;chemicals&#95;pharma.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;chemicals&#95;pharma.PT | eurostat&#95;ipi&#95;chemicals&#95;pharma.PT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=PT |
| eurostat.ipi&#95;chemicals&#95;pharma.RO | eurostat&#95;ipi&#95;chemicals&#95;pharma.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;chemicals&#95;pharma.SE | eurostat&#95;ipi&#95;chemicals&#95;pharma.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C20&#95;C21,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;electronics.BE | eurostat&#95;ipi&#95;electronics.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;electronics.BG | eurostat&#95;ipi&#95;electronics.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;electronics.CZ | eurostat&#95;ipi&#95;electronics.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;electronics.DK | eurostat&#95;ipi&#95;electronics.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;electronics.EE | eurostat&#95;ipi&#95;electronics.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;electronics.EL | eurostat&#95;ipi&#95;electronics.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;electronics.HU | eurostat&#95;ipi&#95;electronics.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;electronics.LV | eurostat&#95;ipi&#95;electronics.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;electronics.NL | eurostat&#95;ipi&#95;electronics.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;electronics.PL | eurostat&#95;ipi&#95;electronics.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;electronics.RO | eurostat&#95;ipi&#95;electronics.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;electronics.SE | eurostat&#95;ipi&#95;electronics.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C26&#95;C27,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;food&#95;beverage.BE | eurostat&#95;ipi&#95;food&#95;beverage.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;food&#95;beverage.BG | eurostat&#95;ipi&#95;food&#95;beverage.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;food&#95;beverage.DK | eurostat&#95;ipi&#95;food&#95;beverage.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;food&#95;beverage.EE | eurostat&#95;ipi&#95;food&#95;beverage.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;food&#95;beverage.EL | eurostat&#95;ipi&#95;food&#95;beverage.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;food&#95;beverage.HU | eurostat&#95;ipi&#95;food&#95;beverage.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;food&#95;beverage.LV | eurostat&#95;ipi&#95;food&#95;beverage.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;food&#95;beverage.NL | eurostat&#95;ipi&#95;food&#95;beverage.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;food&#95;beverage.PL | eurostat&#95;ipi&#95;food&#95;beverage.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;food&#95;beverage.RO | eurostat&#95;ipi&#95;food&#95;beverage.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;food&#95;beverage.SE | eurostat&#95;ipi&#95;food&#95;beverage.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C10-C12,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;machinery.AT | eurostat&#95;ipi&#95;machinery.AT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=AT |
| eurostat.ipi&#95;machinery.BE | eurostat&#95;ipi&#95;machinery.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;machinery.BG | eurostat&#95;ipi&#95;machinery.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;machinery.CZ | eurostat&#95;ipi&#95;machinery.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;machinery.DE | eurostat&#95;ipi&#95;machinery.DE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=DE |
| eurostat.ipi&#95;machinery.DK | eurostat&#95;ipi&#95;machinery.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;machinery.EE | eurostat&#95;ipi&#95;machinery.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;machinery.EL | eurostat&#95;ipi&#95;machinery.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;machinery.ES | eurostat&#95;ipi&#95;machinery.ES.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=ES |
| eurostat.ipi&#95;machinery.EU27&#95;2020 | eurostat&#95;ipi&#95;machinery.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;machinery.FI | eurostat&#95;ipi&#95;machinery.FI.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=FI |
| eurostat.ipi&#95;machinery.FR | eurostat&#95;ipi&#95;machinery.FR.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=FR |
| eurostat.ipi&#95;machinery.HU | eurostat&#95;ipi&#95;machinery.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;machinery.IE | eurostat&#95;ipi&#95;machinery.IE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=IE |
| eurostat.ipi&#95;machinery.IT | eurostat&#95;ipi&#95;machinery.IT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=IT |
| eurostat.ipi&#95;machinery.LT | eurostat&#95;ipi&#95;machinery.LT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=LT |
| eurostat.ipi&#95;machinery.LV | eurostat&#95;ipi&#95;machinery.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;machinery.NL | eurostat&#95;ipi&#95;machinery.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;machinery.PL | eurostat&#95;ipi&#95;machinery.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;machinery.PT | eurostat&#95;ipi&#95;machinery.PT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=PT |
| eurostat.ipi&#95;machinery.RO | eurostat&#95;ipi&#95;machinery.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;machinery.SE | eurostat&#95;ipi&#95;machinery.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;manufacturing.EU27 | eurostat&#95;ipi&#95;manufacturing.EU27.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=EU27&#95;2020 |
| eurostat.ipi&#95;manufacturing.EU27&#95;2020 | eurostat&#95;ipi&#95;manufacturing.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;metals.AT | eurostat&#95;ipi&#95;metals.AT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=AT |
| eurostat.ipi&#95;metals.BE | eurostat&#95;ipi&#95;metals.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;metals.BG | eurostat&#95;ipi&#95;metals.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;metals.CZ | eurostat&#95;ipi&#95;metals.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;metals.DE | eurostat&#95;ipi&#95;metals.DE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=DE |
| eurostat.ipi&#95;metals.DK | eurostat&#95;ipi&#95;metals.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;metals.EE | eurostat&#95;ipi&#95;metals.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;metals.EL | eurostat&#95;ipi&#95;metals.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;metals.ES | eurostat&#95;ipi&#95;metals.ES.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=ES |
| eurostat.ipi&#95;metals.EU27&#95;2020 | eurostat&#95;ipi&#95;metals.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;metals.FI | eurostat&#95;ipi&#95;metals.FI.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=FI |
| eurostat.ipi&#95;metals.FR | eurostat&#95;ipi&#95;metals.FR.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=FR |
| eurostat.ipi&#95;metals.HU | eurostat&#95;ipi&#95;metals.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;metals.IE | eurostat&#95;ipi&#95;metals.IE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=IE |
| eurostat.ipi&#95;metals.IT | eurostat&#95;ipi&#95;metals.IT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=IT |
| eurostat.ipi&#95;metals.LT | eurostat&#95;ipi&#95;metals.LT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=LT |
| eurostat.ipi&#95;metals.LV | eurostat&#95;ipi&#95;metals.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;metals.NL | eurostat&#95;ipi&#95;metals.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;metals.PL | eurostat&#95;ipi&#95;metals.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;metals.PT | eurostat&#95;ipi&#95;metals.PT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=PT |
| eurostat.ipi&#95;metals.RO | eurostat&#95;ipi&#95;metals.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;metals.SE | eurostat&#95;ipi&#95;metals.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;nonmetallic.BE | eurostat&#95;ipi&#95;nonmetallic.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;nonmetallic.BG | eurostat&#95;ipi&#95;nonmetallic.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;nonmetallic.CZ | eurostat&#95;ipi&#95;nonmetallic.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;nonmetallic.DK | eurostat&#95;ipi&#95;nonmetallic.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;nonmetallic.EE | eurostat&#95;ipi&#95;nonmetallic.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;nonmetallic.EL | eurostat&#95;ipi&#95;nonmetallic.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;nonmetallic.EU27&#95;2020 | eurostat&#95;ipi&#95;nonmetallic.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;nonmetallic.HU | eurostat&#95;ipi&#95;nonmetallic.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;nonmetallic.IT | eurostat&#95;ipi&#95;nonmetallic.IT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=IT |
| eurostat.ipi&#95;nonmetallic.LV | eurostat&#95;ipi&#95;nonmetallic.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;nonmetallic.NL | eurostat&#95;ipi&#95;nonmetallic.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;nonmetallic.PL | eurostat&#95;ipi&#95;nonmetallic.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;nonmetallic.RO | eurostat&#95;ipi&#95;nonmetallic.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;nonmetallic.SE | eurostat&#95;ipi&#95;nonmetallic.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C23,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;rubber&#95;plastics.AT | eurostat&#95;ipi&#95;rubber&#95;plastics.AT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=AT |
| eurostat.ipi&#95;rubber&#95;plastics.BE | eurostat&#95;ipi&#95;rubber&#95;plastics.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;rubber&#95;plastics.BG | eurostat&#95;ipi&#95;rubber&#95;plastics.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;rubber&#95;plastics.CZ | eurostat&#95;ipi&#95;rubber&#95;plastics.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;rubber&#95;plastics.DE | eurostat&#95;ipi&#95;rubber&#95;plastics.DE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=DE |
| eurostat.ipi&#95;rubber&#95;plastics.DK | eurostat&#95;ipi&#95;rubber&#95;plastics.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;rubber&#95;plastics.EE | eurostat&#95;ipi&#95;rubber&#95;plastics.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;rubber&#95;plastics.EL | eurostat&#95;ipi&#95;rubber&#95;plastics.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;rubber&#95;plastics.ES | eurostat&#95;ipi&#95;rubber&#95;plastics.ES.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=ES |
| eurostat.ipi&#95;rubber&#95;plastics.EU27&#95;2020 | eurostat&#95;ipi&#95;rubber&#95;plastics.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;rubber&#95;plastics.FR | eurostat&#95;ipi&#95;rubber&#95;plastics.FR.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=FR |
| eurostat.ipi&#95;rubber&#95;plastics.HU | eurostat&#95;ipi&#95;rubber&#95;plastics.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;rubber&#95;plastics.IE | eurostat&#95;ipi&#95;rubber&#95;plastics.IE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=IE |
| eurostat.ipi&#95;rubber&#95;plastics.IT | eurostat&#95;ipi&#95;rubber&#95;plastics.IT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=IT |
| eurostat.ipi&#95;rubber&#95;plastics.LT | eurostat&#95;ipi&#95;rubber&#95;plastics.LT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=LT |
| eurostat.ipi&#95;rubber&#95;plastics.LV | eurostat&#95;ipi&#95;rubber&#95;plastics.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;rubber&#95;plastics.NL | eurostat&#95;ipi&#95;rubber&#95;plastics.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;rubber&#95;plastics.PL | eurostat&#95;ipi&#95;rubber&#95;plastics.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;rubber&#95;plastics.PT | eurostat&#95;ipi&#95;rubber&#95;plastics.PT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=PT |
| eurostat.ipi&#95;rubber&#95;plastics.RO | eurostat&#95;ipi&#95;rubber&#95;plastics.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;rubber&#95;plastics.SE | eurostat&#95;ipi&#95;rubber&#95;plastics.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;textiles.BE | eurostat&#95;ipi&#95;textiles.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;textiles.BG | eurostat&#95;ipi&#95;textiles.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;textiles.CZ | eurostat&#95;ipi&#95;textiles.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;textiles.DK | eurostat&#95;ipi&#95;textiles.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;textiles.EE | eurostat&#95;ipi&#95;textiles.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;textiles.EL | eurostat&#95;ipi&#95;textiles.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;textiles.HU | eurostat&#95;ipi&#95;textiles.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;textiles.LV | eurostat&#95;ipi&#95;textiles.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;textiles.PL | eurostat&#95;ipi&#95;textiles.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;textiles.RO | eurostat&#95;ipi&#95;textiles.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;textiles.SE | eurostat&#95;ipi&#95;textiles.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C13-C15,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;total.EU27 | eurostat&#95;ipi&#95;total.EU27.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=B-D,s&#95;adj=SCA,unit=I21,geo=EU27&#95;2020 |
| eurostat.ipi&#95;total.EU27&#95;2020 | eurostat&#95;ipi&#95;total.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=B-D,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;transport&#95;eq.AT | eurostat&#95;ipi&#95;transport&#95;eq.AT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=AT |
| eurostat.ipi&#95;transport&#95;eq.BE | eurostat&#95;ipi&#95;transport&#95;eq.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;transport&#95;eq.BG | eurostat&#95;ipi&#95;transport&#95;eq.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;transport&#95;eq.CZ | eurostat&#95;ipi&#95;transport&#95;eq.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;transport&#95;eq.DE | eurostat&#95;ipi&#95;transport&#95;eq.DE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=DE |
| eurostat.ipi&#95;transport&#95;eq.DK | eurostat&#95;ipi&#95;transport&#95;eq.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;transport&#95;eq.EE | eurostat&#95;ipi&#95;transport&#95;eq.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;transport&#95;eq.EL | eurostat&#95;ipi&#95;transport&#95;eq.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;transport&#95;eq.ES | eurostat&#95;ipi&#95;transport&#95;eq.ES.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=ES |
| eurostat.ipi&#95;transport&#95;eq.EU27&#95;2020 | eurostat&#95;ipi&#95;transport&#95;eq.EU27&#95;2020.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=EU27&#95;2020 |
| eurostat.ipi&#95;transport&#95;eq.FR | eurostat&#95;ipi&#95;transport&#95;eq.FR.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=FR |
| eurostat.ipi&#95;transport&#95;eq.HU | eurostat&#95;ipi&#95;transport&#95;eq.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;transport&#95;eq.IE | eurostat&#95;ipi&#95;transport&#95;eq.IE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=IE |
| eurostat.ipi&#95;transport&#95;eq.IT | eurostat&#95;ipi&#95;transport&#95;eq.IT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=IT |
| eurostat.ipi&#95;transport&#95;eq.LT | eurostat&#95;ipi&#95;transport&#95;eq.LT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=LT |
| eurostat.ipi&#95;transport&#95;eq.LV | eurostat&#95;ipi&#95;transport&#95;eq.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;transport&#95;eq.NL | eurostat&#95;ipi&#95;transport&#95;eq.NL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=NL |
| eurostat.ipi&#95;transport&#95;eq.PL | eurostat&#95;ipi&#95;transport&#95;eq.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;transport&#95;eq.PT | eurostat&#95;ipi&#95;transport&#95;eq.PT.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=PT |
| eurostat.ipi&#95;transport&#95;eq.RO | eurostat&#95;ipi&#95;transport&#95;eq.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;transport&#95;eq.SE | eurostat&#95;ipi&#95;transport&#95;eq.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.ipi&#95;wood&#95;paper.BE | eurostat&#95;ipi&#95;wood&#95;paper.BE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=BE |
| eurostat.ipi&#95;wood&#95;paper.BG | eurostat&#95;ipi&#95;wood&#95;paper.BG.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=BG |
| eurostat.ipi&#95;wood&#95;paper.CZ | eurostat&#95;ipi&#95;wood&#95;paper.CZ.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=CZ |
| eurostat.ipi&#95;wood&#95;paper.DK | eurostat&#95;ipi&#95;wood&#95;paper.DK.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=DK |
| eurostat.ipi&#95;wood&#95;paper.EE | eurostat&#95;ipi&#95;wood&#95;paper.EE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=EE |
| eurostat.ipi&#95;wood&#95;paper.EL | eurostat&#95;ipi&#95;wood&#95;paper.EL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=EL |
| eurostat.ipi&#95;wood&#95;paper.HU | eurostat&#95;ipi&#95;wood&#95;paper.HU.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=HU |
| eurostat.ipi&#95;wood&#95;paper.LV | eurostat&#95;ipi&#95;wood&#95;paper.LV.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=LV |
| eurostat.ipi&#95;wood&#95;paper.PL | eurostat&#95;ipi&#95;wood&#95;paper.PL.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=PL |
| eurostat.ipi&#95;wood&#95;paper.RO | eurostat&#95;ipi&#95;wood&#95;paper.RO.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=RO |
| eurostat.ipi&#95;wood&#95;paper.SE | eurostat&#95;ipi&#95;wood&#95;paper.SE.M | primary | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C16-C18,s&#95;adj=SCA,unit=I15,geo=SE |
| eurostat.labour&#95;productivity&#95;hour.AT | eurostat&#95;labour&#95;productivity&#95;hour.AT.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.BE | eurostat&#95;labour&#95;productivity&#95;hour.BE.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.BG | eurostat&#95;labour&#95;productivity&#95;hour.BG.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.CY | eurostat&#95;labour&#95;productivity&#95;hour.CY.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.CZ | eurostat&#95;labour&#95;productivity&#95;hour.CZ.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.DE | eurostat&#95;labour&#95;productivity&#95;hour.DE.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.DK | eurostat&#95;labour&#95;productivity&#95;hour.DK.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.EE | eurostat&#95;labour&#95;productivity&#95;hour.EE.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.EL | eurostat&#95;labour&#95;productivity&#95;hour.EL.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.ES | eurostat&#95;labour&#95;productivity&#95;hour.ES.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.EU27&#95;2020 | eurostat&#95;labour&#95;productivity&#95;hour.EU27&#95;2020.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.FI | eurostat&#95;labour&#95;productivity&#95;hour.FI.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.FR | eurostat&#95;labour&#95;productivity&#95;hour.FR.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.HR | eurostat&#95;labour&#95;productivity&#95;hour.HR.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.HU | eurostat&#95;labour&#95;productivity&#95;hour.HU.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.IE | eurostat&#95;labour&#95;productivity&#95;hour.IE.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.IT | eurostat&#95;labour&#95;productivity&#95;hour.IT.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.LT | eurostat&#95;labour&#95;productivity&#95;hour.LT.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.LU | eurostat&#95;labour&#95;productivity&#95;hour.LU.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.LV | eurostat&#95;labour&#95;productivity&#95;hour.LV.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.MT | eurostat&#95;labour&#95;productivity&#95;hour.MT.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.NL | eurostat&#95;labour&#95;productivity&#95;hour.NL.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.PL | eurostat&#95;labour&#95;productivity&#95;hour.PL.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.PT | eurostat&#95;labour&#95;productivity&#95;hour.PT.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.RO | eurostat&#95;labour&#95;productivity&#95;hour.RO.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.SE | eurostat&#95;labour&#95;productivity&#95;hour.SE.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.SI | eurostat&#95;labour&#95;productivity&#95;hour.SI.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour.SK | eurostat&#95;labour&#95;productivity&#95;hour.SK.A | primary | inactive | Not specified |
| eurostat.labour&#95;productivity&#95;hour&#95;real.AT | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.AT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=AT |
| eurostat.labour&#95;productivity&#95;hour&#95;real.BE | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.BE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=BE |
| eurostat.labour&#95;productivity&#95;hour&#95;real.BG | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.BG.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=BG |
| eurostat.labour&#95;productivity&#95;hour&#95;real.CY | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.CY.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=CY |
| eurostat.labour&#95;productivity&#95;hour&#95;real.CZ | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.CZ.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=CZ |
| eurostat.labour&#95;productivity&#95;hour&#95;real.DE | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.DE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=DE |
| eurostat.labour&#95;productivity&#95;hour&#95;real.DK | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.DK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=DK |
| eurostat.labour&#95;productivity&#95;hour&#95;real.EE | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.EE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=EE |
| eurostat.labour&#95;productivity&#95;hour&#95;real.EL | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.EL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=EL |
| eurostat.labour&#95;productivity&#95;hour&#95;real.ES | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.ES.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=ES |
| eurostat.labour&#95;productivity&#95;hour&#95;real.EU27&#95;2020 | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.EU27&#95;2020.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=EU27&#95;2020 |
| eurostat.labour&#95;productivity&#95;hour&#95;real.FI | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.FI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=FI |
| eurostat.labour&#95;productivity&#95;hour&#95;real.FR | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.FR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=FR |
| eurostat.labour&#95;productivity&#95;hour&#95;real.HR | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.HR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=HR |
| eurostat.labour&#95;productivity&#95;hour&#95;real.HU | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.HU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=HU |
| eurostat.labour&#95;productivity&#95;hour&#95;real.IE | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.IE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=IE |
| eurostat.labour&#95;productivity&#95;hour&#95;real.IT | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.IT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=IT |
| eurostat.labour&#95;productivity&#95;hour&#95;real.LT | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.LT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=LT |
| eurostat.labour&#95;productivity&#95;hour&#95;real.LU | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.LU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=LU |
| eurostat.labour&#95;productivity&#95;hour&#95;real.LV | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.LV.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=LV |
| eurostat.labour&#95;productivity&#95;hour&#95;real.MT | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.MT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=MT |
| eurostat.labour&#95;productivity&#95;hour&#95;real.NL | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.NL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=NL |
| eurostat.labour&#95;productivity&#95;hour&#95;real.PL | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.PL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=PL |
| eurostat.labour&#95;productivity&#95;hour&#95;real.PT | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.PT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=PT |
| eurostat.labour&#95;productivity&#95;hour&#95;real.RO | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.RO.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=RO |
| eurostat.labour&#95;productivity&#95;hour&#95;real.SE | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.SE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=SE |
| eurostat.labour&#95;productivity&#95;hour&#95;real.SI | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.SI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=SI |
| eurostat.labour&#95;productivity&#95;hour&#95;real.SK | eurostat&#95;labour&#95;productivity&#95;hour&#95;real.SK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=SK |
| eurostat.labour&#95;productivity&#95;per&#95;hour.DE | eurostat&#95;labour&#95;productivity&#95;per&#95;hour.DE.A | primary | inactive | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=DE |
| eurostat.labour&#95;productivity&#95;per&#95;hour.ES | eurostat&#95;labour&#95;productivity&#95;per&#95;hour.ES.A | primary | inactive | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=ES |
| eurostat.labour&#95;productivity&#95;per&#95;hour.EU27&#95;2020 | eurostat&#95;labour&#95;productivity&#95;per&#95;hour.EU27&#95;2020.A | primary | inactive | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=EU27&#95;2020 |
| eurostat.labour&#95;productivity&#95;per&#95;hour.FR | eurostat&#95;labour&#95;productivity&#95;per&#95;hour.FR.A | primary | inactive | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=FR |
| eurostat.labour&#95;productivity&#95;per&#95;hour.PL | eurostat&#95;labour&#95;productivity&#95;per&#95;hour.PL.A | primary | inactive | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=PL |
| eurostat.labour&#95;productivity&#95;per&#95;hour.PT | eurostat&#95;labour&#95;productivity&#95;per&#95;hour.PT.A | primary | inactive | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;HW,geo=PT |
| eurostat.labour&#95;productivity&#95;person&#95;real.AT | eurostat&#95;labour&#95;productivity&#95;person&#95;real.AT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=AT |
| eurostat.labour&#95;productivity&#95;person&#95;real.BE | eurostat&#95;labour&#95;productivity&#95;person&#95;real.BE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=BE |
| eurostat.labour&#95;productivity&#95;person&#95;real.BG | eurostat&#95;labour&#95;productivity&#95;person&#95;real.BG.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=BG |
| eurostat.labour&#95;productivity&#95;person&#95;real.CY | eurostat&#95;labour&#95;productivity&#95;person&#95;real.CY.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=CY |
| eurostat.labour&#95;productivity&#95;person&#95;real.CZ | eurostat&#95;labour&#95;productivity&#95;person&#95;real.CZ.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=CZ |
| eurostat.labour&#95;productivity&#95;person&#95;real.DE | eurostat&#95;labour&#95;productivity&#95;person&#95;real.DE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=DE |
| eurostat.labour&#95;productivity&#95;person&#95;real.DK | eurostat&#95;labour&#95;productivity&#95;person&#95;real.DK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=DK |
| eurostat.labour&#95;productivity&#95;person&#95;real.EE | eurostat&#95;labour&#95;productivity&#95;person&#95;real.EE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=EE |
| eurostat.labour&#95;productivity&#95;person&#95;real.EL | eurostat&#95;labour&#95;productivity&#95;person&#95;real.EL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=EL |
| eurostat.labour&#95;productivity&#95;person&#95;real.ES | eurostat&#95;labour&#95;productivity&#95;person&#95;real.ES.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=ES |
| eurostat.labour&#95;productivity&#95;person&#95;real.EU27&#95;2020 | eurostat&#95;labour&#95;productivity&#95;person&#95;real.EU27&#95;2020.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=EU27&#95;2020 |
| eurostat.labour&#95;productivity&#95;person&#95;real.FI | eurostat&#95;labour&#95;productivity&#95;person&#95;real.FI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=FI |
| eurostat.labour&#95;productivity&#95;person&#95;real.FR | eurostat&#95;labour&#95;productivity&#95;person&#95;real.FR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=FR |
| eurostat.labour&#95;productivity&#95;person&#95;real.HR | eurostat&#95;labour&#95;productivity&#95;person&#95;real.HR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=HR |
| eurostat.labour&#95;productivity&#95;person&#95;real.HU | eurostat&#95;labour&#95;productivity&#95;person&#95;real.HU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=HU |
| eurostat.labour&#95;productivity&#95;person&#95;real.IE | eurostat&#95;labour&#95;productivity&#95;person&#95;real.IE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=IE |
| eurostat.labour&#95;productivity&#95;person&#95;real.IT | eurostat&#95;labour&#95;productivity&#95;person&#95;real.IT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=IT |
| eurostat.labour&#95;productivity&#95;person&#95;real.LT | eurostat&#95;labour&#95;productivity&#95;person&#95;real.LT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=LT |
| eurostat.labour&#95;productivity&#95;person&#95;real.LU | eurostat&#95;labour&#95;productivity&#95;person&#95;real.LU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=LU |
| eurostat.labour&#95;productivity&#95;person&#95;real.LV | eurostat&#95;labour&#95;productivity&#95;person&#95;real.LV.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=LV |
| eurostat.labour&#95;productivity&#95;person&#95;real.MT | eurostat&#95;labour&#95;productivity&#95;person&#95;real.MT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=MT |
| eurostat.labour&#95;productivity&#95;person&#95;real.NL | eurostat&#95;labour&#95;productivity&#95;person&#95;real.NL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=NL |
| eurostat.labour&#95;productivity&#95;person&#95;real.PL | eurostat&#95;labour&#95;productivity&#95;person&#95;real.PL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=PL |
| eurostat.labour&#95;productivity&#95;person&#95;real.PT | eurostat&#95;labour&#95;productivity&#95;person&#95;real.PT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=PT |
| eurostat.labour&#95;productivity&#95;person&#95;real.RO | eurostat&#95;labour&#95;productivity&#95;person&#95;real.RO.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=RO |
| eurostat.labour&#95;productivity&#95;person&#95;real.SE | eurostat&#95;labour&#95;productivity&#95;person&#95;real.SE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=SE |
| eurostat.labour&#95;productivity&#95;person&#95;real.SI | eurostat&#95;labour&#95;productivity&#95;person&#95;real.SI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=SI |
| eurostat.labour&#95;productivity&#95;person&#95;real.SK | eurostat&#95;labour&#95;productivity&#95;person&#95;real.SK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=RLPR&#95;PER,geo=SK |
| eurostat.machinery.PT | ipi&#95;c28.PT.M | cross&#95;check | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C28,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.manufacturing.PT | ipi&#95;manufacturing.PT.M | cross&#95;check | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.metals.PT | eurostat&#95;metals.PT.M | primary | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C24&#95;C25,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.price&#95;level&#95;index.AT | eurostat&#95;price&#95;level&#95;index.AT.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.BE | eurostat&#95;price&#95;level&#95;index.BE.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.BG | eurostat&#95;price&#95;level&#95;index.BG.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.CY | eurostat&#95;price&#95;level&#95;index.CY.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.CZ | eurostat&#95;price&#95;level&#95;index.CZ.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.DE | eurostat&#95;price&#95;level&#95;index.DE.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.DK | eurostat&#95;price&#95;level&#95;index.DK.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.EE | eurostat&#95;price&#95;level&#95;index.EE.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.ES | eurostat&#95;price&#95;level&#95;index.ES.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.EU27 | eurostat&#95;price&#95;level&#95;index.EU27.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.FI | eurostat&#95;price&#95;level&#95;index.FI.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.FR | eurostat&#95;price&#95;level&#95;index.FR.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.GR | eurostat&#95;price&#95;level&#95;index.GR.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.HR | eurostat&#95;price&#95;level&#95;index.HR.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.HU | eurostat&#95;price&#95;level&#95;index.HU.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.IE | eurostat&#95;price&#95;level&#95;index.IE.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.IT | eurostat&#95;price&#95;level&#95;index.IT.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.LT | eurostat&#95;price&#95;level&#95;index.LT.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.LU | eurostat&#95;price&#95;level&#95;index.LU.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.LV | eurostat&#95;price&#95;level&#95;index.LV.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.MT | eurostat&#95;price&#95;level&#95;index.MT.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.NL | eurostat&#95;price&#95;level&#95;index.NL.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.PL | eurostat&#95;price&#95;level&#95;index.PL.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.PT | eurostat&#95;price&#95;level&#95;index.PT.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.RO | eurostat&#95;price&#95;level&#95;index.RO.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.SE | eurostat&#95;price&#95;level&#95;index.SE.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.SI | eurostat&#95;price&#95;level&#95;index.SI.A | primary | inactive | Not specified |
| eurostat.price&#95;level&#95;index.SK | eurostat&#95;price&#95;level&#95;index.SK.A | primary | inactive | Not specified |
| eurostat.rubber&#95;plastics.PT | ipi&#95;c22.PT.M | cross&#95;check | active | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C22,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.total&#95;industry.PT | ipi&#95;total.PT.M | cross&#95;check | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=B-D,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.transport&#95;eq.PT | ipi&#95;c29&#95;c30.PT.M | cross&#95;check | inactive | sts&#95;inpr&#95;m:freq=M,indic&#95;bt=PRD,nace&#95;r2=C29&#95;C30,s&#95;adj=SCA,unit=I21,geo=PT |
| eurostat.unemployment.AT | unemployment&#95;rate.AT.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=AT |
| eurostat.unemployment.BE | unemployment&#95;rate.BE.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=BE |
| eurostat.unemployment.BG | unemployment&#95;rate.BG.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=BG |
| eurostat.unemployment.CY | unemployment&#95;rate.CY.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=CY |
| eurostat.unemployment.CZ | unemployment&#95;rate.CZ.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=CZ |
| eurostat.unemployment.DE | unemployment&#95;rate.DE.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=DE |
| eurostat.unemployment.DK | unemployment&#95;rate.DK.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=DK |
| eurostat.unemployment.EE | unemployment&#95;rate.EE.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=EE |
| eurostat.unemployment.EL | unemployment&#95;rate.EL.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=EL |
| eurostat.unemployment.ES | unemployment&#95;rate.ES.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=ES |
| eurostat.unemployment.EU27 | unemployment&#95;rate.EU27.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=EU27&#95;2020 |
| eurostat.unemployment.FI | unemployment&#95;rate.FI.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=FI |
| eurostat.unemployment.FR | unemployment&#95;rate.FR.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=FR |
| eurostat.unemployment.HR | unemployment&#95;rate.HR.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=HR |
| eurostat.unemployment.HU | unemployment&#95;rate.HU.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=HU |
| eurostat.unemployment.IE | unemployment&#95;rate.IE.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=IE |
| eurostat.unemployment.IT | unemployment&#95;rate.IT.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=IT |
| eurostat.unemployment.LT | unemployment&#95;rate.LT.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=LT |
| eurostat.unemployment.LU | unemployment&#95;rate.LU.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=LU |
| eurostat.unemployment.LV | unemployment&#95;rate.LV.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=LV |
| eurostat.unemployment.MT | unemployment&#95;rate.MT.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=MT |
| eurostat.unemployment.NL | unemployment&#95;rate.NL.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=NL |
| eurostat.unemployment.PL | unemployment&#95;rate.PL.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=PL |
| eurostat.unemployment.RO | unemployment&#95;rate.RO.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=RO |
| eurostat.unemployment.SE | unemployment&#95;rate.SE.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=SE |
| eurostat.unemployment.SI | unemployment&#95;rate.SI.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=SI |
| eurostat.unemployment.SK | unemployment&#95;rate.SK.M | primary | active | une&#95;rt&#95;m:freq=M,s&#95;adj=SA,age=TOTAL,unit=PC&#95;ACT,sex=T,geo=SK |
| eurostat.unit&#95;labour&#95;cost.AT | eurostat&#95;unit&#95;labour&#95;cost.AT.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.BE | eurostat&#95;unit&#95;labour&#95;cost.BE.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.BG | eurostat&#95;unit&#95;labour&#95;cost.BG.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.CY | eurostat&#95;unit&#95;labour&#95;cost.CY.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.CZ | eurostat&#95;unit&#95;labour&#95;cost.CZ.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.DE | eurostat&#95;unit&#95;labour&#95;cost.DE.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.DK | eurostat&#95;unit&#95;labour&#95;cost.DK.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.EE | eurostat&#95;unit&#95;labour&#95;cost.EE.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.EL | eurostat&#95;unit&#95;labour&#95;cost.EL.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.ES | eurostat&#95;unit&#95;labour&#95;cost.ES.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.EU27&#95;2020 | eurostat&#95;unit&#95;labour&#95;cost.EU27&#95;2020.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.FI | eurostat&#95;unit&#95;labour&#95;cost.FI.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.FR | eurostat&#95;unit&#95;labour&#95;cost.FR.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.HR | eurostat&#95;unit&#95;labour&#95;cost.HR.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.HU | eurostat&#95;unit&#95;labour&#95;cost.HU.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.IE | eurostat&#95;unit&#95;labour&#95;cost.IE.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.IT | eurostat&#95;unit&#95;labour&#95;cost.IT.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.LT | eurostat&#95;unit&#95;labour&#95;cost.LT.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.LU | eurostat&#95;unit&#95;labour&#95;cost.LU.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.LV | eurostat&#95;unit&#95;labour&#95;cost.LV.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.MT | eurostat&#95;unit&#95;labour&#95;cost.MT.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.NL | eurostat&#95;unit&#95;labour&#95;cost.NL.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.PL | eurostat&#95;unit&#95;labour&#95;cost.PL.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.PT | eurostat&#95;unit&#95;labour&#95;cost.PT.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.RO | eurostat&#95;unit&#95;labour&#95;cost.RO.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.SE | eurostat&#95;unit&#95;labour&#95;cost.SE.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.SI | eurostat&#95;unit&#95;labour&#95;cost.SI.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost.SK | eurostat&#95;unit&#95;labour&#95;cost.SK.A | primary | inactive | Not specified |
| eurostat.unit&#95;labour&#95;cost&#95;hour.AT | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.AT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=AT |
| eurostat.unit&#95;labour&#95;cost&#95;hour.BE | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.BE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=BE |
| eurostat.unit&#95;labour&#95;cost&#95;hour.BG | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.BG.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=BG |
| eurostat.unit&#95;labour&#95;cost&#95;hour.CY | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.CY.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=CY |
| eurostat.unit&#95;labour&#95;cost&#95;hour.CZ | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.CZ.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=CZ |
| eurostat.unit&#95;labour&#95;cost&#95;hour.DE | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.DE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=DE |
| eurostat.unit&#95;labour&#95;cost&#95;hour.DK | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.DK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=DK |
| eurostat.unit&#95;labour&#95;cost&#95;hour.EE | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.EE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=EE |
| eurostat.unit&#95;labour&#95;cost&#95;hour.EL | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.EL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=EL |
| eurostat.unit&#95;labour&#95;cost&#95;hour.ES | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.ES.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=ES |
| eurostat.unit&#95;labour&#95;cost&#95;hour.EU27&#95;2020 | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.EU27&#95;2020.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=EU27&#95;2020 |
| eurostat.unit&#95;labour&#95;cost&#95;hour.FI | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.FI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=FI |
| eurostat.unit&#95;labour&#95;cost&#95;hour.FR | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.FR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=FR |
| eurostat.unit&#95;labour&#95;cost&#95;hour.HR | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.HR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=HR |
| eurostat.unit&#95;labour&#95;cost&#95;hour.HU | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.HU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=HU |
| eurostat.unit&#95;labour&#95;cost&#95;hour.IE | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.IE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=IE |
| eurostat.unit&#95;labour&#95;cost&#95;hour.IT | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.IT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=IT |
| eurostat.unit&#95;labour&#95;cost&#95;hour.LT | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.LT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=LT |
| eurostat.unit&#95;labour&#95;cost&#95;hour.LU | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.LU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=LU |
| eurostat.unit&#95;labour&#95;cost&#95;hour.LV | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.LV.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=LV |
| eurostat.unit&#95;labour&#95;cost&#95;hour.MT | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.MT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=MT |
| eurostat.unit&#95;labour&#95;cost&#95;hour.NL | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.NL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=NL |
| eurostat.unit&#95;labour&#95;cost&#95;hour.PL | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.PL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=PL |
| eurostat.unit&#95;labour&#95;cost&#95;hour.PT | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.PT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=PT |
| eurostat.unit&#95;labour&#95;cost&#95;hour.RO | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.RO.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=RO |
| eurostat.unit&#95;labour&#95;cost&#95;hour.SE | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.SE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=SE |
| eurostat.unit&#95;labour&#95;cost&#95;hour.SI | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.SI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=SI |
| eurostat.unit&#95;labour&#95;cost&#95;hour.SK | eurostat&#95;unit&#95;labour&#95;cost&#95;hour.SK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;HW,geo=SK |
| eurostat.unit&#95;labour&#95;cost&#95;person.AT | eurostat&#95;unit&#95;labour&#95;cost&#95;person.AT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=AT |
| eurostat.unit&#95;labour&#95;cost&#95;person.BE | eurostat&#95;unit&#95;labour&#95;cost&#95;person.BE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=BE |
| eurostat.unit&#95;labour&#95;cost&#95;person.BG | eurostat&#95;unit&#95;labour&#95;cost&#95;person.BG.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=BG |
| eurostat.unit&#95;labour&#95;cost&#95;person.CY | eurostat&#95;unit&#95;labour&#95;cost&#95;person.CY.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=CY |
| eurostat.unit&#95;labour&#95;cost&#95;person.CZ | eurostat&#95;unit&#95;labour&#95;cost&#95;person.CZ.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=CZ |
| eurostat.unit&#95;labour&#95;cost&#95;person.DE | eurostat&#95;unit&#95;labour&#95;cost&#95;person.DE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=DE |
| eurostat.unit&#95;labour&#95;cost&#95;person.DK | eurostat&#95;unit&#95;labour&#95;cost&#95;person.DK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=DK |
| eurostat.unit&#95;labour&#95;cost&#95;person.EE | eurostat&#95;unit&#95;labour&#95;cost&#95;person.EE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=EE |
| eurostat.unit&#95;labour&#95;cost&#95;person.EL | eurostat&#95;unit&#95;labour&#95;cost&#95;person.EL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=EL |
| eurostat.unit&#95;labour&#95;cost&#95;person.ES | eurostat&#95;unit&#95;labour&#95;cost&#95;person.ES.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=ES |
| eurostat.unit&#95;labour&#95;cost&#95;person.EU27&#95;2020 | eurostat&#95;unit&#95;labour&#95;cost&#95;person.EU27&#95;2020.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=EU27&#95;2020 |
| eurostat.unit&#95;labour&#95;cost&#95;person.FI | eurostat&#95;unit&#95;labour&#95;cost&#95;person.FI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=FI |
| eurostat.unit&#95;labour&#95;cost&#95;person.FR | eurostat&#95;unit&#95;labour&#95;cost&#95;person.FR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=FR |
| eurostat.unit&#95;labour&#95;cost&#95;person.HR | eurostat&#95;unit&#95;labour&#95;cost&#95;person.HR.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=HR |
| eurostat.unit&#95;labour&#95;cost&#95;person.HU | eurostat&#95;unit&#95;labour&#95;cost&#95;person.HU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=HU |
| eurostat.unit&#95;labour&#95;cost&#95;person.IE | eurostat&#95;unit&#95;labour&#95;cost&#95;person.IE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=IE |
| eurostat.unit&#95;labour&#95;cost&#95;person.IT | eurostat&#95;unit&#95;labour&#95;cost&#95;person.IT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=IT |
| eurostat.unit&#95;labour&#95;cost&#95;person.LT | eurostat&#95;unit&#95;labour&#95;cost&#95;person.LT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=LT |
| eurostat.unit&#95;labour&#95;cost&#95;person.LU | eurostat&#95;unit&#95;labour&#95;cost&#95;person.LU.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=LU |
| eurostat.unit&#95;labour&#95;cost&#95;person.LV | eurostat&#95;unit&#95;labour&#95;cost&#95;person.LV.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=LV |
| eurostat.unit&#95;labour&#95;cost&#95;person.MT | eurostat&#95;unit&#95;labour&#95;cost&#95;person.MT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=MT |
| eurostat.unit&#95;labour&#95;cost&#95;person.NL | eurostat&#95;unit&#95;labour&#95;cost&#95;person.NL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=NL |
| eurostat.unit&#95;labour&#95;cost&#95;person.PL | eurostat&#95;unit&#95;labour&#95;cost&#95;person.PL.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=PL |
| eurostat.unit&#95;labour&#95;cost&#95;person.PT | eurostat&#95;unit&#95;labour&#95;cost&#95;person.PT.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=PT |
| eurostat.unit&#95;labour&#95;cost&#95;person.RO | eurostat&#95;unit&#95;labour&#95;cost&#95;person.RO.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=RO |
| eurostat.unit&#95;labour&#95;cost&#95;person.SE | eurostat&#95;unit&#95;labour&#95;cost&#95;person.SE.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=SE |
| eurostat.unit&#95;labour&#95;cost&#95;person.SI | eurostat&#95;unit&#95;labour&#95;cost&#95;person.SI.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=SI |
| eurostat.unit&#95;labour&#95;cost&#95;person.SK | eurostat&#95;unit&#95;labour&#95;cost&#95;person.SK.A | primary | active | nama&#95;10&#95;lp&#95;ulc:freq=A,unit=I10,na&#95;item=NULC&#95;PER,geo=SK |

## fred

Licence: UNVERIFIED — builder must confirm before serving
Licence URL: https://fred.stlouisfed.org/docs/api/terms&#95;of&#95;use.html
Attribution: Source: IMF Primary Commodity Prices, via FRED &#40;Federal Reserve Bank of St. Louis&#41;
Licence eligibility: withheld by registry (redistribution_ok=false).
Independent verification policy: verifiable=true.
Registry entries: 20 (12 active, 8 inactive).

Independent verification channel: Collector: keyed FRED JSON API. Independent channel: public server-rendered HTML data table https://fred.stlouisfed.org/data/&lt;CODE&gt;, including identity and unit metadata. No per-observation status surface. This is the reviewed table, not fredgraph.csv or the rounded landing page. Reviewed implementation: ingest/verifiers/fred.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| fred.aluminum.WORLD | fred&#95;aluminum.WORLD.M | primary | active | PALUMUSDM |
| fred.brent&#95;oil.WORLD | fred&#95;brent&#95;oil.WORLD.M | primary | active | POILBREUSDM |
| fred.coffee.WORLD | fred&#95;coffee.WORLD.M | primary | active | PCOFFOTMUSDM |
| fred.commodity&#95;iron&#95;ore.WORLD | iron&#95;ore&#95;price.WORLD.M | primary | active | PIORECRUSDM |
| fred.commodity&#95;nickel.WORLD | nickel&#95;price.WORLD.M | primary | active | PNICKUSDM |
| fred.commodity&#95;soybean.WORLD | soybean&#95;price.WORLD.M | primary | active | PSOYBUSDM |
| fred.commodity&#95;steel.WORLD | steel&#95;price.WORLD.M | cross&#95;check | inactive | Not specified |
| fred.commodity&#95;sugar.WORLD | sugar&#95;price.WORLD.M | primary | active | PSUGAISAUSDM |
| fred.commodity&#95;zinc.WORLD | zinc&#95;price.WORLD.M | primary | active | PZINCUSDM |
| fred.copper.WORLD | fred&#95;copper.WORLD.M | primary | active | PCOPPUSDM |
| fred.corn.WORLD | fred&#95;corn.WORLD.M | primary | active | PMAIZMTUSDM |
| fred.cotton.WORLD | fred&#95;cotton.WORLD.M | primary | active | PCOTTINDUSDM |
| fred.iron&#95;ore.WORLD | iron&#95;ore&#95;price.WORLD.M | cross&#95;check | inactive | PIORECRUSDM |
| fred.natural&#95;gas.WORLD | fred&#95;natural&#95;gas.WORLD.M | primary | inactive | MHHNGSP |
| fred.nickel.WORLD | nickel&#95;price.WORLD.M | cross&#95;check | inactive | PNICKUSDM |
| fred.soybean.WORLD | soybean&#95;price.WORLD.M | cross&#95;check | inactive | PSOYBUSDM |
| fred.steel.WORLD | steel&#95;price.WORLD.M | primary | inactive | WPU101 |
| fred.sugar.WORLD | sugar&#95;price.WORLD.M | cross&#95;check | inactive | PSUGAISAUSDM |
| fred.wheat.WORLD | fred&#95;wheat.WORLD.M | primary | active | PWHEAMTUSDM |
| fred.zinc.WORLD | zinc&#95;price.WORLD.M | cross&#95;check | inactive | PZINCUSDM |

## ine

Licence: CC BY 4.0
Licence URL: https://www.ine.pt/xportal/xmain?xpid=INE&amp;xpgid=ine&#95;cont&#95;inst&amp;INST=3585857
Attribution: Fonte: Instituto Nacional de Estatística, IP – Portugal &#40;identificação da informação estatística referida, período de referência da informação&#41;
Licence eligibility: allowed by registry (redistribution_ok=true).
Independent verification policy: verifiable=true.
Registry entries: 42 (41 active, 1 inactive).

Independent verification channel: Collector: INE JSON Database API &#40;valor token&#41;. Independent channel: https://www.ine.pt/bddXplorer/htdocs/bddXplorer04.jsp?indOcorrCod=&lt;code&gt;&amp;contexto=bd&amp;lang=PT, a server-rendered HTML table with Referer: https://www.ine.pt/ and xmlDocHidden period/dimension selection. Unit and conventional signs come from the table; Decimal comparison permits trailing-zero rendering differences. Reviewed implementation: ingest/verifiers/ine.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| ine.conf&#95;manufacturing.PT | ine&#95;conf&#95;manufacturing.PT.M | primary | active | 0001188:Dim2=PT |
| ine.deaths.PT | ine&#95;deaths.PT.A | primary | active | 0005605:Dim2=PT,Dim3=T,Dim4=T |
| ine.exports&#95;monthly.PT | ine&#95;exports&#95;monthly.PT.M | primary | active | 0001400:Dim2=MUNDO,Dim3=T |
| ine.hicp&#95;yoy.PT | hicp&#95;yoy.PT.M | primary | active | 0014655:Dim2=PT,Dim3=T |
| ine.imports&#95;monthly.PT | ine&#95;imports&#95;monthly.PT.M | primary | active | 0001397:Dim2=MUNDO,Dim3=T |
| ine.ipc&#95;yoy.Continente | ine&#95;ipc&#95;yoy.Continente.M | primary | active | 0014647:Dim2=1,Dim3=T |
| ine.ipc&#95;yoy.PT | ine&#95;ipc&#95;yoy.PT.M | primary | active | 0014647:Dim2=PT,Dim3=T |
| ine.ipi&#95;seasonal&#95;cae.PT | ine&#95;ipi&#95;seasonal&#95;cae.PT.M | primary | inactive | Not specified |
| ine.ipi&#95;seasonal&#95;cae&#95;08.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;08.PT.M | primary | active | 0011889:Dim2=PT,Dim3=08 |
| ine.ipi&#95;seasonal&#95;cae&#95;10.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;10.PT.M | primary | active | 0011889:Dim2=PT,Dim3=10 |
| ine.ipi&#95;seasonal&#95;cae&#95;11.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;11.PT.M | primary | active | 0011889:Dim2=PT,Dim3=11 |
| ine.ipi&#95;seasonal&#95;cae&#95;13.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;13.PT.M | primary | active | 0011889:Dim2=PT,Dim3=13 |
| ine.ipi&#95;seasonal&#95;cae&#95;14.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;14.PT.M | primary | active | 0011889:Dim2=PT,Dim3=14 |
| ine.ipi&#95;seasonal&#95;cae&#95;15.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;15.PT.M | primary | active | 0011889:Dim2=PT,Dim3=15 |
| ine.ipi&#95;seasonal&#95;cae&#95;16.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;16.PT.M | primary | active | 0011889:Dim2=PT,Dim3=16 |
| ine.ipi&#95;seasonal&#95;cae&#95;17.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;17.PT.M | primary | active | 0011889:Dim2=PT,Dim3=17 |
| ine.ipi&#95;seasonal&#95;cae&#95;18.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;18.PT.M | primary | active | 0011889:Dim2=PT,Dim3=18 |
| ine.ipi&#95;seasonal&#95;cae&#95;20.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;20.PT.M | primary | active | 0011889:Dim2=PT,Dim3=20 |
| ine.ipi&#95;seasonal&#95;cae&#95;21.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;21.PT.M | primary | active | 0011889:Dim2=PT,Dim3=21 |
| ine.ipi&#95;seasonal&#95;cae&#95;22.PT | ipi&#95;c22.PT.M | primary | active | 0011889:Dim2=PT,Dim3=22 |
| ine.ipi&#95;seasonal&#95;cae&#95;23.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;23.PT.M | primary | active | 0011889:Dim2=PT,Dim3=23 |
| ine.ipi&#95;seasonal&#95;cae&#95;24.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;24.PT.M | primary | active | 0011889:Dim2=PT,Dim3=24 |
| ine.ipi&#95;seasonal&#95;cae&#95;25.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;25.PT.M | primary | active | 0011889:Dim2=PT,Dim3=25 |
| ine.ipi&#95;seasonal&#95;cae&#95;26.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;26.PT.M | primary | active | 0011889:Dim2=PT,Dim3=26 |
| ine.ipi&#95;seasonal&#95;cae&#95;27.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;27.PT.M | primary | active | 0011889:Dim2=PT,Dim3=27 |
| ine.ipi&#95;seasonal&#95;cae&#95;28.PT | ipi&#95;c28.PT.M | primary | active | 0011889:Dim2=PT,Dim3=28 |
| ine.ipi&#95;seasonal&#95;cae&#95;29.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;29.PT.M | primary | active | 0011889:Dim2=PT,Dim3=29 |
| ine.ipi&#95;seasonal&#95;cae&#95;30.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;30.PT.M | primary | active | 0011889:Dim2=PT,Dim3=30 |
| ine.ipi&#95;seasonal&#95;cae&#95;31.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;31.PT.M | primary | active | 0011889:Dim2=PT,Dim3=31 |
| ine.ipi&#95;seasonal&#95;cae&#95;32.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;32.PT.M | primary | active | 0011889:Dim2=PT,Dim3=32 |
| ine.ipi&#95;seasonal&#95;cae&#95;33.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;33.PT.M | primary | active | 0011889:Dim2=PT,Dim3=33 |
| ine.ipi&#95;seasonal&#95;cae&#95;35.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;35.PT.M | primary | active | 0011889:Dim2=PT,Dim3=35 |
| ine.ipi&#95;seasonal&#95;cae&#95;38.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;38.PT.M | primary | active | 0011889:Dim2=PT,Dim3=38 |
| ine.ipi&#95;seasonal&#95;cae&#95;B.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;B.PT.M | primary | active | 0011889:Dim2=PT,Dim3=B |
| ine.ipi&#95;seasonal&#95;cae&#95;C.PT | ipi&#95;manufacturing.PT.M | primary | active | 0011889:Dim2=PT,Dim3=C |
| ine.ipi&#95;seasonal&#95;cae&#95;D.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;D.PT.M | primary | active | 0011889:Dim2=PT,Dim3=D |
| ine.ipi&#95;seasonal&#95;cae&#95;E.PT | ine&#95;ipi&#95;seasonal&#95;cae&#95;E.PT.M | primary | active | 0011889:Dim2=PT,Dim3=E |
| ine.ipi&#95;seasonal&#95;cae&#95;TOT.PT | ipi&#95;total.PT.M | primary | active | 0011889:Dim2=PT,Dim3=TOT |
| ine.ipi&#95;yoy&#95;cae.PT | ine&#95;ipi&#95;yoy&#95;cae.PT.M | primary | active | 0011897:Dim2=PT,Dim3=C |
| ine.live&#95;births.PT | ine&#95;live&#95;births.PT.A | primary | active | 0001346:Dim2=PT,Dim3=T |
| ine.population.PT | ine&#95;population.PT.A | primary | active | 0006031:Dim2=PT,Dim3=T,Dim4=T,Dim5=T |
| ine.unemployment&#95;monthly.PT | unemployment&#95;rate.PT.M | primary | active | 0007983:Dim2=PT,Dim3=T |

## oecd

Licence: OECD T&amp;C §3 bespoke data grant &#40;reuse for any purpose incl. commercial, with attribution and sub-licence acknowledgment propagation&#41; - UNVERIFIED pending per-dataset third-party rights clearance
Licence URL: https://www.oecd.org/en/about/terms-conditions.html
Attribution: Source: OECD &#40;year&#41;, &#40;dataset name&#41;, sdmx.oecd.org &#40;accessed on YYYY-MM-DD&#41;
Licence eligibility: withheld by registry (redistribution_ok=false).
Independent verification policy: verifiable=true.
Registry entries: 6 (6 active, 0 inactive).

Independent verification channel: Collector: SDMX-JSON data 2.0. Independent channel: https://sdmx.oecd.org/public/rest/data/&lt;agency&gt;,&lt;dataflow&gt;/&lt;key&gt;?format=csvfilewithlabels&amp;dimensionAtObservation=AllDimensions, labelled SDMX CSV on the same data API path with an independent parser. Dimensions, units, multiplier and status are checked from CSV fields. Reviewed implementation: ingest/verifiers/oecd.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| oecd.cli.PT | oecd&#95;cli.PT.M | primary | active | OECD.SDD.STES,DSD&#95;STES@DF&#95;CLI/PRT.M.BCICP.IX.&#95;Z.AA.IX.&#95;Z.H |
| oecd.employment.PT | oecd&#95;employment.PT.M | primary | active | OECD.SDD.STES,DSD&#95;STES@DF&#95;BTS/PRT.M.EM.PB.C.Y.&#95;Z.FT.N |
| oecd.order&#95;books.PT | oecd&#95;order&#95;books.PT.M | primary | active | OECD.SDD.STES,DSD&#95;STES@DF&#95;BTS/PRT.M.OB.PB.C.Y.&#95;Z.C.N |
| oecd.production.PT | oecd&#95;production.PT.M | primary | active | OECD.SDD.STES,DSD&#95;STES@DF&#95;BTS/PRT.M.PR.PB.C.Y.&#95;Z.T.N |
| oecd.selling&#95;prices.PT | oecd&#95;selling&#95;prices.PT.M | primary | active | OECD.SDD.STES,DSD&#95;STES@DF&#95;BTS/PRT.M.SP.PB.C.Y.&#95;Z.FT.N |
| oecd.unemp&#95;m.PT | unemployment&#95;rate.PT.M | cross&#95;check | active | OECD.SDD.TPS,DSD&#95;LFS@DF&#95;IALFS&#95;UNE&#95;M/PRT.UNE&#95;LF&#95;M.PT&#95;LF&#95;SUB.&#95;Z.Y.&#95;T.Y&#95;GE15.&#95;Z.M |

## ren

Licence: REN DataHub Termos Legais — no open reuse grant &#40;clauses 2/3.2 reserve reproduction, distribution and substantial extraction to express REN consent&#41;
Licence URL: https://datahub.ren.pt/pt/termos-legais-e-condicoes-gerais/
Attribution: Source: REN — Redes Energéticas Nacionais
Licence eligibility: withheld by registry (redistribution_ok=false).
Independent verification policy: verifiable=true.
Registry entries: 14 (14 active, 0 inactive).

Independent verification channel: Collector: servicebus JSON API. Independent channel: https://datahub.ren.pt/service/exports/csv chart CSV export, modelId=1550 &#40;balance&#41; or modelId=2649 &#40;market&#41;, scoped to a month. Balance CSV exposes GWh; market CSV has no unit annotation; neither exposes observation status. Reviewed implementation: ingest/verifiers/ren.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| ren.electricity&#95;biomass.PT | ren&#95;electricity&#95;biomass.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:BIOMASSA |
| ren.electricity&#95;consumption.PT | ren&#95;electricity&#95;consumption.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:CONSUMO |
| ren.electricity&#95;exports.PT | ren&#95;electricity&#95;exports.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:EXPORTACAO |
| ren.electricity&#95;hydro.PT | ren&#95;electricity&#95;hydro.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:HIDRICA |
| ren.electricity&#95;imports.PT | ren&#95;electricity&#95;imports.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:IMPORTACAO |
| ren.electricity&#95;natural&#95;gas.PT | ren&#95;electricity&#95;natural&#95;gas.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:GAS&#95;NATURAL |
| ren.electricity&#95;natural&#95;gas&#95;ccgt.PT | ren&#95;electricity&#95;natural&#95;gas&#95;ccgt.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:GAS&#95;NATURAL&#95;CICLO&#95;COMBINADO |
| ren.electricity&#95;net&#95;imports.PT | ren&#95;electricity&#95;net&#95;imports.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:SALDO&#95;IMPORTADOR |
| ren.electricity&#95;price&#95;mibel.PT | ren&#95;electricity&#95;price&#95;mibel.PT.M | primary | active | ElectricityMarketPricesMonthly:PT.Preço Médio |
| ren.electricity&#95;production&#95;non&#95;renewable.PT | ren&#95;electricity&#95;production&#95;non&#95;renewable.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:PRODUCAO&#95;NAO&#95;RENOVAVEL |
| ren.electricity&#95;production&#95;renewable.PT | ren&#95;electricity&#95;production&#95;renewable.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:PRODUCAO&#95;RENOVAVEL |
| ren.electricity&#95;production&#95;total.PT | ren&#95;electricity&#95;production&#95;total.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:PRODUCAO&#95;TOTAL |
| ren.electricity&#95;solar.PT | ren&#95;electricity&#95;solar.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:SOLAR |
| ren.electricity&#95;wind.PT | ren&#95;electricity&#95;wind.PT.M | primary | active | ElectricityConsumptionSupplyMonthly:EOLICA |

## worldbank

Licence: CC BY 4.0
Licence URL: https://datacatalog.worldbank.org/public-licenses
Attribution: Source: World Bank
Licence eligibility: allowed by registry (redistribution_ok=true).
Independent verification policy: verifiable=true.
Registry entries: 982 (930 active, 52 inactive).

Independent verification channel: Collector: API v2 JSON. Independent channel: publisher bulk CSV ZIP at https://api.worldbank.org/v2/&lt;locale&gt;/indicator/&lt;CODE&gt;?downloadformat=csv, including indicator and country metadata members. Reviewed locales: es for NY.GDP.MKTP.KD.ZG and SL.UEM.TOTL.ZS, en otherwise, with no automatic fallback. No per-cell unit/status surface. Reviewed implementation: ingest/verifiers/worldbank.py.

Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:

| Series ID | Indicator key | Role | State | Native code |
|---|---|---|---|---|
| worldbank.birth&#95;rate.AO | worldbank&#95;birth&#95;rate.AO.A | primary | active | SP.DYN.CBRT.IN:AGO |
| worldbank.birth&#95;rate.AR | worldbank&#95;birth&#95;rate.AR.A | primary | active | SP.DYN.CBRT.IN:ARG |
| worldbank.birth&#95;rate.AT | worldbank&#95;birth&#95;rate.AT.A | primary | active | SP.DYN.CBRT.IN:AUT |
| worldbank.birth&#95;rate.BE | worldbank&#95;birth&#95;rate.BE.A | primary | active | SP.DYN.CBRT.IN:BEL |
| worldbank.birth&#95;rate.BG | worldbank&#95;birth&#95;rate.BG.A | primary | active | SP.DYN.CBRT.IN:BGR |
| worldbank.birth&#95;rate.BR | worldbank&#95;birth&#95;rate.BR.A | primary | active | SP.DYN.CBRT.IN:BRA |
| worldbank.birth&#95;rate.CA | worldbank&#95;birth&#95;rate.CA.A | primary | active | SP.DYN.CBRT.IN:CAN |
| worldbank.birth&#95;rate.CH | worldbank&#95;birth&#95;rate.CH.A | primary | active | SP.DYN.CBRT.IN:CHE |
| worldbank.birth&#95;rate.CL | worldbank&#95;birth&#95;rate.CL.A | primary | active | SP.DYN.CBRT.IN:CHL |
| worldbank.birth&#95;rate.CN | worldbank&#95;birth&#95;rate.CN.A | primary | active | SP.DYN.CBRT.IN:CHN |
| worldbank.birth&#95;rate.CV | worldbank&#95;birth&#95;rate.CV.A | primary | active | SP.DYN.CBRT.IN:CPV |
| worldbank.birth&#95;rate.CY | worldbank&#95;birth&#95;rate.CY.A | primary | active | SP.DYN.CBRT.IN:CYP |
| worldbank.birth&#95;rate.CZ | worldbank&#95;birth&#95;rate.CZ.A | primary | active | SP.DYN.CBRT.IN:CZE |
| worldbank.birth&#95;rate.DE | worldbank&#95;birth&#95;rate.DE.A | primary | active | SP.DYN.CBRT.IN:DEU |
| worldbank.birth&#95;rate.DK | worldbank&#95;birth&#95;rate.DK.A | primary | active | SP.DYN.CBRT.IN:DNK |
| worldbank.birth&#95;rate.EE | worldbank&#95;birth&#95;rate.EE.A | primary | active | SP.DYN.CBRT.IN:EST |
| worldbank.birth&#95;rate.EG | worldbank&#95;birth&#95;rate.EG.A | primary | active | SP.DYN.CBRT.IN:EGY |
| worldbank.birth&#95;rate.ES | worldbank&#95;birth&#95;rate.ES.A | primary | active | SP.DYN.CBRT.IN:ESP |
| worldbank.birth&#95;rate.EU | worldbank&#95;birth&#95;rate.EU.A | primary | active | SP.DYN.CBRT.IN:EUU |
| worldbank.birth&#95;rate.FI | worldbank&#95;birth&#95;rate.FI.A | primary | active | SP.DYN.CBRT.IN:FIN |
| worldbank.birth&#95;rate.FR | worldbank&#95;birth&#95;rate.FR.A | primary | active | SP.DYN.CBRT.IN:FRA |
| worldbank.birth&#95;rate.GB | worldbank&#95;birth&#95;rate.GB.A | primary | active | SP.DYN.CBRT.IN:GBR |
| worldbank.birth&#95;rate.GR | worldbank&#95;birth&#95;rate.GR.A | primary | active | SP.DYN.CBRT.IN:GRC |
| worldbank.birth&#95;rate.GW | worldbank&#95;birth&#95;rate.GW.A | primary | active | SP.DYN.CBRT.IN:GNB |
| worldbank.birth&#95;rate.HR | worldbank&#95;birth&#95;rate.HR.A | primary | active | SP.DYN.CBRT.IN:HRV |
| worldbank.birth&#95;rate.HU | worldbank&#95;birth&#95;rate.HU.A | primary | active | SP.DYN.CBRT.IN:HUN |
| worldbank.birth&#95;rate.ID | worldbank&#95;birth&#95;rate.ID.A | primary | active | SP.DYN.CBRT.IN:IDN |
| worldbank.birth&#95;rate.IE | worldbank&#95;birth&#95;rate.IE.A | primary | active | SP.DYN.CBRT.IN:IRL |
| worldbank.birth&#95;rate.IN | worldbank&#95;birth&#95;rate.IN.A | primary | active | SP.DYN.CBRT.IN:IND |
| worldbank.birth&#95;rate.IT | worldbank&#95;birth&#95;rate.IT.A | primary | active | SP.DYN.CBRT.IN:ITA |
| worldbank.birth&#95;rate.JP | worldbank&#95;birth&#95;rate.JP.A | primary | active | SP.DYN.CBRT.IN:JPN |
| worldbank.birth&#95;rate.KR | worldbank&#95;birth&#95;rate.KR.A | primary | active | SP.DYN.CBRT.IN:KOR |
| worldbank.birth&#95;rate.LT | worldbank&#95;birth&#95;rate.LT.A | primary | active | SP.DYN.CBRT.IN:LTU |
| worldbank.birth&#95;rate.LU | worldbank&#95;birth&#95;rate.LU.A | primary | active | SP.DYN.CBRT.IN:LUX |
| worldbank.birth&#95;rate.LV | worldbank&#95;birth&#95;rate.LV.A | primary | active | SP.DYN.CBRT.IN:LVA |
| worldbank.birth&#95;rate.MT | worldbank&#95;birth&#95;rate.MT.A | primary | active | SP.DYN.CBRT.IN:MLT |
| worldbank.birth&#95;rate.MX | worldbank&#95;birth&#95;rate.MX.A | primary | active | SP.DYN.CBRT.IN:MEX |
| worldbank.birth&#95;rate.MY | worldbank&#95;birth&#95;rate.MY.A | primary | active | SP.DYN.CBRT.IN:MYS |
| worldbank.birth&#95;rate.MZ | worldbank&#95;birth&#95;rate.MZ.A | primary | active | SP.DYN.CBRT.IN:MOZ |
| worldbank.birth&#95;rate.NG | worldbank&#95;birth&#95;rate.NG.A | primary | active | SP.DYN.CBRT.IN:NGA |
| worldbank.birth&#95;rate.NL | worldbank&#95;birth&#95;rate.NL.A | primary | active | SP.DYN.CBRT.IN:NLD |
| worldbank.birth&#95;rate.NO | worldbank&#95;birth&#95;rate.NO.A | primary | active | SP.DYN.CBRT.IN:NOR |
| worldbank.birth&#95;rate.PL | worldbank&#95;birth&#95;rate.PL.A | primary | active | SP.DYN.CBRT.IN:POL |
| worldbank.birth&#95;rate.PT | worldbank&#95;birth&#95;rate.PT.A | primary | active | SP.DYN.CBRT.IN:PRT |
| worldbank.birth&#95;rate.RO | worldbank&#95;birth&#95;rate.RO.A | primary | active | SP.DYN.CBRT.IN:ROU |
| worldbank.birth&#95;rate.SE | worldbank&#95;birth&#95;rate.SE.A | primary | active | SP.DYN.CBRT.IN:SWE |
| worldbank.birth&#95;rate.SI | worldbank&#95;birth&#95;rate.SI.A | primary | active | SP.DYN.CBRT.IN:SVN |
| worldbank.birth&#95;rate.SK | worldbank&#95;birth&#95;rate.SK.A | primary | active | SP.DYN.CBRT.IN:SVK |
| worldbank.birth&#95;rate.ST | worldbank&#95;birth&#95;rate.ST.A | primary | active | SP.DYN.CBRT.IN:STP |
| worldbank.birth&#95;rate.TH | worldbank&#95;birth&#95;rate.TH.A | primary | active | SP.DYN.CBRT.IN:THA |
| worldbank.birth&#95;rate.TL | worldbank&#95;birth&#95;rate.TL.A | primary | active | SP.DYN.CBRT.IN:TLS |
| worldbank.birth&#95;rate.TR | worldbank&#95;birth&#95;rate.TR.A | primary | active | SP.DYN.CBRT.IN:TUR |
| worldbank.birth&#95;rate.US | worldbank&#95;birth&#95;rate.US.A | primary | active | SP.DYN.CBRT.IN:USA |
| worldbank.birth&#95;rate.ZA | worldbank&#95;birth&#95;rate.ZA.A | primary | active | SP.DYN.CBRT.IN:ZAF |
| worldbank.death&#95;rate.AO | worldbank&#95;death&#95;rate.AO.A | primary | active | SP.DYN.CDRT.IN:AGO |
| worldbank.death&#95;rate.AR | worldbank&#95;death&#95;rate.AR.A | primary | active | SP.DYN.CDRT.IN:ARG |
| worldbank.death&#95;rate.AT | worldbank&#95;death&#95;rate.AT.A | primary | active | SP.DYN.CDRT.IN:AUT |
| worldbank.death&#95;rate.BE | worldbank&#95;death&#95;rate.BE.A | primary | active | SP.DYN.CDRT.IN:BEL |
| worldbank.death&#95;rate.BG | worldbank&#95;death&#95;rate.BG.A | primary | active | SP.DYN.CDRT.IN:BGR |
| worldbank.death&#95;rate.BR | worldbank&#95;death&#95;rate.BR.A | primary | active | SP.DYN.CDRT.IN:BRA |
| worldbank.death&#95;rate.CA | worldbank&#95;death&#95;rate.CA.A | primary | active | SP.DYN.CDRT.IN:CAN |
| worldbank.death&#95;rate.CH | worldbank&#95;death&#95;rate.CH.A | primary | active | SP.DYN.CDRT.IN:CHE |
| worldbank.death&#95;rate.CL | worldbank&#95;death&#95;rate.CL.A | primary | active | SP.DYN.CDRT.IN:CHL |
| worldbank.death&#95;rate.CN | worldbank&#95;death&#95;rate.CN.A | primary | active | SP.DYN.CDRT.IN:CHN |
| worldbank.death&#95;rate.CV | worldbank&#95;death&#95;rate.CV.A | primary | active | SP.DYN.CDRT.IN:CPV |
| worldbank.death&#95;rate.CY | worldbank&#95;death&#95;rate.CY.A | primary | active | SP.DYN.CDRT.IN:CYP |
| worldbank.death&#95;rate.CZ | worldbank&#95;death&#95;rate.CZ.A | primary | active | SP.DYN.CDRT.IN:CZE |
| worldbank.death&#95;rate.DE | worldbank&#95;death&#95;rate.DE.A | primary | active | SP.DYN.CDRT.IN:DEU |
| worldbank.death&#95;rate.DK | worldbank&#95;death&#95;rate.DK.A | primary | active | SP.DYN.CDRT.IN:DNK |
| worldbank.death&#95;rate.EE | worldbank&#95;death&#95;rate.EE.A | primary | active | SP.DYN.CDRT.IN:EST |
| worldbank.death&#95;rate.EG | worldbank&#95;death&#95;rate.EG.A | primary | active | SP.DYN.CDRT.IN:EGY |
| worldbank.death&#95;rate.ES | worldbank&#95;death&#95;rate.ES.A | primary | active | SP.DYN.CDRT.IN:ESP |
| worldbank.death&#95;rate.EU | worldbank&#95;death&#95;rate.EU.A | primary | active | SP.DYN.CDRT.IN:EUU |
| worldbank.death&#95;rate.FI | worldbank&#95;death&#95;rate.FI.A | primary | active | SP.DYN.CDRT.IN:FIN |
| worldbank.death&#95;rate.FR | worldbank&#95;death&#95;rate.FR.A | primary | active | SP.DYN.CDRT.IN:FRA |
| worldbank.death&#95;rate.GB | worldbank&#95;death&#95;rate.GB.A | primary | active | SP.DYN.CDRT.IN:GBR |
| worldbank.death&#95;rate.GR | worldbank&#95;death&#95;rate.GR.A | primary | active | SP.DYN.CDRT.IN:GRC |
| worldbank.death&#95;rate.GW | worldbank&#95;death&#95;rate.GW.A | primary | active | SP.DYN.CDRT.IN:GNB |
| worldbank.death&#95;rate.HR | worldbank&#95;death&#95;rate.HR.A | primary | active | SP.DYN.CDRT.IN:HRV |
| worldbank.death&#95;rate.HU | worldbank&#95;death&#95;rate.HU.A | primary | active | SP.DYN.CDRT.IN:HUN |
| worldbank.death&#95;rate.ID | worldbank&#95;death&#95;rate.ID.A | primary | active | SP.DYN.CDRT.IN:IDN |
| worldbank.death&#95;rate.IE | worldbank&#95;death&#95;rate.IE.A | primary | active | SP.DYN.CDRT.IN:IRL |
| worldbank.death&#95;rate.IN | worldbank&#95;death&#95;rate.IN.A | primary | active | SP.DYN.CDRT.IN:IND |
| worldbank.death&#95;rate.IT | worldbank&#95;death&#95;rate.IT.A | primary | active | SP.DYN.CDRT.IN:ITA |
| worldbank.death&#95;rate.JP | worldbank&#95;death&#95;rate.JP.A | primary | active | SP.DYN.CDRT.IN:JPN |
| worldbank.death&#95;rate.KR | worldbank&#95;death&#95;rate.KR.A | primary | active | SP.DYN.CDRT.IN:KOR |
| worldbank.death&#95;rate.LT | worldbank&#95;death&#95;rate.LT.A | primary | active | SP.DYN.CDRT.IN:LTU |
| worldbank.death&#95;rate.LU | worldbank&#95;death&#95;rate.LU.A | primary | active | SP.DYN.CDRT.IN:LUX |
| worldbank.death&#95;rate.LV | worldbank&#95;death&#95;rate.LV.A | primary | active | SP.DYN.CDRT.IN:LVA |
| worldbank.death&#95;rate.MT | worldbank&#95;death&#95;rate.MT.A | primary | active | SP.DYN.CDRT.IN:MLT |
| worldbank.death&#95;rate.MX | worldbank&#95;death&#95;rate.MX.A | primary | active | SP.DYN.CDRT.IN:MEX |
| worldbank.death&#95;rate.MY | worldbank&#95;death&#95;rate.MY.A | primary | active | SP.DYN.CDRT.IN:MYS |
| worldbank.death&#95;rate.MZ | worldbank&#95;death&#95;rate.MZ.A | primary | active | SP.DYN.CDRT.IN:MOZ |
| worldbank.death&#95;rate.NG | worldbank&#95;death&#95;rate.NG.A | primary | active | SP.DYN.CDRT.IN:NGA |
| worldbank.death&#95;rate.NL | worldbank&#95;death&#95;rate.NL.A | primary | active | SP.DYN.CDRT.IN:NLD |
| worldbank.death&#95;rate.NO | worldbank&#95;death&#95;rate.NO.A | primary | active | SP.DYN.CDRT.IN:NOR |
| worldbank.death&#95;rate.PL | worldbank&#95;death&#95;rate.PL.A | primary | active | SP.DYN.CDRT.IN:POL |
| worldbank.death&#95;rate.PT | worldbank&#95;death&#95;rate.PT.A | primary | active | SP.DYN.CDRT.IN:PRT |
| worldbank.death&#95;rate.RO | worldbank&#95;death&#95;rate.RO.A | primary | active | SP.DYN.CDRT.IN:ROU |
| worldbank.death&#95;rate.SE | worldbank&#95;death&#95;rate.SE.A | primary | active | SP.DYN.CDRT.IN:SWE |
| worldbank.death&#95;rate.SI | worldbank&#95;death&#95;rate.SI.A | primary | active | SP.DYN.CDRT.IN:SVN |
| worldbank.death&#95;rate.SK | worldbank&#95;death&#95;rate.SK.A | primary | active | SP.DYN.CDRT.IN:SVK |
| worldbank.death&#95;rate.ST | worldbank&#95;death&#95;rate.ST.A | primary | active | SP.DYN.CDRT.IN:STP |
| worldbank.death&#95;rate.TH | worldbank&#95;death&#95;rate.TH.A | primary | active | SP.DYN.CDRT.IN:THA |
| worldbank.death&#95;rate.TL | worldbank&#95;death&#95;rate.TL.A | primary | active | SP.DYN.CDRT.IN:TLS |
| worldbank.death&#95;rate.TR | worldbank&#95;death&#95;rate.TR.A | primary | active | SP.DYN.CDRT.IN:TUR |
| worldbank.death&#95;rate.US | worldbank&#95;death&#95;rate.US.A | primary | active | SP.DYN.CDRT.IN:USA |
| worldbank.death&#95;rate.ZA | worldbank&#95;death&#95;rate.ZA.A | primary | active | SP.DYN.CDRT.IN:ZAF |
| worldbank.employment&#95;rate.AO | worldbank&#95;employment&#95;rate.AO.A | primary | active | SL.EMP.TOTL.SP.ZS:AGO |
| worldbank.employment&#95;rate.AR | worldbank&#95;employment&#95;rate.AR.A | primary | active | SL.EMP.TOTL.SP.ZS:ARG |
| worldbank.employment&#95;rate.AT | worldbank&#95;employment&#95;rate.AT.A | primary | active | SL.EMP.TOTL.SP.ZS:AUT |
| worldbank.employment&#95;rate.BE | worldbank&#95;employment&#95;rate.BE.A | primary | active | SL.EMP.TOTL.SP.ZS:BEL |
| worldbank.employment&#95;rate.BG | worldbank&#95;employment&#95;rate.BG.A | primary | active | SL.EMP.TOTL.SP.ZS:BGR |
| worldbank.employment&#95;rate.BR | worldbank&#95;employment&#95;rate.BR.A | primary | active | SL.EMP.TOTL.SP.ZS:BRA |
| worldbank.employment&#95;rate.CA | worldbank&#95;employment&#95;rate.CA.A | primary | active | SL.EMP.TOTL.SP.ZS:CAN |
| worldbank.employment&#95;rate.CH | worldbank&#95;employment&#95;rate.CH.A | primary | active | SL.EMP.TOTL.SP.ZS:CHE |
| worldbank.employment&#95;rate.CL | worldbank&#95;employment&#95;rate.CL.A | primary | active | SL.EMP.TOTL.SP.ZS:CHL |
| worldbank.employment&#95;rate.CN | worldbank&#95;employment&#95;rate.CN.A | primary | active | SL.EMP.TOTL.SP.ZS:CHN |
| worldbank.employment&#95;rate.CV | worldbank&#95;employment&#95;rate.CV.A | primary | active | SL.EMP.TOTL.SP.ZS:CPV |
| worldbank.employment&#95;rate.CY | worldbank&#95;employment&#95;rate.CY.A | primary | active | SL.EMP.TOTL.SP.ZS:CYP |
| worldbank.employment&#95;rate.CZ | worldbank&#95;employment&#95;rate.CZ.A | primary | active | SL.EMP.TOTL.SP.ZS:CZE |
| worldbank.employment&#95;rate.DE | worldbank&#95;employment&#95;rate.DE.A | primary | active | SL.EMP.TOTL.SP.ZS:DEU |
| worldbank.employment&#95;rate.DK | worldbank&#95;employment&#95;rate.DK.A | primary | active | SL.EMP.TOTL.SP.ZS:DNK |
| worldbank.employment&#95;rate.EE | worldbank&#95;employment&#95;rate.EE.A | primary | active | SL.EMP.TOTL.SP.ZS:EST |
| worldbank.employment&#95;rate.EG | worldbank&#95;employment&#95;rate.EG.A | primary | active | SL.EMP.TOTL.SP.ZS:EGY |
| worldbank.employment&#95;rate.ES | worldbank&#95;employment&#95;rate.ES.A | primary | active | SL.EMP.TOTL.SP.ZS:ESP |
| worldbank.employment&#95;rate.EU | worldbank&#95;employment&#95;rate.EU.A | primary | active | SL.EMP.TOTL.SP.ZS:EUU |
| worldbank.employment&#95;rate.FI | worldbank&#95;employment&#95;rate.FI.A | primary | active | SL.EMP.TOTL.SP.ZS:FIN |
| worldbank.employment&#95;rate.FR | worldbank&#95;employment&#95;rate.FR.A | primary | active | SL.EMP.TOTL.SP.ZS:FRA |
| worldbank.employment&#95;rate.GB | worldbank&#95;employment&#95;rate.GB.A | primary | active | SL.EMP.TOTL.SP.ZS:GBR |
| worldbank.employment&#95;rate.GR | worldbank&#95;employment&#95;rate.GR.A | primary | active | SL.EMP.TOTL.SP.ZS:GRC |
| worldbank.employment&#95;rate.GW | worldbank&#95;employment&#95;rate.GW.A | primary | active | SL.EMP.TOTL.SP.ZS:GNB |
| worldbank.employment&#95;rate.HR | worldbank&#95;employment&#95;rate.HR.A | primary | active | SL.EMP.TOTL.SP.ZS:HRV |
| worldbank.employment&#95;rate.HU | worldbank&#95;employment&#95;rate.HU.A | primary | active | SL.EMP.TOTL.SP.ZS:HUN |
| worldbank.employment&#95;rate.ID | worldbank&#95;employment&#95;rate.ID.A | primary | active | SL.EMP.TOTL.SP.ZS:IDN |
| worldbank.employment&#95;rate.IE | worldbank&#95;employment&#95;rate.IE.A | primary | active | SL.EMP.TOTL.SP.ZS:IRL |
| worldbank.employment&#95;rate.IN | worldbank&#95;employment&#95;rate.IN.A | primary | active | SL.EMP.TOTL.SP.ZS:IND |
| worldbank.employment&#95;rate.IT | worldbank&#95;employment&#95;rate.IT.A | primary | active | SL.EMP.TOTL.SP.ZS:ITA |
| worldbank.employment&#95;rate.JP | worldbank&#95;employment&#95;rate.JP.A | primary | active | SL.EMP.TOTL.SP.ZS:JPN |
| worldbank.employment&#95;rate.KR | worldbank&#95;employment&#95;rate.KR.A | primary | active | SL.EMP.TOTL.SP.ZS:KOR |
| worldbank.employment&#95;rate.LT | worldbank&#95;employment&#95;rate.LT.A | primary | active | SL.EMP.TOTL.SP.ZS:LTU |
| worldbank.employment&#95;rate.LU | worldbank&#95;employment&#95;rate.LU.A | primary | active | SL.EMP.TOTL.SP.ZS:LUX |
| worldbank.employment&#95;rate.LV | worldbank&#95;employment&#95;rate.LV.A | primary | active | SL.EMP.TOTL.SP.ZS:LVA |
| worldbank.employment&#95;rate.MT | worldbank&#95;employment&#95;rate.MT.A | primary | active | SL.EMP.TOTL.SP.ZS:MLT |
| worldbank.employment&#95;rate.MX | worldbank&#95;employment&#95;rate.MX.A | primary | active | SL.EMP.TOTL.SP.ZS:MEX |
| worldbank.employment&#95;rate.MY | worldbank&#95;employment&#95;rate.MY.A | primary | active | SL.EMP.TOTL.SP.ZS:MYS |
| worldbank.employment&#95;rate.MZ | worldbank&#95;employment&#95;rate.MZ.A | primary | active | SL.EMP.TOTL.SP.ZS:MOZ |
| worldbank.employment&#95;rate.NG | worldbank&#95;employment&#95;rate.NG.A | primary | active | SL.EMP.TOTL.SP.ZS:NGA |
| worldbank.employment&#95;rate.NL | worldbank&#95;employment&#95;rate.NL.A | primary | active | SL.EMP.TOTL.SP.ZS:NLD |
| worldbank.employment&#95;rate.NO | worldbank&#95;employment&#95;rate.NO.A | primary | active | SL.EMP.TOTL.SP.ZS:NOR |
| worldbank.employment&#95;rate.PL | worldbank&#95;employment&#95;rate.PL.A | primary | active | SL.EMP.TOTL.SP.ZS:POL |
| worldbank.employment&#95;rate.PT | worldbank&#95;employment&#95;rate.PT.A | primary | active | SL.EMP.TOTL.SP.ZS:PRT |
| worldbank.employment&#95;rate.RO | worldbank&#95;employment&#95;rate.RO.A | primary | active | SL.EMP.TOTL.SP.ZS:ROU |
| worldbank.employment&#95;rate.SE | worldbank&#95;employment&#95;rate.SE.A | primary | active | SL.EMP.TOTL.SP.ZS:SWE |
| worldbank.employment&#95;rate.SI | worldbank&#95;employment&#95;rate.SI.A | primary | active | SL.EMP.TOTL.SP.ZS:SVN |
| worldbank.employment&#95;rate.SK | worldbank&#95;employment&#95;rate.SK.A | primary | active | SL.EMP.TOTL.SP.ZS:SVK |
| worldbank.employment&#95;rate.ST | worldbank&#95;employment&#95;rate.ST.A | primary | active | SL.EMP.TOTL.SP.ZS:STP |
| worldbank.employment&#95;rate.TH | worldbank&#95;employment&#95;rate.TH.A | primary | active | SL.EMP.TOTL.SP.ZS:THA |
| worldbank.employment&#95;rate.TL | worldbank&#95;employment&#95;rate.TL.A | primary | active | SL.EMP.TOTL.SP.ZS:TLS |
| worldbank.employment&#95;rate.TR | worldbank&#95;employment&#95;rate.TR.A | primary | active | SL.EMP.TOTL.SP.ZS:TUR |
| worldbank.employment&#95;rate.US | worldbank&#95;employment&#95;rate.US.A | primary | active | SL.EMP.TOTL.SP.ZS:USA |
| worldbank.employment&#95;rate.ZA | worldbank&#95;employment&#95;rate.ZA.A | primary | active | SL.EMP.TOTL.SP.ZS:ZAF |
| worldbank.exports&#95;pct&#95;gdp.AO | worldbank&#95;exports&#95;pct&#95;gdp.AO.A | primary | active | NE.EXP.GNFS.ZS:AGO |
| worldbank.exports&#95;pct&#95;gdp.AR | worldbank&#95;exports&#95;pct&#95;gdp.AR.A | primary | active | NE.EXP.GNFS.ZS:ARG |
| worldbank.exports&#95;pct&#95;gdp.AT | worldbank&#95;exports&#95;pct&#95;gdp.AT.A | primary | active | NE.EXP.GNFS.ZS:AUT |
| worldbank.exports&#95;pct&#95;gdp.BE | worldbank&#95;exports&#95;pct&#95;gdp.BE.A | primary | active | NE.EXP.GNFS.ZS:BEL |
| worldbank.exports&#95;pct&#95;gdp.BG | worldbank&#95;exports&#95;pct&#95;gdp.BG.A | primary | active | NE.EXP.GNFS.ZS:BGR |
| worldbank.exports&#95;pct&#95;gdp.BR | worldbank&#95;exports&#95;pct&#95;gdp.BR.A | primary | active | NE.EXP.GNFS.ZS:BRA |
| worldbank.exports&#95;pct&#95;gdp.CA | worldbank&#95;exports&#95;pct&#95;gdp.CA.A | primary | active | NE.EXP.GNFS.ZS:CAN |
| worldbank.exports&#95;pct&#95;gdp.CH | worldbank&#95;exports&#95;pct&#95;gdp.CH.A | primary | active | NE.EXP.GNFS.ZS:CHE |
| worldbank.exports&#95;pct&#95;gdp.CL | worldbank&#95;exports&#95;pct&#95;gdp.CL.A | primary | active | NE.EXP.GNFS.ZS:CHL |
| worldbank.exports&#95;pct&#95;gdp.CN | worldbank&#95;exports&#95;pct&#95;gdp.CN.A | primary | active | NE.EXP.GNFS.ZS:CHN |
| worldbank.exports&#95;pct&#95;gdp.CV | worldbank&#95;exports&#95;pct&#95;gdp.CV.A | primary | active | NE.EXP.GNFS.ZS:CPV |
| worldbank.exports&#95;pct&#95;gdp.CY | worldbank&#95;exports&#95;pct&#95;gdp.CY.A | primary | active | NE.EXP.GNFS.ZS:CYP |
| worldbank.exports&#95;pct&#95;gdp.CZ | worldbank&#95;exports&#95;pct&#95;gdp.CZ.A | primary | active | NE.EXP.GNFS.ZS:CZE |
| worldbank.exports&#95;pct&#95;gdp.DE | worldbank&#95;exports&#95;pct&#95;gdp.DE.A | primary | active | NE.EXP.GNFS.ZS:DEU |
| worldbank.exports&#95;pct&#95;gdp.DK | worldbank&#95;exports&#95;pct&#95;gdp.DK.A | primary | active | NE.EXP.GNFS.ZS:DNK |
| worldbank.exports&#95;pct&#95;gdp.EE | worldbank&#95;exports&#95;pct&#95;gdp.EE.A | primary | active | NE.EXP.GNFS.ZS:EST |
| worldbank.exports&#95;pct&#95;gdp.EG | worldbank&#95;exports&#95;pct&#95;gdp.EG.A | primary | active | NE.EXP.GNFS.ZS:EGY |
| worldbank.exports&#95;pct&#95;gdp.ES | worldbank&#95;exports&#95;pct&#95;gdp.ES.A | primary | active | NE.EXP.GNFS.ZS:ESP |
| worldbank.exports&#95;pct&#95;gdp.FI | worldbank&#95;exports&#95;pct&#95;gdp.FI.A | primary | active | NE.EXP.GNFS.ZS:FIN |
| worldbank.exports&#95;pct&#95;gdp.FR | worldbank&#95;exports&#95;pct&#95;gdp.FR.A | primary | active | NE.EXP.GNFS.ZS:FRA |
| worldbank.exports&#95;pct&#95;gdp.GB | worldbank&#95;exports&#95;pct&#95;gdp.GB.A | primary | active | NE.EXP.GNFS.ZS:GBR |
| worldbank.exports&#95;pct&#95;gdp.GW | worldbank&#95;exports&#95;pct&#95;gdp.GW.A | primary | active | NE.EXP.GNFS.ZS:GNB |
| worldbank.exports&#95;pct&#95;gdp.HR | worldbank&#95;exports&#95;pct&#95;gdp.HR.A | primary | active | NE.EXP.GNFS.ZS:HRV |
| worldbank.exports&#95;pct&#95;gdp.HU | worldbank&#95;exports&#95;pct&#95;gdp.HU.A | primary | active | NE.EXP.GNFS.ZS:HUN |
| worldbank.exports&#95;pct&#95;gdp.ID | worldbank&#95;exports&#95;pct&#95;gdp.ID.A | primary | active | NE.EXP.GNFS.ZS:IDN |
| worldbank.exports&#95;pct&#95;gdp.IE | worldbank&#95;exports&#95;pct&#95;gdp.IE.A | primary | active | NE.EXP.GNFS.ZS:IRL |
| worldbank.exports&#95;pct&#95;gdp.IN | worldbank&#95;exports&#95;pct&#95;gdp.IN.A | primary | active | NE.EXP.GNFS.ZS:IND |
| worldbank.exports&#95;pct&#95;gdp.IT | worldbank&#95;exports&#95;pct&#95;gdp.IT.A | primary | active | NE.EXP.GNFS.ZS:ITA |
| worldbank.exports&#95;pct&#95;gdp.JP | worldbank&#95;exports&#95;pct&#95;gdp.JP.A | primary | active | NE.EXP.GNFS.ZS:JPN |
| worldbank.exports&#95;pct&#95;gdp.KR | worldbank&#95;exports&#95;pct&#95;gdp.KR.A | primary | active | NE.EXP.GNFS.ZS:KOR |
| worldbank.exports&#95;pct&#95;gdp.LT | worldbank&#95;exports&#95;pct&#95;gdp.LT.A | primary | active | NE.EXP.GNFS.ZS:LTU |
| worldbank.exports&#95;pct&#95;gdp.LU | worldbank&#95;exports&#95;pct&#95;gdp.LU.A | primary | active | NE.EXP.GNFS.ZS:LUX |
| worldbank.exports&#95;pct&#95;gdp.LV | worldbank&#95;exports&#95;pct&#95;gdp.LV.A | primary | active | NE.EXP.GNFS.ZS:LVA |
| worldbank.exports&#95;pct&#95;gdp.MT | worldbank&#95;exports&#95;pct&#95;gdp.MT.A | primary | active | NE.EXP.GNFS.ZS:MLT |
| worldbank.exports&#95;pct&#95;gdp.MX | worldbank&#95;exports&#95;pct&#95;gdp.MX.A | primary | active | NE.EXP.GNFS.ZS:MEX |
| worldbank.exports&#95;pct&#95;gdp.MY | worldbank&#95;exports&#95;pct&#95;gdp.MY.A | primary | active | NE.EXP.GNFS.ZS:MYS |
| worldbank.exports&#95;pct&#95;gdp.MZ | worldbank&#95;exports&#95;pct&#95;gdp.MZ.A | primary | active | NE.EXP.GNFS.ZS:MOZ |
| worldbank.exports&#95;pct&#95;gdp.NG | worldbank&#95;exports&#95;pct&#95;gdp.NG.A | primary | active | NE.EXP.GNFS.ZS:NGA |
| worldbank.exports&#95;pct&#95;gdp.NL | worldbank&#95;exports&#95;pct&#95;gdp.NL.A | primary | active | NE.EXP.GNFS.ZS:NLD |
| worldbank.exports&#95;pct&#95;gdp.NO | worldbank&#95;exports&#95;pct&#95;gdp.NO.A | primary | active | NE.EXP.GNFS.ZS:NOR |
| worldbank.exports&#95;pct&#95;gdp.PL | worldbank&#95;exports&#95;pct&#95;gdp.PL.A | primary | active | NE.EXP.GNFS.ZS:POL |
| worldbank.exports&#95;pct&#95;gdp.PT | worldbank&#95;exports&#95;pct&#95;gdp.PT.A | primary | active | NE.EXP.GNFS.ZS:PRT |
| worldbank.exports&#95;pct&#95;gdp.RO | worldbank&#95;exports&#95;pct&#95;gdp.RO.A | primary | active | NE.EXP.GNFS.ZS:ROU |
| worldbank.exports&#95;pct&#95;gdp.SE | worldbank&#95;exports&#95;pct&#95;gdp.SE.A | primary | active | NE.EXP.GNFS.ZS:SWE |
| worldbank.exports&#95;pct&#95;gdp.SI | worldbank&#95;exports&#95;pct&#95;gdp.SI.A | primary | active | NE.EXP.GNFS.ZS:SVN |
| worldbank.exports&#95;pct&#95;gdp.SK | worldbank&#95;exports&#95;pct&#95;gdp.SK.A | primary | active | NE.EXP.GNFS.ZS:SVK |
| worldbank.exports&#95;pct&#95;gdp.TH | worldbank&#95;exports&#95;pct&#95;gdp.TH.A | primary | active | NE.EXP.GNFS.ZS:THA |
| worldbank.exports&#95;pct&#95;gdp.TL | worldbank&#95;exports&#95;pct&#95;gdp.TL.A | primary | active | NE.EXP.GNFS.ZS:TLS |
| worldbank.exports&#95;pct&#95;gdp.TR | worldbank&#95;exports&#95;pct&#95;gdp.TR.A | primary | active | NE.EXP.GNFS.ZS:TUR |
| worldbank.exports&#95;pct&#95;gdp.US | worldbank&#95;exports&#95;pct&#95;gdp.US.A | primary | active | NE.EXP.GNFS.ZS:USA |
| worldbank.exports&#95;pct&#95;gdp.ZA | worldbank&#95;exports&#95;pct&#95;gdp.ZA.A | primary | active | NE.EXP.GNFS.ZS:ZAF |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.AO | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.AO.A | primary | active | BX.KLT.DINV.WD.GD.ZS:AGO |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.AR | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.AR.A | primary | active | BX.KLT.DINV.WD.GD.ZS:ARG |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.AT | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.AT.A | primary | active | BX.KLT.DINV.WD.GD.ZS:AUT |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.BE | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.BE.A | primary | active | BX.KLT.DINV.WD.GD.ZS:BEL |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.BG | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.BG.A | primary | active | BX.KLT.DINV.WD.GD.ZS:BGR |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.BR | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.BR.A | primary | active | BX.KLT.DINV.WD.GD.ZS:BRA |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.CA | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.CA.A | primary | active | BX.KLT.DINV.WD.GD.ZS:CAN |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.CH | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.CH.A | primary | active | BX.KLT.DINV.WD.GD.ZS:CHE |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.CL | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.CL.A | primary | active | BX.KLT.DINV.WD.GD.ZS:CHL |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.CN | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.CN.A | primary | active | BX.KLT.DINV.WD.GD.ZS:CHN |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.CV | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.CV.A | primary | active | BX.KLT.DINV.WD.GD.ZS:CPV |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.CY | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.CY.A | primary | active | BX.KLT.DINV.WD.GD.ZS:CYP |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.CZ | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.CZ.A | primary | active | BX.KLT.DINV.WD.GD.ZS:CZE |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.DE | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.DE.A | primary | active | BX.KLT.DINV.WD.GD.ZS:DEU |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.DK | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.DK.A | primary | active | BX.KLT.DINV.WD.GD.ZS:DNK |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.EE | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.EE.A | primary | active | BX.KLT.DINV.WD.GD.ZS:EST |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.EG | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.EG.A | primary | active | BX.KLT.DINV.WD.GD.ZS:EGY |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.ES | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.ES.A | primary | active | BX.KLT.DINV.WD.GD.ZS:ESP |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.FI | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.FI.A | primary | active | BX.KLT.DINV.WD.GD.ZS:FIN |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.FR | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.FR.A | primary | active | BX.KLT.DINV.WD.GD.ZS:FRA |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.GB | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.GB.A | primary | active | BX.KLT.DINV.WD.GD.ZS:GBR |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.GW | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.GW.A | primary | active | BX.KLT.DINV.WD.GD.ZS:GNB |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.HR | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.HR.A | primary | active | BX.KLT.DINV.WD.GD.ZS:HRV |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.HU | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.HU.A | primary | active | BX.KLT.DINV.WD.GD.ZS:HUN |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.ID | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.ID.A | primary | active | BX.KLT.DINV.WD.GD.ZS:IDN |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.IE | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.IE.A | primary | active | BX.KLT.DINV.WD.GD.ZS:IRL |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.IN | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.IN.A | primary | active | BX.KLT.DINV.WD.GD.ZS:IND |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.IT | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.IT.A | primary | active | BX.KLT.DINV.WD.GD.ZS:ITA |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.JP | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.JP.A | primary | active | BX.KLT.DINV.WD.GD.ZS:JPN |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.KR | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.KR.A | primary | active | BX.KLT.DINV.WD.GD.ZS:KOR |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.LT | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.LT.A | primary | active | BX.KLT.DINV.WD.GD.ZS:LTU |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.LU | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.LU.A | primary | active | BX.KLT.DINV.WD.GD.ZS:LUX |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.LV | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.LV.A | primary | active | BX.KLT.DINV.WD.GD.ZS:LVA |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.MT | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.MT.A | primary | active | BX.KLT.DINV.WD.GD.ZS:MLT |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.MX | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.MX.A | primary | active | BX.KLT.DINV.WD.GD.ZS:MEX |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.MY | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.MY.A | primary | active | BX.KLT.DINV.WD.GD.ZS:MYS |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.MZ | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.MZ.A | primary | active | BX.KLT.DINV.WD.GD.ZS:MOZ |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.NG | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.NG.A | primary | active | BX.KLT.DINV.WD.GD.ZS:NGA |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.NL | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.NL.A | primary | active | BX.KLT.DINV.WD.GD.ZS:NLD |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.NO | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.NO.A | primary | active | BX.KLT.DINV.WD.GD.ZS:NOR |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.PL | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.PL.A | primary | active | BX.KLT.DINV.WD.GD.ZS:POL |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.PT | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.PT.A | primary | active | BX.KLT.DINV.WD.GD.ZS:PRT |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.RO | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.RO.A | primary | active | BX.KLT.DINV.WD.GD.ZS:ROU |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.SE | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.SE.A | primary | active | BX.KLT.DINV.WD.GD.ZS:SWE |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.SI | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.SI.A | primary | active | BX.KLT.DINV.WD.GD.ZS:SVN |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.SK | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.SK.A | primary | active | BX.KLT.DINV.WD.GD.ZS:SVK |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.ST | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.ST.A | primary | active | BX.KLT.DINV.WD.GD.ZS:STP |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.TH | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.TH.A | primary | active | BX.KLT.DINV.WD.GD.ZS:THA |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.TL | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.TL.A | primary | active | BX.KLT.DINV.WD.GD.ZS:TLS |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.TR | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.TR.A | primary | active | BX.KLT.DINV.WD.GD.ZS:TUR |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.US | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.US.A | primary | active | BX.KLT.DINV.WD.GD.ZS:USA |
| worldbank.fdi&#95;inflows&#95;pct&#95;gdp.ZA | worldbank&#95;fdi&#95;inflows&#95;pct&#95;gdp.ZA.A | primary | active | BX.KLT.DINV.WD.GD.ZS:ZAF |
| worldbank.female&#95;labor&#95;participation.AO | worldbank&#95;female&#95;labor&#95;participation.AO.A | primary | active | SL.TLF.CACT.FE.ZS:AGO |
| worldbank.female&#95;labor&#95;participation.AR | worldbank&#95;female&#95;labor&#95;participation.AR.A | primary | active | SL.TLF.CACT.FE.ZS:ARG |
| worldbank.female&#95;labor&#95;participation.AT | worldbank&#95;female&#95;labor&#95;participation.AT.A | primary | active | SL.TLF.CACT.FE.ZS:AUT |
| worldbank.female&#95;labor&#95;participation.BE | worldbank&#95;female&#95;labor&#95;participation.BE.A | primary | active | SL.TLF.CACT.FE.ZS:BEL |
| worldbank.female&#95;labor&#95;participation.BG | worldbank&#95;female&#95;labor&#95;participation.BG.A | primary | active | SL.TLF.CACT.FE.ZS:BGR |
| worldbank.female&#95;labor&#95;participation.BR | worldbank&#95;female&#95;labor&#95;participation.BR.A | primary | active | SL.TLF.CACT.FE.ZS:BRA |
| worldbank.female&#95;labor&#95;participation.CA | worldbank&#95;female&#95;labor&#95;participation.CA.A | primary | active | SL.TLF.CACT.FE.ZS:CAN |
| worldbank.female&#95;labor&#95;participation.CH | worldbank&#95;female&#95;labor&#95;participation.CH.A | primary | active | SL.TLF.CACT.FE.ZS:CHE |
| worldbank.female&#95;labor&#95;participation.CL | worldbank&#95;female&#95;labor&#95;participation.CL.A | primary | active | SL.TLF.CACT.FE.ZS:CHL |
| worldbank.female&#95;labor&#95;participation.CN | worldbank&#95;female&#95;labor&#95;participation.CN.A | primary | active | SL.TLF.CACT.FE.ZS:CHN |
| worldbank.female&#95;labor&#95;participation.CV | worldbank&#95;female&#95;labor&#95;participation.CV.A | primary | active | SL.TLF.CACT.FE.ZS:CPV |
| worldbank.female&#95;labor&#95;participation.CY | worldbank&#95;female&#95;labor&#95;participation.CY.A | primary | active | SL.TLF.CACT.FE.ZS:CYP |
| worldbank.female&#95;labor&#95;participation.CZ | worldbank&#95;female&#95;labor&#95;participation.CZ.A | primary | active | SL.TLF.CACT.FE.ZS:CZE |
| worldbank.female&#95;labor&#95;participation.DE | worldbank&#95;female&#95;labor&#95;participation.DE.A | primary | active | SL.TLF.CACT.FE.ZS:DEU |
| worldbank.female&#95;labor&#95;participation.DK | worldbank&#95;female&#95;labor&#95;participation.DK.A | primary | active | SL.TLF.CACT.FE.ZS:DNK |
| worldbank.female&#95;labor&#95;participation.EE | worldbank&#95;female&#95;labor&#95;participation.EE.A | primary | active | SL.TLF.CACT.FE.ZS:EST |
| worldbank.female&#95;labor&#95;participation.EG | worldbank&#95;female&#95;labor&#95;participation.EG.A | primary | active | SL.TLF.CACT.FE.ZS:EGY |
| worldbank.female&#95;labor&#95;participation.ES | worldbank&#95;female&#95;labor&#95;participation.ES.A | primary | active | SL.TLF.CACT.FE.ZS:ESP |
| worldbank.female&#95;labor&#95;participation.FI | worldbank&#95;female&#95;labor&#95;participation.FI.A | primary | active | SL.TLF.CACT.FE.ZS:FIN |
| worldbank.female&#95;labor&#95;participation.FR | worldbank&#95;female&#95;labor&#95;participation.FR.A | primary | active | SL.TLF.CACT.FE.ZS:FRA |
| worldbank.female&#95;labor&#95;participation.GB | worldbank&#95;female&#95;labor&#95;participation.GB.A | primary | active | SL.TLF.CACT.FE.ZS:GBR |
| worldbank.female&#95;labor&#95;participation.GW | worldbank&#95;female&#95;labor&#95;participation.GW.A | primary | active | SL.TLF.CACT.FE.ZS:GNB |
| worldbank.female&#95;labor&#95;participation.HR | worldbank&#95;female&#95;labor&#95;participation.HR.A | primary | active | SL.TLF.CACT.FE.ZS:HRV |
| worldbank.female&#95;labor&#95;participation.HU | worldbank&#95;female&#95;labor&#95;participation.HU.A | primary | active | SL.TLF.CACT.FE.ZS:HUN |
| worldbank.female&#95;labor&#95;participation.ID | worldbank&#95;female&#95;labor&#95;participation.ID.A | primary | active | SL.TLF.CACT.FE.ZS:IDN |
| worldbank.female&#95;labor&#95;participation.IE | worldbank&#95;female&#95;labor&#95;participation.IE.A | primary | active | SL.TLF.CACT.FE.ZS:IRL |
| worldbank.female&#95;labor&#95;participation.IN | worldbank&#95;female&#95;labor&#95;participation.IN.A | primary | active | SL.TLF.CACT.FE.ZS:IND |
| worldbank.female&#95;labor&#95;participation.IT | worldbank&#95;female&#95;labor&#95;participation.IT.A | primary | active | SL.TLF.CACT.FE.ZS:ITA |
| worldbank.female&#95;labor&#95;participation.JP | worldbank&#95;female&#95;labor&#95;participation.JP.A | primary | active | SL.TLF.CACT.FE.ZS:JPN |
| worldbank.female&#95;labor&#95;participation.KR | worldbank&#95;female&#95;labor&#95;participation.KR.A | primary | active | SL.TLF.CACT.FE.ZS:KOR |
| worldbank.female&#95;labor&#95;participation.LT | worldbank&#95;female&#95;labor&#95;participation.LT.A | primary | active | SL.TLF.CACT.FE.ZS:LTU |
| worldbank.female&#95;labor&#95;participation.LU | worldbank&#95;female&#95;labor&#95;participation.LU.A | primary | active | SL.TLF.CACT.FE.ZS:LUX |
| worldbank.female&#95;labor&#95;participation.LV | worldbank&#95;female&#95;labor&#95;participation.LV.A | primary | active | SL.TLF.CACT.FE.ZS:LVA |
| worldbank.female&#95;labor&#95;participation.MT | worldbank&#95;female&#95;labor&#95;participation.MT.A | primary | active | SL.TLF.CACT.FE.ZS:MLT |
| worldbank.female&#95;labor&#95;participation.MX | worldbank&#95;female&#95;labor&#95;participation.MX.A | primary | active | SL.TLF.CACT.FE.ZS:MEX |
| worldbank.female&#95;labor&#95;participation.MY | worldbank&#95;female&#95;labor&#95;participation.MY.A | primary | active | SL.TLF.CACT.FE.ZS:MYS |
| worldbank.female&#95;labor&#95;participation.MZ | worldbank&#95;female&#95;labor&#95;participation.MZ.A | primary | active | SL.TLF.CACT.FE.ZS:MOZ |
| worldbank.female&#95;labor&#95;participation.NG | worldbank&#95;female&#95;labor&#95;participation.NG.A | primary | active | SL.TLF.CACT.FE.ZS:NGA |
| worldbank.female&#95;labor&#95;participation.NL | worldbank&#95;female&#95;labor&#95;participation.NL.A | primary | active | SL.TLF.CACT.FE.ZS:NLD |
| worldbank.female&#95;labor&#95;participation.NO | worldbank&#95;female&#95;labor&#95;participation.NO.A | primary | active | SL.TLF.CACT.FE.ZS:NOR |
| worldbank.female&#95;labor&#95;participation.PL | worldbank&#95;female&#95;labor&#95;participation.PL.A | primary | active | SL.TLF.CACT.FE.ZS:POL |
| worldbank.female&#95;labor&#95;participation.PT | worldbank&#95;female&#95;labor&#95;participation.PT.A | primary | active | SL.TLF.CACT.FE.ZS:PRT |
| worldbank.female&#95;labor&#95;participation.RO | worldbank&#95;female&#95;labor&#95;participation.RO.A | primary | active | SL.TLF.CACT.FE.ZS:ROU |
| worldbank.female&#95;labor&#95;participation.SE | worldbank&#95;female&#95;labor&#95;participation.SE.A | primary | active | SL.TLF.CACT.FE.ZS:SWE |
| worldbank.female&#95;labor&#95;participation.SI | worldbank&#95;female&#95;labor&#95;participation.SI.A | primary | active | SL.TLF.CACT.FE.ZS:SVN |
| worldbank.female&#95;labor&#95;participation.SK | worldbank&#95;female&#95;labor&#95;participation.SK.A | primary | active | SL.TLF.CACT.FE.ZS:SVK |
| worldbank.female&#95;labor&#95;participation.ST | worldbank&#95;female&#95;labor&#95;participation.ST.A | primary | active | SL.TLF.CACT.FE.ZS:STP |
| worldbank.female&#95;labor&#95;participation.TH | worldbank&#95;female&#95;labor&#95;participation.TH.A | primary | active | SL.TLF.CACT.FE.ZS:THA |
| worldbank.female&#95;labor&#95;participation.TL | worldbank&#95;female&#95;labor&#95;participation.TL.A | primary | active | SL.TLF.CACT.FE.ZS:TLS |
| worldbank.female&#95;labor&#95;participation.TR | worldbank&#95;female&#95;labor&#95;participation.TR.A | primary | active | SL.TLF.CACT.FE.ZS:TUR |
| worldbank.female&#95;labor&#95;participation.US | worldbank&#95;female&#95;labor&#95;participation.US.A | primary | active | SL.TLF.CACT.FE.ZS:USA |
| worldbank.female&#95;labor&#95;participation.ZA | worldbank&#95;female&#95;labor&#95;participation.ZA.A | primary | active | SL.TLF.CACT.FE.ZS:ZAF |
| worldbank.gdp&#95;growth.AO | worldbank&#95;gdp&#95;growth.AO.A | primary | active | NY.GDP.MKTP.KD.ZG:AGO |
| worldbank.gdp&#95;growth.AR | worldbank&#95;gdp&#95;growth.AR.A | primary | active | NY.GDP.MKTP.KD.ZG:ARG |
| worldbank.gdp&#95;growth.AT | worldbank&#95;gdp&#95;growth.AT.A | primary | active | NY.GDP.MKTP.KD.ZG:AUT |
| worldbank.gdp&#95;growth.BE | worldbank&#95;gdp&#95;growth.BE.A | primary | active | NY.GDP.MKTP.KD.ZG:BEL |
| worldbank.gdp&#95;growth.BG | worldbank&#95;gdp&#95;growth.BG.A | primary | active | NY.GDP.MKTP.KD.ZG:BGR |
| worldbank.gdp&#95;growth.BR | worldbank&#95;gdp&#95;growth.BR.A | primary | active | NY.GDP.MKTP.KD.ZG:BRA |
| worldbank.gdp&#95;growth.CA | worldbank&#95;gdp&#95;growth.CA.A | primary | active | NY.GDP.MKTP.KD.ZG:CAN |
| worldbank.gdp&#95;growth.CH | worldbank&#95;gdp&#95;growth.CH.A | primary | active | NY.GDP.MKTP.KD.ZG:CHE |
| worldbank.gdp&#95;growth.CL | worldbank&#95;gdp&#95;growth.CL.A | primary | active | NY.GDP.MKTP.KD.ZG:CHL |
| worldbank.gdp&#95;growth.CN | worldbank&#95;gdp&#95;growth.CN.A | primary | active | NY.GDP.MKTP.KD.ZG:CHN |
| worldbank.gdp&#95;growth.CV | worldbank&#95;gdp&#95;growth.CV.A | primary | active | NY.GDP.MKTP.KD.ZG:CPV |
| worldbank.gdp&#95;growth.CY | worldbank&#95;gdp&#95;growth.CY.A | primary | active | NY.GDP.MKTP.KD.ZG:CYP |
| worldbank.gdp&#95;growth.CZ | worldbank&#95;gdp&#95;growth.CZ.A | primary | active | NY.GDP.MKTP.KD.ZG:CZE |
| worldbank.gdp&#95;growth.DE | worldbank&#95;gdp&#95;growth.DE.A | primary | active | NY.GDP.MKTP.KD.ZG:DEU |
| worldbank.gdp&#95;growth.DK | worldbank&#95;gdp&#95;growth.DK.A | primary | active | NY.GDP.MKTP.KD.ZG:DNK |
| worldbank.gdp&#95;growth.EE | worldbank&#95;gdp&#95;growth.EE.A | primary | active | NY.GDP.MKTP.KD.ZG:EST |
| worldbank.gdp&#95;growth.EG | worldbank&#95;gdp&#95;growth.EG.A | primary | active | NY.GDP.MKTP.KD.ZG:EGY |
| worldbank.gdp&#95;growth.ES | worldbank&#95;gdp&#95;growth.ES.A | primary | active | NY.GDP.MKTP.KD.ZG:ESP |
| worldbank.gdp&#95;growth.EU | worldbank&#95;gdp&#95;growth.EU.A | primary | active | NY.GDP.MKTP.KD.ZG:EUU |
| worldbank.gdp&#95;growth.FI | worldbank&#95;gdp&#95;growth.FI.A | primary | active | NY.GDP.MKTP.KD.ZG:FIN |
| worldbank.gdp&#95;growth.FR | worldbank&#95;gdp&#95;growth.FR.A | primary | active | NY.GDP.MKTP.KD.ZG:FRA |
| worldbank.gdp&#95;growth.GB | worldbank&#95;gdp&#95;growth.GB.A | primary | active | NY.GDP.MKTP.KD.ZG:GBR |
| worldbank.gdp&#95;growth.GR | worldbank&#95;gdp&#95;growth.GR.A | primary | active | NY.GDP.MKTP.KD.ZG:GRC |
| worldbank.gdp&#95;growth.GW | worldbank&#95;gdp&#95;growth.GW.A | primary | active | NY.GDP.MKTP.KD.ZG:GNB |
| worldbank.gdp&#95;growth.HR | worldbank&#95;gdp&#95;growth.HR.A | primary | active | NY.GDP.MKTP.KD.ZG:HRV |
| worldbank.gdp&#95;growth.HU | worldbank&#95;gdp&#95;growth.HU.A | primary | active | NY.GDP.MKTP.KD.ZG:HUN |
| worldbank.gdp&#95;growth.ID | worldbank&#95;gdp&#95;growth.ID.A | primary | active | NY.GDP.MKTP.KD.ZG:IDN |
| worldbank.gdp&#95;growth.IE | worldbank&#95;gdp&#95;growth.IE.A | primary | active | NY.GDP.MKTP.KD.ZG:IRL |
| worldbank.gdp&#95;growth.IN | worldbank&#95;gdp&#95;growth.IN.A | primary | active | NY.GDP.MKTP.KD.ZG:IND |
| worldbank.gdp&#95;growth.IT | worldbank&#95;gdp&#95;growth.IT.A | primary | active | NY.GDP.MKTP.KD.ZG:ITA |
| worldbank.gdp&#95;growth.JP | worldbank&#95;gdp&#95;growth.JP.A | primary | active | NY.GDP.MKTP.KD.ZG:JPN |
| worldbank.gdp&#95;growth.KR | worldbank&#95;gdp&#95;growth.KR.A | primary | active | NY.GDP.MKTP.KD.ZG:KOR |
| worldbank.gdp&#95;growth.LT | worldbank&#95;gdp&#95;growth.LT.A | primary | active | NY.GDP.MKTP.KD.ZG:LTU |
| worldbank.gdp&#95;growth.LU | worldbank&#95;gdp&#95;growth.LU.A | primary | active | NY.GDP.MKTP.KD.ZG:LUX |
| worldbank.gdp&#95;growth.LV | worldbank&#95;gdp&#95;growth.LV.A | primary | active | NY.GDP.MKTP.KD.ZG:LVA |
| worldbank.gdp&#95;growth.MT | worldbank&#95;gdp&#95;growth.MT.A | primary | active | NY.GDP.MKTP.KD.ZG:MLT |
| worldbank.gdp&#95;growth.MX | worldbank&#95;gdp&#95;growth.MX.A | primary | active | NY.GDP.MKTP.KD.ZG:MEX |
| worldbank.gdp&#95;growth.MY | worldbank&#95;gdp&#95;growth.MY.A | primary | active | NY.GDP.MKTP.KD.ZG:MYS |
| worldbank.gdp&#95;growth.MZ | worldbank&#95;gdp&#95;growth.MZ.A | primary | active | NY.GDP.MKTP.KD.ZG:MOZ |
| worldbank.gdp&#95;growth.NG | worldbank&#95;gdp&#95;growth.NG.A | primary | active | NY.GDP.MKTP.KD.ZG:NGA |
| worldbank.gdp&#95;growth.NL | worldbank&#95;gdp&#95;growth.NL.A | primary | active | NY.GDP.MKTP.KD.ZG:NLD |
| worldbank.gdp&#95;growth.NO | worldbank&#95;gdp&#95;growth.NO.A | primary | active | NY.GDP.MKTP.KD.ZG:NOR |
| worldbank.gdp&#95;growth.PL | worldbank&#95;gdp&#95;growth.PL.A | primary | active | NY.GDP.MKTP.KD.ZG:POL |
| worldbank.gdp&#95;growth.PT | worldbank&#95;gdp&#95;growth.PT.A | primary | active | NY.GDP.MKTP.KD.ZG:PRT |
| worldbank.gdp&#95;growth.RO | worldbank&#95;gdp&#95;growth.RO.A | primary | active | NY.GDP.MKTP.KD.ZG:ROU |
| worldbank.gdp&#95;growth.SE | worldbank&#95;gdp&#95;growth.SE.A | primary | active | NY.GDP.MKTP.KD.ZG:SWE |
| worldbank.gdp&#95;growth.SI | worldbank&#95;gdp&#95;growth.SI.A | primary | active | NY.GDP.MKTP.KD.ZG:SVN |
| worldbank.gdp&#95;growth.SK | worldbank&#95;gdp&#95;growth.SK.A | primary | active | NY.GDP.MKTP.KD.ZG:SVK |
| worldbank.gdp&#95;growth.ST | worldbank&#95;gdp&#95;growth.ST.A | primary | active | NY.GDP.MKTP.KD.ZG:STP |
| worldbank.gdp&#95;growth.TH | worldbank&#95;gdp&#95;growth.TH.A | primary | active | NY.GDP.MKTP.KD.ZG:THA |
| worldbank.gdp&#95;growth.TL | worldbank&#95;gdp&#95;growth.TL.A | primary | active | NY.GDP.MKTP.KD.ZG:TLS |
| worldbank.gdp&#95;growth.TR | worldbank&#95;gdp&#95;growth.TR.A | primary | active | NY.GDP.MKTP.KD.ZG:TUR |
| worldbank.gdp&#95;growth.US | worldbank&#95;gdp&#95;growth.US.A | primary | active | NY.GDP.MKTP.KD.ZG:USA |
| worldbank.gdp&#95;growth.ZA | worldbank&#95;gdp&#95;growth.ZA.A | primary | active | NY.GDP.MKTP.KD.ZG:ZAF |
| worldbank.gdp&#95;per&#95;capita.AO | worldbank&#95;gdp&#95;per&#95;capita.AO.A | primary | active | NY.GDP.PCAP.CD:AGO |
| worldbank.gdp&#95;per&#95;capita.AR | worldbank&#95;gdp&#95;per&#95;capita.AR.A | primary | active | NY.GDP.PCAP.CD:ARG |
| worldbank.gdp&#95;per&#95;capita.AT | worldbank&#95;gdp&#95;per&#95;capita.AT.A | primary | active | NY.GDP.PCAP.CD:AUT |
| worldbank.gdp&#95;per&#95;capita.BE | worldbank&#95;gdp&#95;per&#95;capita.BE.A | primary | active | NY.GDP.PCAP.CD:BEL |
| worldbank.gdp&#95;per&#95;capita.BG | worldbank&#95;gdp&#95;per&#95;capita.BG.A | primary | active | NY.GDP.PCAP.CD:BGR |
| worldbank.gdp&#95;per&#95;capita.BR | worldbank&#95;gdp&#95;per&#95;capita.BR.A | primary | active | NY.GDP.PCAP.CD:BRA |
| worldbank.gdp&#95;per&#95;capita.CA | worldbank&#95;gdp&#95;per&#95;capita.CA.A | primary | active | NY.GDP.PCAP.CD:CAN |
| worldbank.gdp&#95;per&#95;capita.CH | worldbank&#95;gdp&#95;per&#95;capita.CH.A | primary | active | NY.GDP.PCAP.CD:CHE |
| worldbank.gdp&#95;per&#95;capita.CL | worldbank&#95;gdp&#95;per&#95;capita.CL.A | primary | active | NY.GDP.PCAP.CD:CHL |
| worldbank.gdp&#95;per&#95;capita.CN | worldbank&#95;gdp&#95;per&#95;capita.CN.A | primary | active | NY.GDP.PCAP.CD:CHN |
| worldbank.gdp&#95;per&#95;capita.CV | worldbank&#95;gdp&#95;per&#95;capita.CV.A | primary | active | NY.GDP.PCAP.CD:CPV |
| worldbank.gdp&#95;per&#95;capita.CY | worldbank&#95;gdp&#95;per&#95;capita.CY.A | primary | active | NY.GDP.PCAP.CD:CYP |
| worldbank.gdp&#95;per&#95;capita.CZ | worldbank&#95;gdp&#95;per&#95;capita.CZ.A | primary | active | NY.GDP.PCAP.CD:CZE |
| worldbank.gdp&#95;per&#95;capita.DE | worldbank&#95;gdp&#95;per&#95;capita.DE.A | primary | active | NY.GDP.PCAP.CD:DEU |
| worldbank.gdp&#95;per&#95;capita.DK | worldbank&#95;gdp&#95;per&#95;capita.DK.A | primary | active | NY.GDP.PCAP.CD:DNK |
| worldbank.gdp&#95;per&#95;capita.EE | worldbank&#95;gdp&#95;per&#95;capita.EE.A | primary | active | NY.GDP.PCAP.CD:EST |
| worldbank.gdp&#95;per&#95;capita.EG | worldbank&#95;gdp&#95;per&#95;capita.EG.A | primary | active | NY.GDP.PCAP.CD:EGY |
| worldbank.gdp&#95;per&#95;capita.ES | worldbank&#95;gdp&#95;per&#95;capita.ES.A | primary | active | NY.GDP.PCAP.CD:ESP |
| worldbank.gdp&#95;per&#95;capita.EU | worldbank&#95;gdp&#95;per&#95;capita.EU.A | primary | active | NY.GDP.PCAP.CD:EUU |
| worldbank.gdp&#95;per&#95;capita.FI | worldbank&#95;gdp&#95;per&#95;capita.FI.A | primary | active | NY.GDP.PCAP.CD:FIN |
| worldbank.gdp&#95;per&#95;capita.FR | worldbank&#95;gdp&#95;per&#95;capita.FR.A | primary | active | NY.GDP.PCAP.CD:FRA |
| worldbank.gdp&#95;per&#95;capita.GB | worldbank&#95;gdp&#95;per&#95;capita.GB.A | primary | active | NY.GDP.PCAP.CD:GBR |
| worldbank.gdp&#95;per&#95;capita.GR | worldbank&#95;gdp&#95;per&#95;capita.GR.A | primary | active | NY.GDP.PCAP.CD:GRC |
| worldbank.gdp&#95;per&#95;capita.GW | worldbank&#95;gdp&#95;per&#95;capita.GW.A | primary | active | NY.GDP.PCAP.CD:GNB |
| worldbank.gdp&#95;per&#95;capita.HR | worldbank&#95;gdp&#95;per&#95;capita.HR.A | primary | active | NY.GDP.PCAP.CD:HRV |
| worldbank.gdp&#95;per&#95;capita.HU | worldbank&#95;gdp&#95;per&#95;capita.HU.A | primary | active | NY.GDP.PCAP.CD:HUN |
| worldbank.gdp&#95;per&#95;capita.ID | worldbank&#95;gdp&#95;per&#95;capita.ID.A | primary | active | NY.GDP.PCAP.CD:IDN |
| worldbank.gdp&#95;per&#95;capita.IE | worldbank&#95;gdp&#95;per&#95;capita.IE.A | primary | active | NY.GDP.PCAP.CD:IRL |
| worldbank.gdp&#95;per&#95;capita.IN | worldbank&#95;gdp&#95;per&#95;capita.IN.A | primary | active | NY.GDP.PCAP.CD:IND |
| worldbank.gdp&#95;per&#95;capita.IT | worldbank&#95;gdp&#95;per&#95;capita.IT.A | primary | active | NY.GDP.PCAP.CD:ITA |
| worldbank.gdp&#95;per&#95;capita.JP | worldbank&#95;gdp&#95;per&#95;capita.JP.A | primary | active | NY.GDP.PCAP.CD:JPN |
| worldbank.gdp&#95;per&#95;capita.KR | worldbank&#95;gdp&#95;per&#95;capita.KR.A | primary | active | NY.GDP.PCAP.CD:KOR |
| worldbank.gdp&#95;per&#95;capita.LT | worldbank&#95;gdp&#95;per&#95;capita.LT.A | primary | active | NY.GDP.PCAP.CD:LTU |
| worldbank.gdp&#95;per&#95;capita.LU | worldbank&#95;gdp&#95;per&#95;capita.LU.A | primary | active | NY.GDP.PCAP.CD:LUX |
| worldbank.gdp&#95;per&#95;capita.LV | worldbank&#95;gdp&#95;per&#95;capita.LV.A | primary | active | NY.GDP.PCAP.CD:LVA |
| worldbank.gdp&#95;per&#95;capita.MT | worldbank&#95;gdp&#95;per&#95;capita.MT.A | primary | active | NY.GDP.PCAP.CD:MLT |
| worldbank.gdp&#95;per&#95;capita.MX | worldbank&#95;gdp&#95;per&#95;capita.MX.A | primary | active | NY.GDP.PCAP.CD:MEX |
| worldbank.gdp&#95;per&#95;capita.MY | worldbank&#95;gdp&#95;per&#95;capita.MY.A | primary | active | NY.GDP.PCAP.CD:MYS |
| worldbank.gdp&#95;per&#95;capita.MZ | worldbank&#95;gdp&#95;per&#95;capita.MZ.A | primary | active | NY.GDP.PCAP.CD:MOZ |
| worldbank.gdp&#95;per&#95;capita.NG | worldbank&#95;gdp&#95;per&#95;capita.NG.A | primary | active | NY.GDP.PCAP.CD:NGA |
| worldbank.gdp&#95;per&#95;capita.NL | worldbank&#95;gdp&#95;per&#95;capita.NL.A | primary | active | NY.GDP.PCAP.CD:NLD |
| worldbank.gdp&#95;per&#95;capita.NO | worldbank&#95;gdp&#95;per&#95;capita.NO.A | primary | active | NY.GDP.PCAP.CD:NOR |
| worldbank.gdp&#95;per&#95;capita.PL | worldbank&#95;gdp&#95;per&#95;capita.PL.A | primary | active | NY.GDP.PCAP.CD:POL |
| worldbank.gdp&#95;per&#95;capita.PT | worldbank&#95;gdp&#95;per&#95;capita.PT.A | primary | active | NY.GDP.PCAP.CD:PRT |
| worldbank.gdp&#95;per&#95;capita.RO | worldbank&#95;gdp&#95;per&#95;capita.RO.A | primary | active | NY.GDP.PCAP.CD:ROU |
| worldbank.gdp&#95;per&#95;capita.SE | worldbank&#95;gdp&#95;per&#95;capita.SE.A | primary | active | NY.GDP.PCAP.CD:SWE |
| worldbank.gdp&#95;per&#95;capita.SI | worldbank&#95;gdp&#95;per&#95;capita.SI.A | primary | active | NY.GDP.PCAP.CD:SVN |
| worldbank.gdp&#95;per&#95;capita.SK | worldbank&#95;gdp&#95;per&#95;capita.SK.A | primary | active | NY.GDP.PCAP.CD:SVK |
| worldbank.gdp&#95;per&#95;capita.ST | worldbank&#95;gdp&#95;per&#95;capita.ST.A | primary | active | NY.GDP.PCAP.CD:STP |
| worldbank.gdp&#95;per&#95;capita.TH | worldbank&#95;gdp&#95;per&#95;capita.TH.A | primary | active | NY.GDP.PCAP.CD:THA |
| worldbank.gdp&#95;per&#95;capita.TL | worldbank&#95;gdp&#95;per&#95;capita.TL.A | primary | active | NY.GDP.PCAP.CD:TLS |
| worldbank.gdp&#95;per&#95;capita.TR | worldbank&#95;gdp&#95;per&#95;capita.TR.A | primary | active | NY.GDP.PCAP.CD:TUR |
| worldbank.gdp&#95;per&#95;capita.US | worldbank&#95;gdp&#95;per&#95;capita.US.A | primary | active | NY.GDP.PCAP.CD:USA |
| worldbank.gdp&#95;per&#95;capita.ZA | worldbank&#95;gdp&#95;per&#95;capita.ZA.A | primary | active | NY.GDP.PCAP.CD:ZAF |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.AO | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.AO.A | primary | inactive | NY.GDP.PCAP.PP.CD:AGO |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.AR | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.AR.A | primary | inactive | NY.GDP.PCAP.PP.CD:ARG |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.AT | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.AT.A | primary | inactive | NY.GDP.PCAP.PP.CD:AUT |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.BE | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.BE.A | primary | inactive | NY.GDP.PCAP.PP.CD:BEL |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.BG | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.BG.A | primary | inactive | NY.GDP.PCAP.PP.CD:BGR |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.BR | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.BR.A | primary | inactive | NY.GDP.PCAP.PP.CD:BRA |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.CA | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.CA.A | primary | inactive | NY.GDP.PCAP.PP.CD:CAN |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.CH | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.CH.A | primary | inactive | NY.GDP.PCAP.PP.CD:CHE |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.CL | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.CL.A | primary | inactive | NY.GDP.PCAP.PP.CD:CHL |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.CN | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.CN.A | primary | inactive | NY.GDP.PCAP.PP.CD:CHN |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.CV | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.CV.A | primary | inactive | NY.GDP.PCAP.PP.CD:CPV |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.CY | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.CY.A | primary | inactive | NY.GDP.PCAP.PP.CD:CYP |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.CZ | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.CZ.A | primary | inactive | NY.GDP.PCAP.PP.CD:CZE |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.DE | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.DE.A | primary | inactive | NY.GDP.PCAP.PP.CD:DEU |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.DK | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.DK.A | primary | inactive | NY.GDP.PCAP.PP.CD:DNK |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.EE | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.EE.A | primary | inactive | NY.GDP.PCAP.PP.CD:EST |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.EG | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.EG.A | primary | inactive | NY.GDP.PCAP.PP.CD:EGY |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.ES | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.ES.A | primary | inactive | NY.GDP.PCAP.PP.CD:ESP |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.EU | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.EU.A | primary | inactive | NY.GDP.PCAP.PP.CD:EUU |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.FI | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.FI.A | primary | inactive | NY.GDP.PCAP.PP.CD:FIN |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.FR | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.FR.A | primary | inactive | NY.GDP.PCAP.PP.CD:FRA |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.GB | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.GB.A | primary | inactive | NY.GDP.PCAP.PP.CD:GBR |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.GW | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.GW.A | primary | inactive | NY.GDP.PCAP.PP.CD:GNB |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.HR | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.HR.A | primary | inactive | NY.GDP.PCAP.PP.CD:HRV |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.HU | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.HU.A | primary | inactive | NY.GDP.PCAP.PP.CD:HUN |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.ID | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.ID.A | primary | inactive | NY.GDP.PCAP.PP.CD:IDN |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.IE | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.IE.A | primary | inactive | NY.GDP.PCAP.PP.CD:IRL |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.IN | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.IN.A | primary | inactive | NY.GDP.PCAP.PP.CD:IND |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.IT | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.IT.A | primary | inactive | NY.GDP.PCAP.PP.CD:ITA |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.JP | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.JP.A | primary | inactive | NY.GDP.PCAP.PP.CD:JPN |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.KR | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.KR.A | primary | inactive | NY.GDP.PCAP.PP.CD:KOR |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.LU | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.LU.A | primary | inactive | NY.GDP.PCAP.PP.CD:LUX |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.LV | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.LV.A | primary | inactive | NY.GDP.PCAP.PP.CD:LVA |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.MT | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.MT.A | primary | inactive | NY.GDP.PCAP.PP.CD:MLT |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.MX | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.MX.A | primary | inactive | NY.GDP.PCAP.PP.CD:MEX |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.MY | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.MY.A | primary | inactive | NY.GDP.PCAP.PP.CD:MYS |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.MZ | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.MZ.A | primary | inactive | NY.GDP.PCAP.PP.CD:MOZ |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.NG | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.NG.A | primary | inactive | NY.GDP.PCAP.PP.CD:NGA |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.NL | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.NL.A | primary | inactive | NY.GDP.PCAP.PP.CD:NLD |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.NO | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.NO.A | primary | inactive | NY.GDP.PCAP.PP.CD:NOR |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.PL | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.PL.A | primary | inactive | NY.GDP.PCAP.PP.CD:POL |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.PT | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.PT.A | primary | inactive | NY.GDP.PCAP.PP.CD:PRT |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.RO | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.RO.A | primary | inactive | NY.GDP.PCAP.PP.CD:ROU |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.SE | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.SE.A | primary | inactive | NY.GDP.PCAP.PP.CD:SWE |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.SI | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.SI.A | primary | inactive | NY.GDP.PCAP.PP.CD:SVN |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.SK | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.SK.A | primary | inactive | NY.GDP.PCAP.PP.CD:SVK |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.ST | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.ST.A | primary | inactive | NY.GDP.PCAP.PP.CD:STP |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.TH | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.TH.A | primary | inactive | NY.GDP.PCAP.PP.CD:THA |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.TL | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.TL.A | primary | inactive | NY.GDP.PCAP.PP.CD:TLS |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.TR | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.TR.A | primary | inactive | NY.GDP.PCAP.PP.CD:TUR |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.US | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.US.A | primary | inactive | NY.GDP.PCAP.PP.CD:USA |
| worldbank.gdp&#95;per&#95;capita&#95;ppp.ZA | worldbank&#95;gdp&#95;per&#95;capita&#95;ppp.ZA.A | primary | inactive | NY.GDP.PCAP.PP.CD:ZAF |
| worldbank.gdp&#95;usd.AO | worldbank&#95;gdp&#95;usd.AO.A | primary | active | NY.GDP.MKTP.CD:AGO |
| worldbank.gdp&#95;usd.AR | worldbank&#95;gdp&#95;usd.AR.A | primary | active | NY.GDP.MKTP.CD:ARG |
| worldbank.gdp&#95;usd.AT | worldbank&#95;gdp&#95;usd.AT.A | primary | active | NY.GDP.MKTP.CD:AUT |
| worldbank.gdp&#95;usd.BE | worldbank&#95;gdp&#95;usd.BE.A | primary | active | NY.GDP.MKTP.CD:BEL |
| worldbank.gdp&#95;usd.BG | worldbank&#95;gdp&#95;usd.BG.A | primary | active | NY.GDP.MKTP.CD:BGR |
| worldbank.gdp&#95;usd.BR | worldbank&#95;gdp&#95;usd.BR.A | primary | active | NY.GDP.MKTP.CD:BRA |
| worldbank.gdp&#95;usd.CA | worldbank&#95;gdp&#95;usd.CA.A | primary | active | NY.GDP.MKTP.CD:CAN |
| worldbank.gdp&#95;usd.CH | worldbank&#95;gdp&#95;usd.CH.A | primary | active | NY.GDP.MKTP.CD:CHE |
| worldbank.gdp&#95;usd.CL | worldbank&#95;gdp&#95;usd.CL.A | primary | active | NY.GDP.MKTP.CD:CHL |
| worldbank.gdp&#95;usd.CN | worldbank&#95;gdp&#95;usd.CN.A | primary | active | NY.GDP.MKTP.CD:CHN |
| worldbank.gdp&#95;usd.CV | worldbank&#95;gdp&#95;usd.CV.A | primary | active | NY.GDP.MKTP.CD:CPV |
| worldbank.gdp&#95;usd.CY | worldbank&#95;gdp&#95;usd.CY.A | primary | active | NY.GDP.MKTP.CD:CYP |
| worldbank.gdp&#95;usd.CZ | worldbank&#95;gdp&#95;usd.CZ.A | primary | active | NY.GDP.MKTP.CD:CZE |
| worldbank.gdp&#95;usd.DE | worldbank&#95;gdp&#95;usd.DE.A | primary | active | NY.GDP.MKTP.CD:DEU |
| worldbank.gdp&#95;usd.DK | worldbank&#95;gdp&#95;usd.DK.A | primary | active | NY.GDP.MKTP.CD:DNK |
| worldbank.gdp&#95;usd.EE | worldbank&#95;gdp&#95;usd.EE.A | primary | active | NY.GDP.MKTP.CD:EST |
| worldbank.gdp&#95;usd.EG | worldbank&#95;gdp&#95;usd.EG.A | primary | active | NY.GDP.MKTP.CD:EGY |
| worldbank.gdp&#95;usd.ES | worldbank&#95;gdp&#95;usd.ES.A | primary | active | NY.GDP.MKTP.CD:ESP |
| worldbank.gdp&#95;usd.EU | worldbank&#95;gdp&#95;usd.EU.A | primary | active | NY.GDP.MKTP.CD:EUU |
| worldbank.gdp&#95;usd.FI | worldbank&#95;gdp&#95;usd.FI.A | primary | active | NY.GDP.MKTP.CD:FIN |
| worldbank.gdp&#95;usd.FR | worldbank&#95;gdp&#95;usd.FR.A | primary | active | NY.GDP.MKTP.CD:FRA |
| worldbank.gdp&#95;usd.GB | worldbank&#95;gdp&#95;usd.GB.A | primary | active | NY.GDP.MKTP.CD:GBR |
| worldbank.gdp&#95;usd.GR | worldbank&#95;gdp&#95;usd.GR.A | primary | active | NY.GDP.MKTP.CD:GRC |
| worldbank.gdp&#95;usd.GW | worldbank&#95;gdp&#95;usd.GW.A | primary | active | NY.GDP.MKTP.CD:GNB |
| worldbank.gdp&#95;usd.HR | worldbank&#95;gdp&#95;usd.HR.A | primary | active | NY.GDP.MKTP.CD:HRV |
| worldbank.gdp&#95;usd.HU | worldbank&#95;gdp&#95;usd.HU.A | primary | active | NY.GDP.MKTP.CD:HUN |
| worldbank.gdp&#95;usd.ID | worldbank&#95;gdp&#95;usd.ID.A | primary | active | NY.GDP.MKTP.CD:IDN |
| worldbank.gdp&#95;usd.IE | worldbank&#95;gdp&#95;usd.IE.A | primary | active | NY.GDP.MKTP.CD:IRL |
| worldbank.gdp&#95;usd.IN | worldbank&#95;gdp&#95;usd.IN.A | primary | active | NY.GDP.MKTP.CD:IND |
| worldbank.gdp&#95;usd.IT | worldbank&#95;gdp&#95;usd.IT.A | primary | active | NY.GDP.MKTP.CD:ITA |
| worldbank.gdp&#95;usd.JP | worldbank&#95;gdp&#95;usd.JP.A | primary | active | NY.GDP.MKTP.CD:JPN |
| worldbank.gdp&#95;usd.KR | worldbank&#95;gdp&#95;usd.KR.A | primary | active | NY.GDP.MKTP.CD:KOR |
| worldbank.gdp&#95;usd.LT | worldbank&#95;gdp&#95;usd.LT.A | primary | active | NY.GDP.MKTP.CD:LTU |
| worldbank.gdp&#95;usd.LU | worldbank&#95;gdp&#95;usd.LU.A | primary | active | NY.GDP.MKTP.CD:LUX |
| worldbank.gdp&#95;usd.LV | worldbank&#95;gdp&#95;usd.LV.A | primary | active | NY.GDP.MKTP.CD:LVA |
| worldbank.gdp&#95;usd.MT | worldbank&#95;gdp&#95;usd.MT.A | primary | active | NY.GDP.MKTP.CD:MLT |
| worldbank.gdp&#95;usd.MX | worldbank&#95;gdp&#95;usd.MX.A | primary | active | NY.GDP.MKTP.CD:MEX |
| worldbank.gdp&#95;usd.MY | worldbank&#95;gdp&#95;usd.MY.A | primary | active | NY.GDP.MKTP.CD:MYS |
| worldbank.gdp&#95;usd.MZ | worldbank&#95;gdp&#95;usd.MZ.A | primary | active | NY.GDP.MKTP.CD:MOZ |
| worldbank.gdp&#95;usd.NG | worldbank&#95;gdp&#95;usd.NG.A | primary | active | NY.GDP.MKTP.CD:NGA |
| worldbank.gdp&#95;usd.NL | worldbank&#95;gdp&#95;usd.NL.A | primary | active | NY.GDP.MKTP.CD:NLD |
| worldbank.gdp&#95;usd.NO | worldbank&#95;gdp&#95;usd.NO.A | primary | active | NY.GDP.MKTP.CD:NOR |
| worldbank.gdp&#95;usd.PL | worldbank&#95;gdp&#95;usd.PL.A | primary | active | NY.GDP.MKTP.CD:POL |
| worldbank.gdp&#95;usd.PT | worldbank&#95;gdp&#95;usd.PT.A | primary | active | NY.GDP.MKTP.CD:PRT |
| worldbank.gdp&#95;usd.RO | worldbank&#95;gdp&#95;usd.RO.A | primary | active | NY.GDP.MKTP.CD:ROU |
| worldbank.gdp&#95;usd.SE | worldbank&#95;gdp&#95;usd.SE.A | primary | active | NY.GDP.MKTP.CD:SWE |
| worldbank.gdp&#95;usd.SI | worldbank&#95;gdp&#95;usd.SI.A | primary | active | NY.GDP.MKTP.CD:SVN |
| worldbank.gdp&#95;usd.SK | worldbank&#95;gdp&#95;usd.SK.A | primary | active | NY.GDP.MKTP.CD:SVK |
| worldbank.gdp&#95;usd.ST | worldbank&#95;gdp&#95;usd.ST.A | primary | active | NY.GDP.MKTP.CD:STP |
| worldbank.gdp&#95;usd.TH | worldbank&#95;gdp&#95;usd.TH.A | primary | active | NY.GDP.MKTP.CD:THA |
| worldbank.gdp&#95;usd.TL | worldbank&#95;gdp&#95;usd.TL.A | primary | active | NY.GDP.MKTP.CD:TLS |
| worldbank.gdp&#95;usd.TR | worldbank&#95;gdp&#95;usd.TR.A | primary | active | NY.GDP.MKTP.CD:TUR |
| worldbank.gdp&#95;usd.US | worldbank&#95;gdp&#95;usd.US.A | primary | active | NY.GDP.MKTP.CD:USA |
| worldbank.gdp&#95;usd.ZA | worldbank&#95;gdp&#95;usd.ZA.A | primary | active | NY.GDP.MKTP.CD:ZAF |
| worldbank.gini.AO | worldbank&#95;gini.AO.A | primary | active | SI.POV.GINI:AGO |
| worldbank.gini.AR | worldbank&#95;gini.AR.A | primary | active | SI.POV.GINI:ARG |
| worldbank.gini.AT | worldbank&#95;gini.AT.A | primary | active | SI.POV.GINI:AUT |
| worldbank.gini.BE | worldbank&#95;gini.BE.A | primary | active | SI.POV.GINI:BEL |
| worldbank.gini.BG | worldbank&#95;gini.BG.A | primary | active | SI.POV.GINI:BGR |
| worldbank.gini.BR | worldbank&#95;gini.BR.A | primary | active | SI.POV.GINI:BRA |
| worldbank.gini.CA | worldbank&#95;gini.CA.A | primary | active | SI.POV.GINI:CAN |
| worldbank.gini.CH | worldbank&#95;gini.CH.A | primary | active | SI.POV.GINI:CHE |
| worldbank.gini.CL | worldbank&#95;gini.CL.A | primary | active | SI.POV.GINI:CHL |
| worldbank.gini.CN | worldbank&#95;gini.CN.A | primary | active | SI.POV.GINI:CHN |
| worldbank.gini.CV | worldbank&#95;gini.CV.A | primary | active | SI.POV.GINI:CPV |
| worldbank.gini.CY | worldbank&#95;gini.CY.A | primary | active | SI.POV.GINI:CYP |
| worldbank.gini.CZ | worldbank&#95;gini.CZ.A | primary | active | SI.POV.GINI:CZE |
| worldbank.gini.DE | worldbank&#95;gini.DE.A | primary | active | SI.POV.GINI:DEU |
| worldbank.gini.DK | worldbank&#95;gini.DK.A | primary | active | SI.POV.GINI:DNK |
| worldbank.gini.EE | worldbank&#95;gini.EE.A | primary | active | SI.POV.GINI:EST |
| worldbank.gini.EG | worldbank&#95;gini.EG.A | primary | active | SI.POV.GINI:EGY |
| worldbank.gini.ES | worldbank&#95;gini.ES.A | primary | active | SI.POV.GINI:ESP |
| worldbank.gini.FI | worldbank&#95;gini.FI.A | primary | active | SI.POV.GINI:FIN |
| worldbank.gini.FR | worldbank&#95;gini.FR.A | primary | active | SI.POV.GINI:FRA |
| worldbank.gini.GB | worldbank&#95;gini.GB.A | primary | active | SI.POV.GINI:GBR |
| worldbank.gini.GW | worldbank&#95;gini.GW.A | primary | active | SI.POV.GINI:GNB |
| worldbank.gini.HR | worldbank&#95;gini.HR.A | primary | active | SI.POV.GINI:HRV |
| worldbank.gini.HU | worldbank&#95;gini.HU.A | primary | active | SI.POV.GINI:HUN |
| worldbank.gini.ID | worldbank&#95;gini.ID.A | primary | active | SI.POV.GINI:IDN |
| worldbank.gini.IE | worldbank&#95;gini.IE.A | primary | active | SI.POV.GINI:IRL |
| worldbank.gini.IN | worldbank&#95;gini.IN.A | primary | active | SI.POV.GINI:IND |
| worldbank.gini.IT | worldbank&#95;gini.IT.A | primary | active | SI.POV.GINI:ITA |
| worldbank.gini.JP | worldbank&#95;gini.JP.A | primary | active | SI.POV.GINI:JPN |
| worldbank.gini.KR | worldbank&#95;gini.KR.A | primary | active | SI.POV.GINI:KOR |
| worldbank.gini.LT | worldbank&#95;gini.LT.A | primary | active | SI.POV.GINI:LTU |
| worldbank.gini.LU | worldbank&#95;gini.LU.A | primary | active | SI.POV.GINI:LUX |
| worldbank.gini.LV | worldbank&#95;gini.LV.A | primary | active | SI.POV.GINI:LVA |
| worldbank.gini.MT | worldbank&#95;gini.MT.A | primary | active | SI.POV.GINI:MLT |
| worldbank.gini.MX | worldbank&#95;gini.MX.A | primary | active | SI.POV.GINI:MEX |
| worldbank.gini.MY | worldbank&#95;gini.MY.A | primary | active | SI.POV.GINI:MYS |
| worldbank.gini.MZ | worldbank&#95;gini.MZ.A | primary | active | SI.POV.GINI:MOZ |
| worldbank.gini.NG | worldbank&#95;gini.NG.A | primary | active | SI.POV.GINI:NGA |
| worldbank.gini.NL | worldbank&#95;gini.NL.A | primary | active | SI.POV.GINI:NLD |
| worldbank.gini.NO | worldbank&#95;gini.NO.A | primary | active | SI.POV.GINI:NOR |
| worldbank.gini.PL | worldbank&#95;gini.PL.A | primary | active | SI.POV.GINI:POL |
| worldbank.gini.PT | worldbank&#95;gini.PT.A | primary | active | SI.POV.GINI:PRT |
| worldbank.gini.RO | worldbank&#95;gini.RO.A | primary | active | SI.POV.GINI:ROU |
| worldbank.gini.SE | worldbank&#95;gini.SE.A | primary | active | SI.POV.GINI:SWE |
| worldbank.gini.SI | worldbank&#95;gini.SI.A | primary | active | SI.POV.GINI:SVN |
| worldbank.gini.SK | worldbank&#95;gini.SK.A | primary | active | SI.POV.GINI:SVK |
| worldbank.gini.ST | worldbank&#95;gini.ST.A | primary | active | SI.POV.GINI:STP |
| worldbank.gini.TH | worldbank&#95;gini.TH.A | primary | active | SI.POV.GINI:THA |
| worldbank.gini.TL | worldbank&#95;gini.TL.A | primary | active | SI.POV.GINI:TLS |
| worldbank.gini.TR | worldbank&#95;gini.TR.A | primary | active | SI.POV.GINI:TUR |
| worldbank.gini.US | worldbank&#95;gini.US.A | primary | active | SI.POV.GINI:USA |
| worldbank.gini.ZA | worldbank&#95;gini.ZA.A | primary | active | SI.POV.GINI:ZAF |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.BR | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.BR.A | primary | active | GC.DOD.TOTL.GD.ZS:BRA |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.CA | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.CA.A | primary | active | GC.DOD.TOTL.GD.ZS:CAN |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.CH | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.CH.A | primary | active | GC.DOD.TOTL.GD.ZS:CHE |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.CL | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.CL.A | primary | active | GC.DOD.TOTL.GD.ZS:CHL |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.CY | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.CY.A | primary | active | GC.DOD.TOTL.GD.ZS:CYP |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.CZ | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.CZ.A | primary | active | GC.DOD.TOTL.GD.ZS:CZE |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.DE | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.DE.A | primary | active | GC.DOD.TOTL.GD.ZS:DEU |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.DK | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.DK.A | primary | active | GC.DOD.TOTL.GD.ZS:DNK |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.EG | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.EG.A | primary | active | GC.DOD.TOTL.GD.ZS:EGY |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.ES | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.ES.A | primary | active | GC.DOD.TOTL.GD.ZS:ESP |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.FI | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.FI.A | primary | active | GC.DOD.TOTL.GD.ZS:FIN |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.GB | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.GB.A | primary | active | GC.DOD.TOTL.GD.ZS:GBR |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.HU | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.HU.A | primary | active | GC.DOD.TOTL.GD.ZS:HUN |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.ID | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.ID.A | primary | active | GC.DOD.TOTL.GD.ZS:IDN |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.IN | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.IN.A | primary | active | GC.DOD.TOTL.GD.ZS:IND |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.IT | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.IT.A | primary | active | GC.DOD.TOTL.GD.ZS:ITA |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.KR | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.KR.A | primary | active | GC.DOD.TOTL.GD.ZS:KOR |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.LU | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.LU.A | primary | active | GC.DOD.TOTL.GD.ZS:LUX |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.LV | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.LV.A | primary | active | GC.DOD.TOTL.GD.ZS:LVA |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.MT | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.MT.A | primary | active | GC.DOD.TOTL.GD.ZS:MLT |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.MX | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.MX.A | primary | active | GC.DOD.TOTL.GD.ZS:MEX |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.MY | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.MY.A | primary | active | GC.DOD.TOTL.GD.ZS:MYS |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.MZ | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.MZ.A | primary | active | GC.DOD.TOTL.GD.ZS:MOZ |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.NL | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.NL.A | primary | active | GC.DOD.TOTL.GD.ZS:NLD |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.NO | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.NO.A | primary | active | GC.DOD.TOTL.GD.ZS:NOR |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.PL | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.PL.A | primary | active | GC.DOD.TOTL.GD.ZS:POL |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.PT | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.PT.A | primary | active | GC.DOD.TOTL.GD.ZS:PRT |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.SI | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.SI.A | primary | active | GC.DOD.TOTL.GD.ZS:SVN |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.TH | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.TH.A | primary | active | GC.DOD.TOTL.GD.ZS:THA |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.TR | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.TR.A | primary | active | GC.DOD.TOTL.GD.ZS:TUR |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.US | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.US.A | primary | active | GC.DOD.TOTL.GD.ZS:USA |
| worldbank.gov&#95;debt&#95;pct&#95;gdp&#95;wb.ZA | worldbank&#95;gov&#95;debt&#95;pct&#95;gdp&#95;wb.ZA.A | primary | active | GC.DOD.TOTL.GD.ZS:ZAF |
| worldbank.imports&#95;pct&#95;gdp.AO | worldbank&#95;imports&#95;pct&#95;gdp.AO.A | primary | active | NE.IMP.GNFS.ZS:AGO |
| worldbank.imports&#95;pct&#95;gdp.AR | worldbank&#95;imports&#95;pct&#95;gdp.AR.A | primary | active | NE.IMP.GNFS.ZS:ARG |
| worldbank.imports&#95;pct&#95;gdp.AT | worldbank&#95;imports&#95;pct&#95;gdp.AT.A | primary | active | NE.IMP.GNFS.ZS:AUT |
| worldbank.imports&#95;pct&#95;gdp.BE | worldbank&#95;imports&#95;pct&#95;gdp.BE.A | primary | active | NE.IMP.GNFS.ZS:BEL |
| worldbank.imports&#95;pct&#95;gdp.BG | worldbank&#95;imports&#95;pct&#95;gdp.BG.A | primary | active | NE.IMP.GNFS.ZS:BGR |
| worldbank.imports&#95;pct&#95;gdp.BR | worldbank&#95;imports&#95;pct&#95;gdp.BR.A | primary | active | NE.IMP.GNFS.ZS:BRA |
| worldbank.imports&#95;pct&#95;gdp.CA | worldbank&#95;imports&#95;pct&#95;gdp.CA.A | primary | active | NE.IMP.GNFS.ZS:CAN |
| worldbank.imports&#95;pct&#95;gdp.CH | worldbank&#95;imports&#95;pct&#95;gdp.CH.A | primary | active | NE.IMP.GNFS.ZS:CHE |
| worldbank.imports&#95;pct&#95;gdp.CL | worldbank&#95;imports&#95;pct&#95;gdp.CL.A | primary | active | NE.IMP.GNFS.ZS:CHL |
| worldbank.imports&#95;pct&#95;gdp.CN | worldbank&#95;imports&#95;pct&#95;gdp.CN.A | primary | active | NE.IMP.GNFS.ZS:CHN |
| worldbank.imports&#95;pct&#95;gdp.CV | worldbank&#95;imports&#95;pct&#95;gdp.CV.A | primary | active | NE.IMP.GNFS.ZS:CPV |
| worldbank.imports&#95;pct&#95;gdp.CY | worldbank&#95;imports&#95;pct&#95;gdp.CY.A | primary | active | NE.IMP.GNFS.ZS:CYP |
| worldbank.imports&#95;pct&#95;gdp.CZ | worldbank&#95;imports&#95;pct&#95;gdp.CZ.A | primary | active | NE.IMP.GNFS.ZS:CZE |
| worldbank.imports&#95;pct&#95;gdp.DE | worldbank&#95;imports&#95;pct&#95;gdp.DE.A | primary | active | NE.IMP.GNFS.ZS:DEU |
| worldbank.imports&#95;pct&#95;gdp.DK | worldbank&#95;imports&#95;pct&#95;gdp.DK.A | primary | active | NE.IMP.GNFS.ZS:DNK |
| worldbank.imports&#95;pct&#95;gdp.EE | worldbank&#95;imports&#95;pct&#95;gdp.EE.A | primary | active | NE.IMP.GNFS.ZS:EST |
| worldbank.imports&#95;pct&#95;gdp.EG | worldbank&#95;imports&#95;pct&#95;gdp.EG.A | primary | active | NE.IMP.GNFS.ZS:EGY |
| worldbank.imports&#95;pct&#95;gdp.ES | worldbank&#95;imports&#95;pct&#95;gdp.ES.A | primary | active | NE.IMP.GNFS.ZS:ESP |
| worldbank.imports&#95;pct&#95;gdp.FI | worldbank&#95;imports&#95;pct&#95;gdp.FI.A | primary | active | NE.IMP.GNFS.ZS:FIN |
| worldbank.imports&#95;pct&#95;gdp.FR | worldbank&#95;imports&#95;pct&#95;gdp.FR.A | primary | active | NE.IMP.GNFS.ZS:FRA |
| worldbank.imports&#95;pct&#95;gdp.GB | worldbank&#95;imports&#95;pct&#95;gdp.GB.A | primary | active | NE.IMP.GNFS.ZS:GBR |
| worldbank.imports&#95;pct&#95;gdp.GW | worldbank&#95;imports&#95;pct&#95;gdp.GW.A | primary | active | NE.IMP.GNFS.ZS:GNB |
| worldbank.imports&#95;pct&#95;gdp.HR | worldbank&#95;imports&#95;pct&#95;gdp.HR.A | primary | active | NE.IMP.GNFS.ZS:HRV |
| worldbank.imports&#95;pct&#95;gdp.HU | worldbank&#95;imports&#95;pct&#95;gdp.HU.A | primary | active | NE.IMP.GNFS.ZS:HUN |
| worldbank.imports&#95;pct&#95;gdp.ID | worldbank&#95;imports&#95;pct&#95;gdp.ID.A | primary | active | NE.IMP.GNFS.ZS:IDN |
| worldbank.imports&#95;pct&#95;gdp.IE | worldbank&#95;imports&#95;pct&#95;gdp.IE.A | primary | active | NE.IMP.GNFS.ZS:IRL |
| worldbank.imports&#95;pct&#95;gdp.IN | worldbank&#95;imports&#95;pct&#95;gdp.IN.A | primary | active | NE.IMP.GNFS.ZS:IND |
| worldbank.imports&#95;pct&#95;gdp.IT | worldbank&#95;imports&#95;pct&#95;gdp.IT.A | primary | active | NE.IMP.GNFS.ZS:ITA |
| worldbank.imports&#95;pct&#95;gdp.JP | worldbank&#95;imports&#95;pct&#95;gdp.JP.A | primary | active | NE.IMP.GNFS.ZS:JPN |
| worldbank.imports&#95;pct&#95;gdp.KR | worldbank&#95;imports&#95;pct&#95;gdp.KR.A | primary | active | NE.IMP.GNFS.ZS:KOR |
| worldbank.imports&#95;pct&#95;gdp.LT | worldbank&#95;imports&#95;pct&#95;gdp.LT.A | primary | active | NE.IMP.GNFS.ZS:LTU |
| worldbank.imports&#95;pct&#95;gdp.LU | worldbank&#95;imports&#95;pct&#95;gdp.LU.A | primary | active | NE.IMP.GNFS.ZS:LUX |
| worldbank.imports&#95;pct&#95;gdp.LV | worldbank&#95;imports&#95;pct&#95;gdp.LV.A | primary | active | NE.IMP.GNFS.ZS:LVA |
| worldbank.imports&#95;pct&#95;gdp.MT | worldbank&#95;imports&#95;pct&#95;gdp.MT.A | primary | active | NE.IMP.GNFS.ZS:MLT |
| worldbank.imports&#95;pct&#95;gdp.MX | worldbank&#95;imports&#95;pct&#95;gdp.MX.A | primary | active | NE.IMP.GNFS.ZS:MEX |
| worldbank.imports&#95;pct&#95;gdp.MY | worldbank&#95;imports&#95;pct&#95;gdp.MY.A | primary | active | NE.IMP.GNFS.ZS:MYS |
| worldbank.imports&#95;pct&#95;gdp.MZ | worldbank&#95;imports&#95;pct&#95;gdp.MZ.A | primary | active | NE.IMP.GNFS.ZS:MOZ |
| worldbank.imports&#95;pct&#95;gdp.NG | worldbank&#95;imports&#95;pct&#95;gdp.NG.A | primary | active | NE.IMP.GNFS.ZS:NGA |
| worldbank.imports&#95;pct&#95;gdp.NL | worldbank&#95;imports&#95;pct&#95;gdp.NL.A | primary | active | NE.IMP.GNFS.ZS:NLD |
| worldbank.imports&#95;pct&#95;gdp.NO | worldbank&#95;imports&#95;pct&#95;gdp.NO.A | primary | active | NE.IMP.GNFS.ZS:NOR |
| worldbank.imports&#95;pct&#95;gdp.PL | worldbank&#95;imports&#95;pct&#95;gdp.PL.A | primary | active | NE.IMP.GNFS.ZS:POL |
| worldbank.imports&#95;pct&#95;gdp.PT | worldbank&#95;imports&#95;pct&#95;gdp.PT.A | primary | active | NE.IMP.GNFS.ZS:PRT |
| worldbank.imports&#95;pct&#95;gdp.RO | worldbank&#95;imports&#95;pct&#95;gdp.RO.A | primary | active | NE.IMP.GNFS.ZS:ROU |
| worldbank.imports&#95;pct&#95;gdp.SE | worldbank&#95;imports&#95;pct&#95;gdp.SE.A | primary | active | NE.IMP.GNFS.ZS:SWE |
| worldbank.imports&#95;pct&#95;gdp.SI | worldbank&#95;imports&#95;pct&#95;gdp.SI.A | primary | active | NE.IMP.GNFS.ZS:SVN |
| worldbank.imports&#95;pct&#95;gdp.SK | worldbank&#95;imports&#95;pct&#95;gdp.SK.A | primary | active | NE.IMP.GNFS.ZS:SVK |
| worldbank.imports&#95;pct&#95;gdp.TH | worldbank&#95;imports&#95;pct&#95;gdp.TH.A | primary | active | NE.IMP.GNFS.ZS:THA |
| worldbank.imports&#95;pct&#95;gdp.TL | worldbank&#95;imports&#95;pct&#95;gdp.TL.A | primary | active | NE.IMP.GNFS.ZS:TLS |
| worldbank.imports&#95;pct&#95;gdp.TR | worldbank&#95;imports&#95;pct&#95;gdp.TR.A | primary | active | NE.IMP.GNFS.ZS:TUR |
| worldbank.imports&#95;pct&#95;gdp.US | worldbank&#95;imports&#95;pct&#95;gdp.US.A | primary | active | NE.IMP.GNFS.ZS:USA |
| worldbank.imports&#95;pct&#95;gdp.ZA | worldbank&#95;imports&#95;pct&#95;gdp.ZA.A | primary | active | NE.IMP.GNFS.ZS:ZAF |
| worldbank.life&#95;expectancy.AO | worldbank&#95;life&#95;expectancy.AO.A | primary | active | SP.DYN.LE00.IN:AGO |
| worldbank.life&#95;expectancy.AR | worldbank&#95;life&#95;expectancy.AR.A | primary | active | SP.DYN.LE00.IN:ARG |
| worldbank.life&#95;expectancy.AT | worldbank&#95;life&#95;expectancy.AT.A | primary | active | SP.DYN.LE00.IN:AUT |
| worldbank.life&#95;expectancy.BE | worldbank&#95;life&#95;expectancy.BE.A | primary | active | SP.DYN.LE00.IN:BEL |
| worldbank.life&#95;expectancy.BG | worldbank&#95;life&#95;expectancy.BG.A | primary | active | SP.DYN.LE00.IN:BGR |
| worldbank.life&#95;expectancy.BR | worldbank&#95;life&#95;expectancy.BR.A | primary | active | SP.DYN.LE00.IN:BRA |
| worldbank.life&#95;expectancy.CA | worldbank&#95;life&#95;expectancy.CA.A | primary | active | SP.DYN.LE00.IN:CAN |
| worldbank.life&#95;expectancy.CH | worldbank&#95;life&#95;expectancy.CH.A | primary | active | SP.DYN.LE00.IN:CHE |
| worldbank.life&#95;expectancy.CL | worldbank&#95;life&#95;expectancy.CL.A | primary | active | SP.DYN.LE00.IN:CHL |
| worldbank.life&#95;expectancy.CN | worldbank&#95;life&#95;expectancy.CN.A | primary | active | SP.DYN.LE00.IN:CHN |
| worldbank.life&#95;expectancy.CV | worldbank&#95;life&#95;expectancy.CV.A | primary | active | SP.DYN.LE00.IN:CPV |
| worldbank.life&#95;expectancy.CY | worldbank&#95;life&#95;expectancy.CY.A | primary | active | SP.DYN.LE00.IN:CYP |
| worldbank.life&#95;expectancy.CZ | worldbank&#95;life&#95;expectancy.CZ.A | primary | active | SP.DYN.LE00.IN:CZE |
| worldbank.life&#95;expectancy.DE | worldbank&#95;life&#95;expectancy.DE.A | primary | active | SP.DYN.LE00.IN:DEU |
| worldbank.life&#95;expectancy.DK | worldbank&#95;life&#95;expectancy.DK.A | primary | active | SP.DYN.LE00.IN:DNK |
| worldbank.life&#95;expectancy.EE | worldbank&#95;life&#95;expectancy.EE.A | primary | active | SP.DYN.LE00.IN:EST |
| worldbank.life&#95;expectancy.EG | worldbank&#95;life&#95;expectancy.EG.A | primary | active | SP.DYN.LE00.IN:EGY |
| worldbank.life&#95;expectancy.ES | worldbank&#95;life&#95;expectancy.ES.A | primary | active | SP.DYN.LE00.IN:ESP |
| worldbank.life&#95;expectancy.EU | worldbank&#95;life&#95;expectancy.EU.A | primary | active | SP.DYN.LE00.IN:EUU |
| worldbank.life&#95;expectancy.FI | worldbank&#95;life&#95;expectancy.FI.A | primary | active | SP.DYN.LE00.IN:FIN |
| worldbank.life&#95;expectancy.FR | worldbank&#95;life&#95;expectancy.FR.A | primary | active | SP.DYN.LE00.IN:FRA |
| worldbank.life&#95;expectancy.GB | worldbank&#95;life&#95;expectancy.GB.A | primary | active | SP.DYN.LE00.IN:GBR |
| worldbank.life&#95;expectancy.GR | worldbank&#95;life&#95;expectancy.GR.A | primary | active | SP.DYN.LE00.IN:GRC |
| worldbank.life&#95;expectancy.GW | worldbank&#95;life&#95;expectancy.GW.A | primary | active | SP.DYN.LE00.IN:GNB |
| worldbank.life&#95;expectancy.HR | worldbank&#95;life&#95;expectancy.HR.A | primary | active | SP.DYN.LE00.IN:HRV |
| worldbank.life&#95;expectancy.HU | worldbank&#95;life&#95;expectancy.HU.A | primary | active | SP.DYN.LE00.IN:HUN |
| worldbank.life&#95;expectancy.ID | worldbank&#95;life&#95;expectancy.ID.A | primary | active | SP.DYN.LE00.IN:IDN |
| worldbank.life&#95;expectancy.IE | worldbank&#95;life&#95;expectancy.IE.A | primary | active | SP.DYN.LE00.IN:IRL |
| worldbank.life&#95;expectancy.IN | worldbank&#95;life&#95;expectancy.IN.A | primary | active | SP.DYN.LE00.IN:IND |
| worldbank.life&#95;expectancy.IT | worldbank&#95;life&#95;expectancy.IT.A | primary | active | SP.DYN.LE00.IN:ITA |
| worldbank.life&#95;expectancy.JP | worldbank&#95;life&#95;expectancy.JP.A | primary | active | SP.DYN.LE00.IN:JPN |
| worldbank.life&#95;expectancy.KR | worldbank&#95;life&#95;expectancy.KR.A | primary | active | SP.DYN.LE00.IN:KOR |
| worldbank.life&#95;expectancy.LT | worldbank&#95;life&#95;expectancy.LT.A | primary | active | SP.DYN.LE00.IN:LTU |
| worldbank.life&#95;expectancy.LU | worldbank&#95;life&#95;expectancy.LU.A | primary | active | SP.DYN.LE00.IN:LUX |
| worldbank.life&#95;expectancy.LV | worldbank&#95;life&#95;expectancy.LV.A | primary | active | SP.DYN.LE00.IN:LVA |
| worldbank.life&#95;expectancy.MT | worldbank&#95;life&#95;expectancy.MT.A | primary | active | SP.DYN.LE00.IN:MLT |
| worldbank.life&#95;expectancy.MX | worldbank&#95;life&#95;expectancy.MX.A | primary | active | SP.DYN.LE00.IN:MEX |
| worldbank.life&#95;expectancy.MY | worldbank&#95;life&#95;expectancy.MY.A | primary | active | SP.DYN.LE00.IN:MYS |
| worldbank.life&#95;expectancy.MZ | worldbank&#95;life&#95;expectancy.MZ.A | primary | active | SP.DYN.LE00.IN:MOZ |
| worldbank.life&#95;expectancy.NG | worldbank&#95;life&#95;expectancy.NG.A | primary | active | SP.DYN.LE00.IN:NGA |
| worldbank.life&#95;expectancy.NL | worldbank&#95;life&#95;expectancy.NL.A | primary | active | SP.DYN.LE00.IN:NLD |
| worldbank.life&#95;expectancy.NO | worldbank&#95;life&#95;expectancy.NO.A | primary | active | SP.DYN.LE00.IN:NOR |
| worldbank.life&#95;expectancy.PL | worldbank&#95;life&#95;expectancy.PL.A | primary | active | SP.DYN.LE00.IN:POL |
| worldbank.life&#95;expectancy.PT | worldbank&#95;life&#95;expectancy.PT.A | primary | active | SP.DYN.LE00.IN:PRT |
| worldbank.life&#95;expectancy.RO | worldbank&#95;life&#95;expectancy.RO.A | primary | active | SP.DYN.LE00.IN:ROU |
| worldbank.life&#95;expectancy.SE | worldbank&#95;life&#95;expectancy.SE.A | primary | active | SP.DYN.LE00.IN:SWE |
| worldbank.life&#95;expectancy.SI | worldbank&#95;life&#95;expectancy.SI.A | primary | active | SP.DYN.LE00.IN:SVN |
| worldbank.life&#95;expectancy.SK | worldbank&#95;life&#95;expectancy.SK.A | primary | active | SP.DYN.LE00.IN:SVK |
| worldbank.life&#95;expectancy.ST | worldbank&#95;life&#95;expectancy.ST.A | primary | active | SP.DYN.LE00.IN:STP |
| worldbank.life&#95;expectancy.TH | worldbank&#95;life&#95;expectancy.TH.A | primary | active | SP.DYN.LE00.IN:THA |
| worldbank.life&#95;expectancy.TL | worldbank&#95;life&#95;expectancy.TL.A | primary | active | SP.DYN.LE00.IN:TLS |
| worldbank.life&#95;expectancy.TR | worldbank&#95;life&#95;expectancy.TR.A | primary | active | SP.DYN.LE00.IN:TUR |
| worldbank.life&#95;expectancy.US | worldbank&#95;life&#95;expectancy.US.A | primary | active | SP.DYN.LE00.IN:USA |
| worldbank.life&#95;expectancy.ZA | worldbank&#95;life&#95;expectancy.ZA.A | primary | active | SP.DYN.LE00.IN:ZAF |
| worldbank.population.AO | worldbank&#95;population.AO.A | primary | active | SP.POP.TOTL:AGO |
| worldbank.population.AR | worldbank&#95;population.AR.A | primary | active | SP.POP.TOTL:ARG |
| worldbank.population.AT | worldbank&#95;population.AT.A | primary | active | SP.POP.TOTL:AUT |
| worldbank.population.BE | worldbank&#95;population.BE.A | primary | active | SP.POP.TOTL:BEL |
| worldbank.population.BG | worldbank&#95;population.BG.A | primary | active | SP.POP.TOTL:BGR |
| worldbank.population.BR | worldbank&#95;population.BR.A | primary | active | SP.POP.TOTL:BRA |
| worldbank.population.CA | worldbank&#95;population.CA.A | primary | active | SP.POP.TOTL:CAN |
| worldbank.population.CH | worldbank&#95;population.CH.A | primary | active | SP.POP.TOTL:CHE |
| worldbank.population.CL | worldbank&#95;population.CL.A | primary | active | SP.POP.TOTL:CHL |
| worldbank.population.CN | worldbank&#95;population.CN.A | primary | active | SP.POP.TOTL:CHN |
| worldbank.population.CV | worldbank&#95;population.CV.A | primary | active | SP.POP.TOTL:CPV |
| worldbank.population.CY | worldbank&#95;population.CY.A | primary | active | SP.POP.TOTL:CYP |
| worldbank.population.CZ | worldbank&#95;population.CZ.A | primary | active | SP.POP.TOTL:CZE |
| worldbank.population.DE | worldbank&#95;population.DE.A | primary | active | SP.POP.TOTL:DEU |
| worldbank.population.DK | worldbank&#95;population.DK.A | primary | active | SP.POP.TOTL:DNK |
| worldbank.population.EE | worldbank&#95;population.EE.A | primary | active | SP.POP.TOTL:EST |
| worldbank.population.EG | worldbank&#95;population.EG.A | primary | active | SP.POP.TOTL:EGY |
| worldbank.population.ES | worldbank&#95;population.ES.A | primary | active | SP.POP.TOTL:ESP |
| worldbank.population.EU | worldbank&#95;population.EU.A | primary | active | SP.POP.TOTL:EUU |
| worldbank.population.FI | worldbank&#95;population.FI.A | primary | active | SP.POP.TOTL:FIN |
| worldbank.population.FR | worldbank&#95;population.FR.A | primary | active | SP.POP.TOTL:FRA |
| worldbank.population.GB | worldbank&#95;population.GB.A | primary | active | SP.POP.TOTL:GBR |
| worldbank.population.GR | worldbank&#95;population.GR.A | primary | active | SP.POP.TOTL:GRC |
| worldbank.population.GW | worldbank&#95;population.GW.A | primary | active | SP.POP.TOTL:GNB |
| worldbank.population.HR | worldbank&#95;population.HR.A | primary | active | SP.POP.TOTL:HRV |
| worldbank.population.HU | worldbank&#95;population.HU.A | primary | active | SP.POP.TOTL:HUN |
| worldbank.population.ID | worldbank&#95;population.ID.A | primary | active | SP.POP.TOTL:IDN |
| worldbank.population.IE | worldbank&#95;population.IE.A | primary | active | SP.POP.TOTL:IRL |
| worldbank.population.IN | worldbank&#95;population.IN.A | primary | active | SP.POP.TOTL:IND |
| worldbank.population.IT | worldbank&#95;population.IT.A | primary | active | SP.POP.TOTL:ITA |
| worldbank.population.JP | worldbank&#95;population.JP.A | primary | active | SP.POP.TOTL:JPN |
| worldbank.population.KR | worldbank&#95;population.KR.A | primary | active | SP.POP.TOTL:KOR |
| worldbank.population.LT | worldbank&#95;population.LT.A | primary | active | SP.POP.TOTL:LTU |
| worldbank.population.LU | worldbank&#95;population.LU.A | primary | active | SP.POP.TOTL:LUX |
| worldbank.population.LV | worldbank&#95;population.LV.A | primary | active | SP.POP.TOTL:LVA |
| worldbank.population.MT | worldbank&#95;population.MT.A | primary | active | SP.POP.TOTL:MLT |
| worldbank.population.MX | worldbank&#95;population.MX.A | primary | active | SP.POP.TOTL:MEX |
| worldbank.population.MY | worldbank&#95;population.MY.A | primary | active | SP.POP.TOTL:MYS |
| worldbank.population.MZ | worldbank&#95;population.MZ.A | primary | active | SP.POP.TOTL:MOZ |
| worldbank.population.NG | worldbank&#95;population.NG.A | primary | active | SP.POP.TOTL:NGA |
| worldbank.population.NL | worldbank&#95;population.NL.A | primary | active | SP.POP.TOTL:NLD |
| worldbank.population.NO | worldbank&#95;population.NO.A | primary | active | SP.POP.TOTL:NOR |
| worldbank.population.PL | worldbank&#95;population.PL.A | primary | active | SP.POP.TOTL:POL |
| worldbank.population.PT | worldbank&#95;population.PT.A | primary | active | SP.POP.TOTL:PRT |
| worldbank.population.RO | worldbank&#95;population.RO.A | primary | active | SP.POP.TOTL:ROU |
| worldbank.population.SE | worldbank&#95;population.SE.A | primary | active | SP.POP.TOTL:SWE |
| worldbank.population.SI | worldbank&#95;population.SI.A | primary | active | SP.POP.TOTL:SVN |
| worldbank.population.SK | worldbank&#95;population.SK.A | primary | active | SP.POP.TOTL:SVK |
| worldbank.population.ST | worldbank&#95;population.ST.A | primary | active | SP.POP.TOTL:STP |
| worldbank.population.TH | worldbank&#95;population.TH.A | primary | active | SP.POP.TOTL:THA |
| worldbank.population.TL | worldbank&#95;population.TL.A | primary | active | SP.POP.TOTL:TLS |
| worldbank.population.TR | worldbank&#95;population.TR.A | primary | active | SP.POP.TOTL:TUR |
| worldbank.population.US | worldbank&#95;population.US.A | primary | active | SP.POP.TOTL:USA |
| worldbank.population.ZA | worldbank&#95;population.ZA.A | primary | active | SP.POP.TOTL:ZAF |
| worldbank.rnd&#95;pct&#95;gdp.AO | worldbank&#95;rnd&#95;pct&#95;gdp.AO.A | primary | active | GB.XPD.RSDV.GD.ZS:AGO |
| worldbank.rnd&#95;pct&#95;gdp.AR | worldbank&#95;rnd&#95;pct&#95;gdp.AR.A | primary | active | GB.XPD.RSDV.GD.ZS:ARG |
| worldbank.rnd&#95;pct&#95;gdp.AT | worldbank&#95;rnd&#95;pct&#95;gdp.AT.A | primary | active | GB.XPD.RSDV.GD.ZS:AUT |
| worldbank.rnd&#95;pct&#95;gdp.BE | worldbank&#95;rnd&#95;pct&#95;gdp.BE.A | primary | active | GB.XPD.RSDV.GD.ZS:BEL |
| worldbank.rnd&#95;pct&#95;gdp.BG | worldbank&#95;rnd&#95;pct&#95;gdp.BG.A | primary | active | GB.XPD.RSDV.GD.ZS:BGR |
| worldbank.rnd&#95;pct&#95;gdp.BR | worldbank&#95;rnd&#95;pct&#95;gdp.BR.A | primary | active | GB.XPD.RSDV.GD.ZS:BRA |
| worldbank.rnd&#95;pct&#95;gdp.CA | worldbank&#95;rnd&#95;pct&#95;gdp.CA.A | primary | active | GB.XPD.RSDV.GD.ZS:CAN |
| worldbank.rnd&#95;pct&#95;gdp.CH | worldbank&#95;rnd&#95;pct&#95;gdp.CH.A | primary | active | GB.XPD.RSDV.GD.ZS:CHE |
| worldbank.rnd&#95;pct&#95;gdp.CL | worldbank&#95;rnd&#95;pct&#95;gdp.CL.A | primary | active | GB.XPD.RSDV.GD.ZS:CHL |
| worldbank.rnd&#95;pct&#95;gdp.CN | worldbank&#95;rnd&#95;pct&#95;gdp.CN.A | primary | active | GB.XPD.RSDV.GD.ZS:CHN |
| worldbank.rnd&#95;pct&#95;gdp.CV | worldbank&#95;rnd&#95;pct&#95;gdp.CV.A | primary | active | GB.XPD.RSDV.GD.ZS:CPV |
| worldbank.rnd&#95;pct&#95;gdp.CY | worldbank&#95;rnd&#95;pct&#95;gdp.CY.A | primary | active | GB.XPD.RSDV.GD.ZS:CYP |
| worldbank.rnd&#95;pct&#95;gdp.CZ | worldbank&#95;rnd&#95;pct&#95;gdp.CZ.A | primary | active | GB.XPD.RSDV.GD.ZS:CZE |
| worldbank.rnd&#95;pct&#95;gdp.DE | worldbank&#95;rnd&#95;pct&#95;gdp.DE.A | primary | active | GB.XPD.RSDV.GD.ZS:DEU |
| worldbank.rnd&#95;pct&#95;gdp.DK | worldbank&#95;rnd&#95;pct&#95;gdp.DK.A | primary | active | GB.XPD.RSDV.GD.ZS:DNK |
| worldbank.rnd&#95;pct&#95;gdp.EE | worldbank&#95;rnd&#95;pct&#95;gdp.EE.A | primary | active | GB.XPD.RSDV.GD.ZS:EST |
| worldbank.rnd&#95;pct&#95;gdp.EG | worldbank&#95;rnd&#95;pct&#95;gdp.EG.A | primary | active | GB.XPD.RSDV.GD.ZS:EGY |
| worldbank.rnd&#95;pct&#95;gdp.ES | worldbank&#95;rnd&#95;pct&#95;gdp.ES.A | primary | active | GB.XPD.RSDV.GD.ZS:ESP |
| worldbank.rnd&#95;pct&#95;gdp.FI | worldbank&#95;rnd&#95;pct&#95;gdp.FI.A | primary | active | GB.XPD.RSDV.GD.ZS:FIN |
| worldbank.rnd&#95;pct&#95;gdp.FR | worldbank&#95;rnd&#95;pct&#95;gdp.FR.A | primary | active | GB.XPD.RSDV.GD.ZS:FRA |
| worldbank.rnd&#95;pct&#95;gdp.GB | worldbank&#95;rnd&#95;pct&#95;gdp.GB.A | primary | active | GB.XPD.RSDV.GD.ZS:GBR |
| worldbank.rnd&#95;pct&#95;gdp.HR | worldbank&#95;rnd&#95;pct&#95;gdp.HR.A | primary | active | GB.XPD.RSDV.GD.ZS:HRV |
| worldbank.rnd&#95;pct&#95;gdp.HU | worldbank&#95;rnd&#95;pct&#95;gdp.HU.A | primary | active | GB.XPD.RSDV.GD.ZS:HUN |
| worldbank.rnd&#95;pct&#95;gdp.ID | worldbank&#95;rnd&#95;pct&#95;gdp.ID.A | primary | active | GB.XPD.RSDV.GD.ZS:IDN |
| worldbank.rnd&#95;pct&#95;gdp.IE | worldbank&#95;rnd&#95;pct&#95;gdp.IE.A | primary | active | GB.XPD.RSDV.GD.ZS:IRL |
| worldbank.rnd&#95;pct&#95;gdp.IN | worldbank&#95;rnd&#95;pct&#95;gdp.IN.A | primary | active | GB.XPD.RSDV.GD.ZS:IND |
| worldbank.rnd&#95;pct&#95;gdp.IT | worldbank&#95;rnd&#95;pct&#95;gdp.IT.A | primary | active | GB.XPD.RSDV.GD.ZS:ITA |
| worldbank.rnd&#95;pct&#95;gdp.JP | worldbank&#95;rnd&#95;pct&#95;gdp.JP.A | primary | active | GB.XPD.RSDV.GD.ZS:JPN |
| worldbank.rnd&#95;pct&#95;gdp.KR | worldbank&#95;rnd&#95;pct&#95;gdp.KR.A | primary | active | GB.XPD.RSDV.GD.ZS:KOR |
| worldbank.rnd&#95;pct&#95;gdp.LT | worldbank&#95;rnd&#95;pct&#95;gdp.LT.A | primary | active | GB.XPD.RSDV.GD.ZS:LTU |
| worldbank.rnd&#95;pct&#95;gdp.LU | worldbank&#95;rnd&#95;pct&#95;gdp.LU.A | primary | active | GB.XPD.RSDV.GD.ZS:LUX |
| worldbank.rnd&#95;pct&#95;gdp.LV | worldbank&#95;rnd&#95;pct&#95;gdp.LV.A | primary | active | GB.XPD.RSDV.GD.ZS:LVA |
| worldbank.rnd&#95;pct&#95;gdp.MT | worldbank&#95;rnd&#95;pct&#95;gdp.MT.A | primary | active | GB.XPD.RSDV.GD.ZS:MLT |
| worldbank.rnd&#95;pct&#95;gdp.MX | worldbank&#95;rnd&#95;pct&#95;gdp.MX.A | primary | active | GB.XPD.RSDV.GD.ZS:MEX |
| worldbank.rnd&#95;pct&#95;gdp.MY | worldbank&#95;rnd&#95;pct&#95;gdp.MY.A | primary | active | GB.XPD.RSDV.GD.ZS:MYS |
| worldbank.rnd&#95;pct&#95;gdp.MZ | worldbank&#95;rnd&#95;pct&#95;gdp.MZ.A | primary | active | GB.XPD.RSDV.GD.ZS:MOZ |
| worldbank.rnd&#95;pct&#95;gdp.NG | worldbank&#95;rnd&#95;pct&#95;gdp.NG.A | primary | active | GB.XPD.RSDV.GD.ZS:NGA |
| worldbank.rnd&#95;pct&#95;gdp.NL | worldbank&#95;rnd&#95;pct&#95;gdp.NL.A | primary | active | GB.XPD.RSDV.GD.ZS:NLD |
| worldbank.rnd&#95;pct&#95;gdp.NO | worldbank&#95;rnd&#95;pct&#95;gdp.NO.A | primary | active | GB.XPD.RSDV.GD.ZS:NOR |
| worldbank.rnd&#95;pct&#95;gdp.PL | worldbank&#95;rnd&#95;pct&#95;gdp.PL.A | primary | active | GB.XPD.RSDV.GD.ZS:POL |
| worldbank.rnd&#95;pct&#95;gdp.PT | worldbank&#95;rnd&#95;pct&#95;gdp.PT.A | primary | active | GB.XPD.RSDV.GD.ZS:PRT |
| worldbank.rnd&#95;pct&#95;gdp.RO | worldbank&#95;rnd&#95;pct&#95;gdp.RO.A | primary | active | GB.XPD.RSDV.GD.ZS:ROU |
| worldbank.rnd&#95;pct&#95;gdp.SE | worldbank&#95;rnd&#95;pct&#95;gdp.SE.A | primary | active | GB.XPD.RSDV.GD.ZS:SWE |
| worldbank.rnd&#95;pct&#95;gdp.SI | worldbank&#95;rnd&#95;pct&#95;gdp.SI.A | primary | active | GB.XPD.RSDV.GD.ZS:SVN |
| worldbank.rnd&#95;pct&#95;gdp.SK | worldbank&#95;rnd&#95;pct&#95;gdp.SK.A | primary | active | GB.XPD.RSDV.GD.ZS:SVK |
| worldbank.rnd&#95;pct&#95;gdp.TH | worldbank&#95;rnd&#95;pct&#95;gdp.TH.A | primary | active | GB.XPD.RSDV.GD.ZS:THA |
| worldbank.rnd&#95;pct&#95;gdp.TR | worldbank&#95;rnd&#95;pct&#95;gdp.TR.A | primary | active | GB.XPD.RSDV.GD.ZS:TUR |
| worldbank.rnd&#95;pct&#95;gdp.US | worldbank&#95;rnd&#95;pct&#95;gdp.US.A | primary | active | GB.XPD.RSDV.GD.ZS:USA |
| worldbank.rnd&#95;pct&#95;gdp.ZA | worldbank&#95;rnd&#95;pct&#95;gdp.ZA.A | primary | active | GB.XPD.RSDV.GD.ZS:ZAF |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.AO | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.AO.A | primary | active | NE.RSB.GNFS.ZS:AGO |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.AR | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.AR.A | primary | active | NE.RSB.GNFS.ZS:ARG |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.AT | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.AT.A | primary | active | NE.RSB.GNFS.ZS:AUT |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.BE | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.BE.A | primary | active | NE.RSB.GNFS.ZS:BEL |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.BG | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.BG.A | primary | active | NE.RSB.GNFS.ZS:BGR |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.BR | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.BR.A | primary | active | NE.RSB.GNFS.ZS:BRA |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.CA | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.CA.A | primary | active | NE.RSB.GNFS.ZS:CAN |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.CH | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.CH.A | primary | active | NE.RSB.GNFS.ZS:CHE |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.CL | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.CL.A | primary | active | NE.RSB.GNFS.ZS:CHL |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.CN | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.CN.A | primary | active | NE.RSB.GNFS.ZS:CHN |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.CV | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.CV.A | primary | active | NE.RSB.GNFS.ZS:CPV |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.CY | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.CY.A | primary | active | NE.RSB.GNFS.ZS:CYP |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.CZ | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.CZ.A | primary | active | NE.RSB.GNFS.ZS:CZE |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.DE | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.DE.A | primary | active | NE.RSB.GNFS.ZS:DEU |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.DK | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.DK.A | primary | active | NE.RSB.GNFS.ZS:DNK |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.EE | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.EE.A | primary | active | NE.RSB.GNFS.ZS:EST |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.EG | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.EG.A | primary | active | NE.RSB.GNFS.ZS:EGY |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.ES | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.ES.A | primary | active | NE.RSB.GNFS.ZS:ESP |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.FI | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.FI.A | primary | active | NE.RSB.GNFS.ZS:FIN |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.FR | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.FR.A | primary | active | NE.RSB.GNFS.ZS:FRA |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.GB | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.GB.A | primary | active | NE.RSB.GNFS.ZS:GBR |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.GW | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.GW.A | primary | active | NE.RSB.GNFS.ZS:GNB |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.HR | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.HR.A | primary | active | NE.RSB.GNFS.ZS:HRV |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.HU | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.HU.A | primary | active | NE.RSB.GNFS.ZS:HUN |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.ID | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.ID.A | primary | active | NE.RSB.GNFS.ZS:IDN |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.IE | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.IE.A | primary | active | NE.RSB.GNFS.ZS:IRL |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.IN | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.IN.A | primary | active | NE.RSB.GNFS.ZS:IND |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.IT | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.IT.A | primary | active | NE.RSB.GNFS.ZS:ITA |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.JP | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.JP.A | primary | active | NE.RSB.GNFS.ZS:JPN |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.KR | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.KR.A | primary | active | NE.RSB.GNFS.ZS:KOR |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.LT | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.LT.A | primary | active | NE.RSB.GNFS.ZS:LTU |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.LU | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.LU.A | primary | active | NE.RSB.GNFS.ZS:LUX |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.LV | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.LV.A | primary | active | NE.RSB.GNFS.ZS:LVA |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.MT | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.MT.A | primary | active | NE.RSB.GNFS.ZS:MLT |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.MX | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.MX.A | primary | active | NE.RSB.GNFS.ZS:MEX |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.MY | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.MY.A | primary | active | NE.RSB.GNFS.ZS:MYS |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.MZ | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.MZ.A | primary | active | NE.RSB.GNFS.ZS:MOZ |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.NG | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.NG.A | primary | active | NE.RSB.GNFS.ZS:NGA |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.NL | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.NL.A | primary | active | NE.RSB.GNFS.ZS:NLD |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.NO | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.NO.A | primary | active | NE.RSB.GNFS.ZS:NOR |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.PL | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.PL.A | primary | active | NE.RSB.GNFS.ZS:POL |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.PT | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.PT.A | primary | active | NE.RSB.GNFS.ZS:PRT |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.RO | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.RO.A | primary | active | NE.RSB.GNFS.ZS:ROU |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.SE | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.SE.A | primary | active | NE.RSB.GNFS.ZS:SWE |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.SI | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.SI.A | primary | active | NE.RSB.GNFS.ZS:SVN |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.SK | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.SK.A | primary | active | NE.RSB.GNFS.ZS:SVK |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.TH | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.TH.A | primary | active | NE.RSB.GNFS.ZS:THA |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.TL | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.TL.A | primary | active | NE.RSB.GNFS.ZS:TLS |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.TR | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.TR.A | primary | active | NE.RSB.GNFS.ZS:TUR |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.US | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.US.A | primary | active | NE.RSB.GNFS.ZS:USA |
| worldbank.trade&#95;balance&#95;pct&#95;gdp.ZA | worldbank&#95;trade&#95;balance&#95;pct&#95;gdp.ZA.A | primary | active | NE.RSB.GNFS.ZS:ZAF |
| worldbank.unemployment&#95;wb.AO | unemployment&#95;rate.AO.A | primary | active | SL.UEM.TOTL.ZS:AGO |
| worldbank.unemployment&#95;wb.AR | unemployment&#95;rate.AR.A | primary | active | SL.UEM.TOTL.ZS:ARG |
| worldbank.unemployment&#95;wb.AT | unemployment&#95;rate.AT.A | primary | active | SL.UEM.TOTL.ZS:AUT |
| worldbank.unemployment&#95;wb.BE | unemployment&#95;rate.BE.A | primary | active | SL.UEM.TOTL.ZS:BEL |
| worldbank.unemployment&#95;wb.BG | unemployment&#95;rate.BG.A | primary | active | SL.UEM.TOTL.ZS:BGR |
| worldbank.unemployment&#95;wb.BR | unemployment&#95;rate.BR.A | primary | active | SL.UEM.TOTL.ZS:BRA |
| worldbank.unemployment&#95;wb.CA | unemployment&#95;rate.CA.A | primary | active | SL.UEM.TOTL.ZS:CAN |
| worldbank.unemployment&#95;wb.CH | unemployment&#95;rate.CH.A | primary | active | SL.UEM.TOTL.ZS:CHE |
| worldbank.unemployment&#95;wb.CL | unemployment&#95;rate.CL.A | primary | active | SL.UEM.TOTL.ZS:CHL |
| worldbank.unemployment&#95;wb.CN | unemployment&#95;rate.CN.A | primary | active | SL.UEM.TOTL.ZS:CHN |
| worldbank.unemployment&#95;wb.CV | unemployment&#95;rate.CV.A | primary | active | SL.UEM.TOTL.ZS:CPV |
| worldbank.unemployment&#95;wb.CY | unemployment&#95;rate.CY.A | primary | active | SL.UEM.TOTL.ZS:CYP |
| worldbank.unemployment&#95;wb.CZ | unemployment&#95;rate.CZ.A | primary | active | SL.UEM.TOTL.ZS:CZE |
| worldbank.unemployment&#95;wb.DE | unemployment&#95;rate.DE.A | primary | active | SL.UEM.TOTL.ZS:DEU |
| worldbank.unemployment&#95;wb.DK | unemployment&#95;rate.DK.A | primary | active | SL.UEM.TOTL.ZS:DNK |
| worldbank.unemployment&#95;wb.EE | unemployment&#95;rate.EE.A | primary | active | SL.UEM.TOTL.ZS:EST |
| worldbank.unemployment&#95;wb.EG | unemployment&#95;rate.EG.A | primary | active | SL.UEM.TOTL.ZS:EGY |
| worldbank.unemployment&#95;wb.ES | unemployment&#95;rate.ES.A | primary | active | SL.UEM.TOTL.ZS:ESP |
| worldbank.unemployment&#95;wb.EU | unemployment&#95;rate.EU.A | primary | active | SL.UEM.TOTL.ZS:EUU |
| worldbank.unemployment&#95;wb.FI | unemployment&#95;rate.FI.A | primary | active | SL.UEM.TOTL.ZS:FIN |
| worldbank.unemployment&#95;wb.FR | unemployment&#95;rate.FR.A | primary | active | SL.UEM.TOTL.ZS:FRA |
| worldbank.unemployment&#95;wb.GB | unemployment&#95;rate.GB.A | primary | active | SL.UEM.TOTL.ZS:GBR |
| worldbank.unemployment&#95;wb.GR | unemployment&#95;rate.GR.A | primary | active | SL.UEM.TOTL.ZS:GRC |
| worldbank.unemployment&#95;wb.GW | unemployment&#95;rate.GW.A | primary | active | SL.UEM.TOTL.ZS:GNB |
| worldbank.unemployment&#95;wb.HR | unemployment&#95;rate.HR.A | primary | active | SL.UEM.TOTL.ZS:HRV |
| worldbank.unemployment&#95;wb.HU | unemployment&#95;rate.HU.A | primary | active | SL.UEM.TOTL.ZS:HUN |
| worldbank.unemployment&#95;wb.ID | unemployment&#95;rate.ID.A | primary | active | SL.UEM.TOTL.ZS:IDN |
| worldbank.unemployment&#95;wb.IE | unemployment&#95;rate.IE.A | primary | active | SL.UEM.TOTL.ZS:IRL |
| worldbank.unemployment&#95;wb.IN | unemployment&#95;rate.IN.A | primary | active | SL.UEM.TOTL.ZS:IND |
| worldbank.unemployment&#95;wb.IT | unemployment&#95;rate.IT.A | primary | active | SL.UEM.TOTL.ZS:ITA |
| worldbank.unemployment&#95;wb.JP | unemployment&#95;rate.JP.A | primary | active | SL.UEM.TOTL.ZS:JPN |
| worldbank.unemployment&#95;wb.KR | unemployment&#95;rate.KR.A | primary | active | SL.UEM.TOTL.ZS:KOR |
| worldbank.unemployment&#95;wb.LT | unemployment&#95;rate.LT.A | primary | active | SL.UEM.TOTL.ZS:LTU |
| worldbank.unemployment&#95;wb.LU | unemployment&#95;rate.LU.A | primary | active | SL.UEM.TOTL.ZS:LUX |
| worldbank.unemployment&#95;wb.LV | unemployment&#95;rate.LV.A | primary | active | SL.UEM.TOTL.ZS:LVA |
| worldbank.unemployment&#95;wb.MT | unemployment&#95;rate.MT.A | primary | active | SL.UEM.TOTL.ZS:MLT |
| worldbank.unemployment&#95;wb.MX | unemployment&#95;rate.MX.A | primary | active | SL.UEM.TOTL.ZS:MEX |
| worldbank.unemployment&#95;wb.MY | unemployment&#95;rate.MY.A | primary | active | SL.UEM.TOTL.ZS:MYS |
| worldbank.unemployment&#95;wb.MZ | unemployment&#95;rate.MZ.A | primary | active | SL.UEM.TOTL.ZS:MOZ |
| worldbank.unemployment&#95;wb.NG | unemployment&#95;rate.NG.A | primary | active | SL.UEM.TOTL.ZS:NGA |
| worldbank.unemployment&#95;wb.NL | unemployment&#95;rate.NL.A | primary | active | SL.UEM.TOTL.ZS:NLD |
| worldbank.unemployment&#95;wb.NO | unemployment&#95;rate.NO.A | primary | active | SL.UEM.TOTL.ZS:NOR |
| worldbank.unemployment&#95;wb.PL | unemployment&#95;rate.PL.A | primary | active | SL.UEM.TOTL.ZS:POL |
| worldbank.unemployment&#95;wb.PT | unemployment&#95;rate.PT.A | primary | active | SL.UEM.TOTL.ZS:PRT |
| worldbank.unemployment&#95;wb.RO | unemployment&#95;rate.RO.A | primary | active | SL.UEM.TOTL.ZS:ROU |
| worldbank.unemployment&#95;wb.SE | unemployment&#95;rate.SE.A | primary | active | SL.UEM.TOTL.ZS:SWE |
| worldbank.unemployment&#95;wb.SI | unemployment&#95;rate.SI.A | primary | active | SL.UEM.TOTL.ZS:SVN |
| worldbank.unemployment&#95;wb.SK | unemployment&#95;rate.SK.A | primary | active | SL.UEM.TOTL.ZS:SVK |
| worldbank.unemployment&#95;wb.ST | unemployment&#95;rate.ST.A | primary | active | SL.UEM.TOTL.ZS:STP |
| worldbank.unemployment&#95;wb.TH | unemployment&#95;rate.TH.A | primary | active | SL.UEM.TOTL.ZS:THA |
| worldbank.unemployment&#95;wb.TL | unemployment&#95;rate.TL.A | primary | active | SL.UEM.TOTL.ZS:TLS |
| worldbank.unemployment&#95;wb.TR | unemployment&#95;rate.TR.A | primary | active | SL.UEM.TOTL.ZS:TUR |
| worldbank.unemployment&#95;wb.US | unemployment&#95;rate.US.A | primary | active | SL.UEM.TOTL.ZS:USA |
| worldbank.unemployment&#95;wb.ZA | unemployment&#95;rate.ZA.A | primary | active | SL.UEM.TOTL.ZS:ZAF |
| worldbank.urbanization.AO | worldbank&#95;urbanization.AO.A | primary | active | SP.URB.TOTL.IN.ZS:AGO |
| worldbank.urbanization.AR | worldbank&#95;urbanization.AR.A | primary | active | SP.URB.TOTL.IN.ZS:ARG |
| worldbank.urbanization.AT | worldbank&#95;urbanization.AT.A | primary | active | SP.URB.TOTL.IN.ZS:AUT |
| worldbank.urbanization.BE | worldbank&#95;urbanization.BE.A | primary | active | SP.URB.TOTL.IN.ZS:BEL |
| worldbank.urbanization.BG | worldbank&#95;urbanization.BG.A | primary | active | SP.URB.TOTL.IN.ZS:BGR |
| worldbank.urbanization.BR | worldbank&#95;urbanization.BR.A | primary | active | SP.URB.TOTL.IN.ZS:BRA |
| worldbank.urbanization.CA | worldbank&#95;urbanization.CA.A | primary | active | SP.URB.TOTL.IN.ZS:CAN |
| worldbank.urbanization.CH | worldbank&#95;urbanization.CH.A | primary | active | SP.URB.TOTL.IN.ZS:CHE |
| worldbank.urbanization.CL | worldbank&#95;urbanization.CL.A | primary | active | SP.URB.TOTL.IN.ZS:CHL |
| worldbank.urbanization.CN | worldbank&#95;urbanization.CN.A | primary | active | SP.URB.TOTL.IN.ZS:CHN |
| worldbank.urbanization.CV | worldbank&#95;urbanization.CV.A | primary | active | SP.URB.TOTL.IN.ZS:CPV |
| worldbank.urbanization.CY | worldbank&#95;urbanization.CY.A | primary | active | SP.URB.TOTL.IN.ZS:CYP |
| worldbank.urbanization.CZ | worldbank&#95;urbanization.CZ.A | primary | active | SP.URB.TOTL.IN.ZS:CZE |
| worldbank.urbanization.DE | worldbank&#95;urbanization.DE.A | primary | active | SP.URB.TOTL.IN.ZS:DEU |
| worldbank.urbanization.DK | worldbank&#95;urbanization.DK.A | primary | active | SP.URB.TOTL.IN.ZS:DNK |
| worldbank.urbanization.EE | worldbank&#95;urbanization.EE.A | primary | active | SP.URB.TOTL.IN.ZS:EST |
| worldbank.urbanization.EG | worldbank&#95;urbanization.EG.A | primary | active | SP.URB.TOTL.IN.ZS:EGY |
| worldbank.urbanization.ES | worldbank&#95;urbanization.ES.A | primary | active | SP.URB.TOTL.IN.ZS:ESP |
| worldbank.urbanization.EU | worldbank&#95;urbanization.EU.A | primary | active | SP.URB.TOTL.IN.ZS:EUU |
| worldbank.urbanization.FI | worldbank&#95;urbanization.FI.A | primary | active | SP.URB.TOTL.IN.ZS:FIN |
| worldbank.urbanization.FR | worldbank&#95;urbanization.FR.A | primary | active | SP.URB.TOTL.IN.ZS:FRA |
| worldbank.urbanization.GB | worldbank&#95;urbanization.GB.A | primary | active | SP.URB.TOTL.IN.ZS:GBR |
| worldbank.urbanization.GR | worldbank&#95;urbanization.GR.A | primary | active | SP.URB.TOTL.IN.ZS:GRC |
| worldbank.urbanization.GW | worldbank&#95;urbanization.GW.A | primary | active | SP.URB.TOTL.IN.ZS:GNB |
| worldbank.urbanization.HR | worldbank&#95;urbanization.HR.A | primary | active | SP.URB.TOTL.IN.ZS:HRV |
| worldbank.urbanization.HU | worldbank&#95;urbanization.HU.A | primary | active | SP.URB.TOTL.IN.ZS:HUN |
| worldbank.urbanization.ID | worldbank&#95;urbanization.ID.A | primary | active | SP.URB.TOTL.IN.ZS:IDN |
| worldbank.urbanization.IE | worldbank&#95;urbanization.IE.A | primary | active | SP.URB.TOTL.IN.ZS:IRL |
| worldbank.urbanization.IN | worldbank&#95;urbanization.IN.A | primary | active | SP.URB.TOTL.IN.ZS:IND |
| worldbank.urbanization.IT | worldbank&#95;urbanization.IT.A | primary | active | SP.URB.TOTL.IN.ZS:ITA |
| worldbank.urbanization.JP | worldbank&#95;urbanization.JP.A | primary | active | SP.URB.TOTL.IN.ZS:JPN |
| worldbank.urbanization.KR | worldbank&#95;urbanization.KR.A | primary | active | SP.URB.TOTL.IN.ZS:KOR |
| worldbank.urbanization.LT | worldbank&#95;urbanization.LT.A | primary | active | SP.URB.TOTL.IN.ZS:LTU |
| worldbank.urbanization.LU | worldbank&#95;urbanization.LU.A | primary | active | SP.URB.TOTL.IN.ZS:LUX |
| worldbank.urbanization.LV | worldbank&#95;urbanization.LV.A | primary | active | SP.URB.TOTL.IN.ZS:LVA |
| worldbank.urbanization.MT | worldbank&#95;urbanization.MT.A | primary | active | SP.URB.TOTL.IN.ZS:MLT |
| worldbank.urbanization.MX | worldbank&#95;urbanization.MX.A | primary | active | SP.URB.TOTL.IN.ZS:MEX |
| worldbank.urbanization.MY | worldbank&#95;urbanization.MY.A | primary | active | SP.URB.TOTL.IN.ZS:MYS |
| worldbank.urbanization.MZ | worldbank&#95;urbanization.MZ.A | primary | active | SP.URB.TOTL.IN.ZS:MOZ |
| worldbank.urbanization.NG | worldbank&#95;urbanization.NG.A | primary | active | SP.URB.TOTL.IN.ZS:NGA |
| worldbank.urbanization.NL | worldbank&#95;urbanization.NL.A | primary | active | SP.URB.TOTL.IN.ZS:NLD |
| worldbank.urbanization.NO | worldbank&#95;urbanization.NO.A | primary | active | SP.URB.TOTL.IN.ZS:NOR |
| worldbank.urbanization.PL | worldbank&#95;urbanization.PL.A | primary | active | SP.URB.TOTL.IN.ZS:POL |
| worldbank.urbanization.PT | worldbank&#95;urbanization.PT.A | primary | active | SP.URB.TOTL.IN.ZS:PRT |
| worldbank.urbanization.RO | worldbank&#95;urbanization.RO.A | primary | active | SP.URB.TOTL.IN.ZS:ROU |
| worldbank.urbanization.SE | worldbank&#95;urbanization.SE.A | primary | active | SP.URB.TOTL.IN.ZS:SWE |
| worldbank.urbanization.SI | worldbank&#95;urbanization.SI.A | primary | active | SP.URB.TOTL.IN.ZS:SVN |
| worldbank.urbanization.SK | worldbank&#95;urbanization.SK.A | primary | active | SP.URB.TOTL.IN.ZS:SVK |
| worldbank.urbanization.ST | worldbank&#95;urbanization.ST.A | primary | active | SP.URB.TOTL.IN.ZS:STP |
| worldbank.urbanization.TH | worldbank&#95;urbanization.TH.A | primary | active | SP.URB.TOTL.IN.ZS:THA |
| worldbank.urbanization.TL | worldbank&#95;urbanization.TL.A | primary | active | SP.URB.TOTL.IN.ZS:TLS |
| worldbank.urbanization.TR | worldbank&#95;urbanization.TR.A | primary | active | SP.URB.TOTL.IN.ZS:TUR |
| worldbank.urbanization.US | worldbank&#95;urbanization.US.A | primary | active | SP.URB.TOTL.IN.ZS:USA |
| worldbank.urbanization.ZA | worldbank&#95;urbanization.ZA.A | primary | active | SP.URB.TOTL.IN.ZS:ZAF |
