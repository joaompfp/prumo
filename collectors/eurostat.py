#!/usr/bin/env python3
"""
Eurostat API Client - Dados Estatísticos União Europeia
API Statistics v1.0 (JSON-stat) - Sem autenticação
Documentação: https://wikis.ec.europa.eu/display/EUROSTATHELP/API+Statistics+-+data+query
"""

import requests
from typing import Optional, Dict, List, Union
from datetime import datetime, timedelta


class EurostatClient:
    """Cliente para Eurostat Statistics API v1.0 (JSON-stat)"""

    BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0"

    # Datasets principais
    DATASETS = {
        # Macro
        "gdp": "nama_10_gdp",
        "inflation": "prc_hicp_midx",
        "unemployment": "une_rt_m",

        # Produção Industrial
        "ipi": "sts_inpr_m",

        # Comércio Internacional
        "trade_intra_eu": "ext_lt_intertrd",
        "trade_extra_eu": "ext_lt_maineu",
        "trade_by_sector": "ext_tec01",

        # Energia
        "energy_balance": "nrg_bal_s",
        "electricity_prices": "nrg_pc_204",

        # Confiança / Inquéritos
        "business_consumer_surveys": "ei_bsco_m",
    }

    # Códigos NACE para IPI (sts_inpr_m)
    NACE_CODES = {
        "total_industry": "B-D",
        "manufacturing": "C",
        "food_beverage": "C10-C12",
        "textiles": "C13-C15",
        "wood_paper": "C16-C18",
        "chemicals_pharma": "C20_C21",
        "rubber_plastics": "C22",
        "non_metallic": "C23",
        "metals": "C24_C25",
        "electronics": "C26-C27",
        "machinery": "C28",
        "transport_eq": "C29_C30",
    }

    # Indicadores de confiança (ei_bsco_m)
    CONFIDENCE_INDICATORS = {
        "consumer": "BS-CSMCI",
        "financial_past": "BS-FS-LY",
        "financial_next": "BS-FS-NY",
        "economy_past": "BS-GES-LY",
        "economy_next": "BS-GES-NY",
        "prices_past": "BS-PT-LY",
        "prices_next": "BS-PT-NY",
        "unemployment_next": "BS-UE-NY",
        "major_purchases": "BS-MP-PR",
        "savings_next": "BS-SV-NY",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "OpenClaw Economic Data Collector"
        })

    def _resolve_dataset(self, dataset: str) -> tuple:
        """Resolve dataset alias to code"""
        if dataset in self.DATASETS:
            return self.DATASETS[dataset], dataset
        return dataset, dataset

    def _compute_since(self, months: Optional[int] = None, years: Optional[int] = None,
                        ref_date: Optional[datetime] = None) -> Optional[str]:
        """Compute sinceTimePeriod from months or years back from ref_date"""
        anchor = ref_date or datetime.now()
        if months:
            dt = anchor - timedelta(days=months * 31)
            return dt.strftime("%Y-%m")
        elif years:
            return str(anchor.year - years)
        return None

    def get_data(
        self,
        dataset: str,
        geo: str = "PT",
        since: Optional[str] = None,
        until: Optional[str] = None,
        months: Optional[int] = None,
        years: Optional[int] = None,
        ref_date: Optional[datetime] = None,
        **dim_filters
    ) -> Dict:
        """
        Buscar dados de qualquer dataset Eurostat

        Args:
            dataset: Dataset code ou alias (ver DATASETS)
            geo: Código país ISO (PT, ES, DE, etc.)
            since: Período início (YYYY-MM para mensal, YYYY para anual)
            until: Período fim
            months: Alternativa a since - últimos N meses com dados
                    (requests wider window to handle publication delays)
            years: Alternativa a since - últimos N anos com dados
            **dim_filters: Filtros dimensionais como keyword args
                           (e.g., nace_r2="C", s_adj="SCA", unit="I15")

        Returns:
            Dict com dados processados

        Example:
            # IPI Manufacturing Portugal, últimos 24 meses, dessazonalizado
            client.get_data("ipi", nace_r2="C", s_adj="SCA", indic_bt="PRD",
                           unit="I15", freq="M", months=24)

            # GDP Portugal últimos 10 anos
            client.get_data("gdp", unit="CLV10_MEUR", na_item="B1GQ",
                           freq="A", years=10)
        """
        dataset_code, dataset_name = self._resolve_dataset(dataset)
        url = f"{self.BASE_URL}/data/{dataset_code}"
        trim_to = None

        # Construir parâmetros
        params = {"geo": geo}

        # Período temporal
        if since:
            params["sinceTimePeriod"] = since
        elif months or years:
            # Request wider window to handle datasets with publication
            # delays (e.g. IPI SCA lags ~2 years), then trim to last N
            trim_to = months or years
            # Use max(requested * 3, minimum floor) to handle short requests
            effective_months = max(months * 3, 60) if months else None
            effective_years = max(years * 3, 10) if years else None
            computed = self._compute_since(months=effective_months,
                                           years=effective_years,
                                           ref_date=ref_date)
            if computed:
                params["sinceTimePeriod"] = computed
            # When ref_date is set, cap the upper bound to avoid fetching future data
            if ref_date and not until:
                params["untilTimePeriod"] = ref_date.strftime("%Y-%m")
        if until:
            params["untilTimePeriod"] = until

        # Filtros dimensionais adicionais
        params.update(dim_filters)

        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()
            result = self._parse_jsonstat(data, dataset_name, dataset_code, url)

            # Trim to last N entries if months/years was used
            if trim_to and "data" in result and result["data"]:
                result["data"] = result["data"][-trim_to:]
                result["count"] = len(result["data"])

            return result

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "dataset": dataset_name,
                "url": url
            }
        except (KeyError, IndexError, ValueError) as e:
            return {
                "error": f"Parse error: {str(e)}",
                "dataset": dataset_name
            }

    def _parse_jsonstat(self, data: Dict, dataset_name: str, dataset_code: str, url: str) -> Dict:
        """Parse JSON-stat response format"""
        values = data.get("value", {})
        dimensions = data.get("dimension", {})
        dim_ids = data.get("id", [])
        dim_sizes = data.get("size", [])

        # Encontrar dimensão temporal
        time_dim = dimensions.get("time", {}).get("category", {})
        time_index = time_dim.get("index", {})
        time_labels = time_dim.get("label", {})

        # Mapear posições para períodos
        # Para datasets com uma única série (todos filtros = 1 valor),
        # o index é linear e mapeia directamente para tempo
        time_dim_pos = dim_ids.index("time") if "time" in dim_ids else -1

        if time_dim_pos < 0:
            return {
                "error": "No time dimension found",
                "dataset": dataset_name
            }

        # Calcular stride para a dimensão temporal
        stride = 1
        for i in range(time_dim_pos + 1, len(dim_sizes)):
            stride *= dim_sizes[i]

        # Calcular quantos elementos antes da dim temporal
        pre_count = 1
        for i in range(0, time_dim_pos):
            pre_count *= dim_sizes[i]

        # Mapear index → período → valor
        sorted_times = sorted(time_index.items(), key=lambda x: x[1])
        observations = []

        for period_id, period_pos in sorted_times:
            # Calcular flat index para este período
            # Para single-series (pre_count=1, stride=1): idx = period_pos
            idx = period_pos * stride
            val = values.get(str(idx))
            if val is not None:
                observations.append({
                    "period": period_id,
                    "period_sort": period_id,
                    "value": float(val)
                })

        # Se multi-série e stride > 1, precisamos iterar diferente
        if pre_count > 1 or stride > 1:
            # Re-extrair com abordagem completa
            observations = []
            n_time = len(sorted_times)
            for period_id, period_pos in sorted_times:
                # Recolher todos os valores para este período
                for pre in range(pre_count):
                    flat_idx = pre * n_time * stride + period_pos * stride
                    for post in range(stride):
                        val = values.get(str(flat_idx + post))
                        if val is not None:
                            observations.append({
                                "period": period_id,
                                "value": float(val)
                            })

        return {
            "dataset": dataset_name,
            "dataset_code": dataset_code,
            "count": len(observations),
            "data": observations,
            "source": "Eurostat",
            "url": url
        }

    # ==========================================
    # Convenience methods - Produção Industrial
    # ==========================================

    def get_ipi_portugal(
        self,
        nace_code: str = "C",
        months: int = 13,
        adjusted: str = "SCA",
        geo: str = "PT",
        ref_date: Optional[datetime] = None
    ) -> Dict:
        """
        Índice Produção Industrial

        Args:
            nace_code: Código NACE ou alias (ver NACE_CODES)
            months: Meses de histórico
            adjusted: Ajuste sazonal (SCA=sazonal+calendário, NSA=bruto, CA=calendário)
            geo: País (PT default)
        """
        if nace_code in self.NACE_CODES:
            nace = self.NACE_CODES[nace_code]
        else:
            nace = nace_code

        return self.get_data(
            "ipi", geo=geo, months=months, ref_date=ref_date,
            freq="M", indic_bt="PRD", nace_r2=nace,
            s_adj=adjusted, unit="I15"
        )

    def get_industrial_dashboard(self, months: int = 13, geo: str = "PT",
                                 ref_date: Optional[datetime] = None) -> Dict[str, Dict]:
        """Dashboard IPI por sector — parallel fetch"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        sectors = ["total_industry", "manufacturing", "metals", "machinery",
                   "chemicals_pharma", "rubber_plastics", "electronics", "transport_eq"]
        results = {}
        with ThreadPoolExecutor(max_workers=len(sectors)) as executor:
            futures = {
                executor.submit(self.get_ipi_portugal, nace_code=s, months=months, geo=geo, ref_date=ref_date): s
                for s in sectors
            }
            for future in as_completed(futures):
                sector = futures[future]
                try:
                    results[sector] = future.result()
                except Exception as e:
                    results[sector] = {"error": str(e), "sector": sector}
        return results

    # ==========================================
    # Convenience methods - Macro
    # ==========================================

    def get_gdp_portugal(self, years: int = 5, geo: str = "PT") -> Dict:
        """PIB (preços constantes 2010, milhões EUR)"""
        return self.get_data(
            "gdp", geo=geo, years=years,
            freq="A", unit="CLV10_MEUR", na_item="B1GQ"
        )

    def get_hicp_portugal(self, months: int = 13, geo: str = "PT",
                          ref_date: Optional[datetime] = None) -> Dict:
        """HICP - Índice Harmonizado de Preços no Consumidor (2015=100)"""
        return self.get_data(
            "inflation", geo=geo, months=months, ref_date=ref_date,
            freq="M", coicop="CP00", unit="I15"
        )

    def get_unemployment_portugal(self, months: int = 13, geo: str = "PT",
                                  ref_date: Optional[datetime] = None) -> Dict:
        """Taxa de desemprego (%, dessazonalizada, total, todas idades)"""
        return self.get_data(
            "unemployment", geo=geo, months=months, ref_date=ref_date,
            freq="M", s_adj="SA", age="TOTAL",
            unit="PC_ACT", sex="T"
        )

    # ==========================================
    # Convenience methods - Confiança
    # ==========================================

    def get_consumer_confidence(self, months: int = 13, geo: str = "PT") -> Dict:
        """Indicador de confiança do consumidor"""
        return self.get_data(
            "business_consumer_surveys", geo=geo, months=months,
            freq="M", indic="BS-CSMCI", s_adj="SA", unit="BAL"
        )

    def get_confidence_dashboard(self, months: int = 13, geo: str = "PT") -> Dict[str, Dict]:
        """Dashboard de todos os indicadores de confiança"""
        results = {}
        for name, code in self.CONFIDENCE_INDICATORS.items():
            results[name] = self.get_data(
                "business_consumer_surveys", geo=geo, months=months,
                freq="M", indic=code, s_adj="SA", unit="BAL"
            )
        return results

    # ==========================================
    # Convenience methods - Comércio
    # ==========================================

    def get_trade_intra_eu(self, years: int = 5, geo: str = "PT") -> Dict:
        """Comércio intra-EU (exportações + importações, milhões EUR, total SITC)"""
        return self.get_data(
            "trade_intra_eu", geo=geo, years=years,
            freq="A", sitc06="TOTAL", partner="EU27_2020"
        )

    def get_trade_extra_eu(self, years: int = 5, geo: str = "PT") -> Dict:
        """Comércio extra-EU (exportações + importações, milhões EUR, total)"""
        return self.get_data(
            "trade_extra_eu", geo=geo, years=years,
            freq="A", sitc06="TOTAL", partner="EXT_EU27_2020"
        )

    # ==========================================
    # Convenience methods - Energia
    # ==========================================

    def get_energy_balance(self, years: int = 5, geo: str = "PT") -> Dict:
        """Balanço energético (produção primária, total, TJ)"""
        return self.get_data(
            "energy_balance", geo=geo, years=years,
            freq="A", nrg_bal="PPRD", siec="TOTAL", unit="TJ"
        )

    def get_electricity_prices(self, geo: str = "PT") -> Dict:
        """Preços electricidade para consumidores domésticos"""
        return self.get_data(
            "electricity_prices", geo=geo, years=3,
            freq="S", siec="E7000", unit="KWH",
            tax="I_TAX", currency="EUR",
            nrg_cons="TOT_KWH"
        )

    # ==========================================
    # Multi-country comparison
    # ==========================================

    def compare_countries(
        self,
        dataset: str,
        countries: List[str],
        months: Optional[int] = None,
        years: Optional[int] = None,
        **dim_filters
    ) -> Dict[str, Dict]:
        """
        Comparar múltiplos países para o mesmo indicador

        Args:
            dataset: Dataset ou alias
            countries: Lista de códigos ISO (e.g., ["PT", "ES", "DE", "FR"])
            months/years: Período
            **dim_filters: Filtros dimensionais

        Returns:
            Dict com chave = país, valor = resultado
        """
        results = {}
        for country in countries:
            results[country] = self.get_data(
                dataset, geo=country, months=months, years=years,
                **dim_filters
            )
        return results


# === Exemplos de Uso ===
if __name__ == "__main__":
    client = EurostatClient()

    print("=== Eurostat API v3 - Teste Portugal ===\n")

    # 1. PIB
    print("1. PIB Portugal (últimos 5 anos):")
    gdp = client.get_gdp_portugal(years=5)
    if "data" in gdp and gdp["data"]:
        for obs in gdp["data"]:
            print(f"  {obs['period']}: {obs['value']:,.0f} M€")
    print()

    # 2. HICP
    print("2. HICP Portugal (últimos 6 meses):")
    hicp = client.get_hicp_portugal(months=6)
    if "data" in hicp and hicp["data"]:
        for obs in hicp["data"]:
            print(f"  {obs['period']}: {obs['value']:.2f}")
    print()

    # 3. Desemprego
    print("3. Desemprego Portugal (últimos 12 meses):")
    unemp = client.get_unemployment_portugal(months=12)
    if "data" in unemp and unemp["data"]:
        for obs in unemp["data"]:
            print(f"  {obs['period']}: {obs['value']:.1f}%")
    print()

    # 4. IPI Manufacturing
    print("4. IPI Manufacturing (últimos 6 meses):")
    ipi = client.get_ipi_portugal(nace_code="manufacturing", months=6)
    if "data" in ipi and ipi["data"]:
        for obs in ipi["data"]:
            print(f"  {obs['period']}: {obs['value']:.1f}")
    print()

    # 5. Dashboard IPI
    print("5. Dashboard Industrial:")
    dashboard = client.get_industrial_dashboard(months=3)
    for sector, result in dashboard.items():
        if "data" in result and result["data"]:
            latest = result["data"][-1]
            print(f"  {sector}: {latest['value']:.1f} ({latest['period']})")
    print()

    # 6. Confiança consumidor
    print("6. Confiança Consumidor (últimos 6 meses):")
    conf = client.get_consumer_confidence(months=6)
    if "data" in conf and conf["data"]:
        for obs in conf["data"]:
            print(f"  {obs['period']}: {obs['value']:.1f}")
