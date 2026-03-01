#!/usr/bin/env python3
"""
OECD Data Explorer API Client - SDMX REST
API pública, sem autenticação
Documentação: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html

Rate limits: 20 queries/min, 60 downloads/hour
Country codes: ISO alpha-3 (PRT, ESP, DEU, FRA, USA, etc.)
"""

import requests
import csv
import io
from typing import Optional, Dict, List
from datetime import datetime, timedelta


class OECDClient:
    """Cliente para OECD Data Explorer SDMX REST API"""

    BASE_URL = "https://sdmx.oecd.org/public/rest"

    # Dataflows - {agency},{DSD}@{dataflow}
    DATAFLOWS = {
        # Short-Term Economic Indicators (OECD.SDD.STES)
        "cli":       "OECD.SDD.STES,DSD_STES@DF_CLI",         # Composite Leading Indicators
        "bts":       "OECD.SDD.STES,DSD_STES@DF_BTS",         # Business Tendency Surveys
        "cs":        "OECD.SDD.STES,DSD_STES@DF_CS",          # Consumer Surveys
        "kei":       "OECD.SDD.STES,DSD_KEI@DF_KEI",          # Key Economic Indicators
        "finmark":   "OECD.SDD.STES,DSD_STES@DF_FINMARK",     # Financial Markets

        # Prices (OECD.SDD.TPS)
        "cpi":       "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL",  # CPI (COICOP 1999)

        # Labour Force (OECD.SDD.TPS)
        "unemp_m":   "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M",   # Unemployment monthly

        # Productivity (OECD.SDD.TPS)
        "pdb":       "OECD.SDD.TPS,DSD_PDB@DF_PDB",           # Productivity database
    }

    # CLI measure codes (only BCICP and CCICP available for most countries)
    CLI_MEASURES = {
        "business_confidence": "BCICP",   # Composite business confidence (amplitude adj, 100=baseline)
        "consumer_confidence": "CCICP",   # Composite consumer confidence
    }

    # BTS measure codes (Business Tendency Surveys)
    # Dimension order: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION.TIME_HORIZ.METHODOLOGY
    BTS_MEASURES = {
        "order_books":       "OB",  # Assessment of order books
        "export_orders":     "XR",  # Export order books/demand
        "production":        "PR",  # Production tendency
        "employment":        "EM",  # Employment expectations
        "business_situation": "BU",  # Business situation
        "demand":            "OD",  # Order intentions/demand
        "finished_goods":    "FG",  # Finished goods stocks
        "selling_prices":    "SP",  # Selling prices
    }

    # BTS time horizons
    BTS_HORIZONS = {
        "tendency": "T",      # Tendency (default for most measures)
        "future":   "FT",     # Future tendency
        "current":  "C",      # Current situation
    }

    # Activity codes (ISIC/NACE sectors)
    ACTIVITIES = {
        "total":          "_T",
        "manufacturing":  "C",
        "construction":   "F",
        "retail":         "G47",
        "services":       "GTU",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "OpenClaw Economic Data Collector"
        })

    def _resolve_dataflow(self, dataset: str) -> str:
        """Resolve alias to full dataflow path"""
        return self.DATAFLOWS.get(dataset, dataset)

    def get_data_csv(
        self,
        dataset: str,
        key: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        last_n: Optional[int] = None
    ) -> Dict:
        """
        Fetch data using CSV format (simplest parsing)

        Args:
            dataset: Dataset alias or full dataflow path
            key: Dimension filter (dot-separated positions)
            start_period: Start period (YYYY-MM, YYYY-QN, or YYYY)
            end_period: End period
            last_n: Last N observations only

        Returns:
            Dict with parsed data
        """
        dataflow = self._resolve_dataflow(dataset)
        url = f"{self.BASE_URL}/data/{dataflow}/{key}"

        params = {
            "format": "csvfilewithlabels",
            "dimensionAtObservation": "AllDimensions"
        }

        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period
        if last_n:
            params["lastNObservations"] = last_n

        import time

        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=60)
                if response.status_code == 429:
                    # Rate limited — wait and retry
                    wait = 15 * (attempt + 1)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return self._parse_csv(response.text, dataset, url)

            except requests.exceptions.RequestException as e:
                if attempt < 2 and "429" in str(e):
                    time.sleep(15)
                    continue
                return {
                    "error": str(e),
                    "dataset": dataset,
                    "url": url
                }

        return {"error": "Rate limited after 3 retries", "dataset": dataset, "url": url}

    def _parse_csv(self, csv_text: str, dataset: str, url: str) -> Dict:
        """Parse CSV response into observations"""
        reader = csv.DictReader(io.StringIO(csv_text))
        observations = []

        for row in reader:
            period = row.get("TIME_PERIOD", "")
            value_str = row.get("OBS_VALUE", "")
            if not value_str or not period:
                continue
            try:
                value = float(value_str)
            except ValueError:
                continue

            obs = {
                "period": period,
                "value": value,
            }
            # Include useful label columns if present
            for col in ["Measure", "MEASURE", "Activity", "ACTIVITY",
                        "Unit of measure", "UNIT_MEASURE"]:
                if col in row and row[col]:
                    obs[col.lower().replace(" ", "_")] = row[col]

            observations.append(obs)

        # Sort by period
        observations.sort(key=lambda x: x["period"])

        return {
            "dataset": dataset,
            "count": len(observations),
            "data": observations,
            "source": "OECD",
            "url": url
        }

    # ==========================================
    # Helper: compute start period
    # ==========================================

    def _since(self, months: Optional[int] = None, years: Optional[int] = None,
               ref_date: Optional[datetime] = None) -> Optional[str]:
        """Compute start period from ref_date (default: now)"""
        anchor = ref_date or datetime.now()
        if months:
            dt = anchor - timedelta(days=months * 31)
            return dt.strftime("%Y-%m")
        elif years:
            return str(anchor.year - years)
        return None

    # ==========================================
    # Convenience: Composite Leading Indicators
    # ==========================================

    def get_cli(
        self,
        country: str = "PRT",
        measure: str = "business_confidence",
        months: int = 24,
        ref_date: Optional[datetime] = None
    ) -> Dict:
        """
        Composite Leading Indicators (OECD)

        > 100 = above long-term average, < 100 = below

        Args:
            country: ISO alpha-3 (PRT, ESP, DEU, FRA, etc.)
            measure: business_confidence, consumer_confidence
            months: Meses de histórico
            ref_date: Reference date for period calculation (default: now)
        """
        code = self.CLI_MEASURES.get(measure, measure)
        key = f"{country}.M.{code}.IX._Z.AA.IX._Z.H"
        end_period = ref_date.strftime("%Y-%m") if ref_date else None
        return self.get_data_csv("cli", key, start_period=self._since(months=months, ref_date=ref_date),
                                 end_period=end_period)

    def get_confidence_dashboard(
        self,
        country: str = "PRT",
        months: int = 24
    ) -> Dict[str, Dict]:
        """Business + consumer confidence"""
        return {
            "business": self.get_cli(country, "business_confidence", months),
            "consumer": self.get_cli(country, "consumer_confidence", months),
        }

    # ==========================================
    # Convenience: Business Tendency Surveys
    # ==========================================

    # Default horizon per BTS measure (based on data availability)
    BTS_DEFAULT_HORIZONS = {
        "production":        "T",   # Tendency
        "order_books":       "C",   # Current
        "export_orders":     "C",   # Current
        "employment":        "FT",  # Future tendency
        "business_situation": "C",  # Current
        "demand":            "FT",  # Future tendency
        "finished_goods":    "C",   # Current
        "selling_prices":    "FT",  # Future tendency
    }

    def get_bts(
        self,
        country: str = "PRT",
        measure: str = "production",
        activity: str = "manufacturing",
        horizon: Optional[str] = None,
        months: int = 24,
        ref_date: Optional[datetime] = None
    ) -> Dict:
        """
        Business Tendency Surveys (qualitative, % balance)

        Args:
            measure: order_books, export_orders, production, employment,
                     business_situation, demand, finished_goods, selling_prices
            activity: manufacturing, construction, retail, services, total
            horizon: T (tendency), FT (future), C (current) - auto-selected if None
        """
        code = self.BTS_MEASURES.get(measure, measure)
        act = self.ACTIVITIES.get(activity, activity)
        if horizon is None:
            hor = self.BTS_DEFAULT_HORIZONS.get(measure, "T")
        else:
            hor = self.BTS_HORIZONS.get(horizon, horizon)
        # Dims: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION.TIME_HORIZ.METHODOLOGY
        key = f"{country}.M.{code}.PB.{act}.Y._Z.{hor}.N"
        end_period = ref_date.strftime("%Y-%m") if ref_date else None
        return self.get_data_csv("bts", key, start_period=self._since(months=months, ref_date=ref_date),
                                 end_period=end_period)

    def get_bts_dashboard(
        self,
        country: str = "PRT",
        months: int = 13,
        ref_date: Optional[datetime] = None
    ) -> Dict[str, Dict]:
        """Dashboard de inquéritos de tendência empresarial (manufacturing)"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        # business_situation (BU) returns 404 for Portugal — excluded
        measures = ["order_books", "production", "employment", "selling_prices"]
        results = {}
        with ThreadPoolExecutor(max_workers=len(measures)) as executor:
            futures = {
                executor.submit(self.get_bts, country, m, "manufacturing", months=months, ref_date=ref_date): m
                for m in measures
            }
            for future in as_completed(futures):
                measure = futures[future]
                try:
                    results[measure] = future.result()
                except Exception as e:
                    results[measure] = {"error": str(e), "measure": measure}
        return results

    # ==========================================
    # Convenience: Unemployment
    # ==========================================

    def get_unemployment(
        self,
        country: str = "PRT",
        months: int = 24,
        age: str = "Y_GE15",
        sex: str = "_T",
        ref_date: Optional[datetime] = None
    ) -> Dict:
        """
        Taxa de desemprego mensal (% da pop. activa)

        Args:
            age: Y_GE15 (15+), Y15T24 (youth 15-24), Y_GE25 (25+)
            sex: _T (total), M (male), F (female)
        """
        # Dims: REF_AREA.MEASURE.UNIT_MEASURE.TRANSFORMATION.ADJUSTMENT.SEX.AGE.ACTIVITY.FREQ
        key = f"{country}.UNE_LF_M.PT_LF_SUB._Z.Y.{sex}.{age}._Z.M"
        end_period = ref_date.strftime("%Y-%m") if ref_date else None
        return self.get_data_csv("unemp_m", key, start_period=self._since(months=months, ref_date=ref_date),
                                 end_period=end_period)

    # ==========================================
    # Convenience: CPI / Inflation
    # ==========================================

    def get_cpi(
        self,
        country: str = "PRT",
        months: int = 24,
        methodology: str = "HICP"
    ) -> Dict:
        """
        Consumer Price Index (taxa crescimento anual, %)

        Args:
            methodology: N (national CPI), HICP (harmonised)
        """
        # Dims: REF_AREA.FREQ.METHODOLOGY.MEASURE.UNIT_MEASURE.EXPENDITURE.ADJUSTMENT.TRANSFORMATION
        key = f"{country}.M.{methodology}.CPI.PA._T.N.GY"
        return self.get_data_csv("cpi", key, start_period=self._since(months=months))

    # ==========================================
    # Convenience: Productivity
    # ==========================================

    def get_productivity(
        self,
        country: str = "PRT",
        years: int = 10
    ) -> Dict:
        """Labour productivity - GDP per hour worked (USD PPP, growth rate, annual)"""
        # Dims: REF_AREA.FREQ.MEASURE.ACTIVITY.UNIT_MEASURE.PRICE_BASE.TRANSFORMATION.ASSET_CODE.CONVERSION_TYPE
        key = f"{country}.A.T_GDPHRS._T.USD_PPP.V.GY._Z._Z"
        return self.get_data_csv("pdb", key, start_period=self._since(years=years))

    def get_ulc(
        self,
        country: str = "PRT",
        years: int = 10
    ) -> Dict:
        """Unit labour costs (annual, total economy, growth rate)"""
        # Same PDB dataflow, different measure
        key = f"{country}.A.ULCE._T.XDC.V.GY._Z._Z"
        return self.get_data_csv("pdb", key, start_period=self._since(years=years))

    # ==========================================
    # Multi-country comparison
    # ==========================================

    def compare_countries(
        self,
        countries: List[str],
        method: str = "cli",
        measure: str = "business_confidence",
        months: int = 24
    ) -> Dict[str, Dict]:
        """
        Compare countries on the same indicator

        Args:
            countries: List of ISO alpha-3 codes (e.g., ["PRT", "ESP", "DEU"])
            method: cli, unemployment, cpi, bts
            measure: indicator-specific measure name
        """
        results = {}
        for country in countries:
            if method == "cli":
                results[country] = self.get_cli(country, measure, months)
            elif method == "unemployment":
                results[country] = self.get_unemployment(country, months)
            elif method == "cpi":
                results[country] = self.get_cpi(country, months)
            elif method == "bts":
                results[country] = self.get_bts(country, measure, months=months)
        return results


# === Exemplos de Uso ===
if __name__ == "__main__":
    client = OECDClient()

    print("=== OECD Data Explorer - Teste Portugal ===\n")

    # 1. CLI Business Confidence
    print("1. Confiança Empresarial (últimos 6 meses):")
    bci = client.get_cli(months=6)
    if "data" in bci and bci["data"]:
        for obs in bci["data"]:
            print(f"  {obs['period']}: {obs['value']:.2f}")
    else:
        print(f"  {bci.get('error', 'no data')}")
    print()

    # 2. Desemprego
    print("2. Desemprego Portugal (últimos 12 meses):")
    unemp = client.get_unemployment(months=12)
    if "data" in unemp and unemp["data"]:
        for obs in unemp["data"]:
            print(f"  {obs['period']}: {obs['value']:.1f}%")
    else:
        print(f"  {unemp.get('error', 'no data')}")
    print()

    # 3. BTS Manufacturing
    print("3. Tendência Produção Industrial (BTS, últimos 6 meses):")
    bts = client.get_bts(measure="production", months=6)
    if "data" in bts and bts["data"]:
        for obs in bts["data"]:
            print(f"  {obs['period']}: {obs['value']:.1f}")
    else:
        print(f"  {bts.get('error', 'no data')}")
    print()

    # 4. Comparação países
    print("4. Confiança Empresarial - PT vs ES vs DE:")
    comp = client.compare_countries(["PRT", "ESP", "DEU"], months=3)
    for country, result in comp.items():
        if "data" in result and result["data"]:
            latest = result["data"][-1]
            print(f"  {country}: {latest['value']:.2f} ({latest['period']})")
