#!/usr/bin/env python3
"""
World Bank API Client - Indicadores Económicos
API V2 - Sem autenticação necessária
Documentação: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

import requests
from typing import Optional, Dict, List
from datetime import datetime

class WorldBankClient:
    """Cliente para World Bank Indicators API v2"""

    BASE_URL = "https://api.worldbank.org/v2"

    # Indicadores principais para Portugal
    INDICATORS = {
        # Macro
        "gdp": "NY.GDP.MKTP.CD",              # GDP (current US$)
        "gdp_growth": "NY.GDP.MKTP.KD.ZG",     # GDP growth (annual %)
        "gdp_per_capita": "NY.GDP.PCAP.CD",           # GDP per capita (current US$)
        "gdp_per_capita_ppp": "NY.GDP.PCAP.PP.CD",  # GDP per capita, PPP (constant 2017 intl $)
        "inflation": "FP.CPI.TOTL.ZG",         # Inflation, consumer prices (annual %)
        "unemployment": "SL.UEM.TOTL.ZS",      # Unemployment, total (% of total labor force)

        # Comércio
        "exports": "NE.EXP.GNFS.CD",           # Exports of goods and services (current US$)
        "imports": "NE.IMP.GNFS.CD",           # Imports of goods and services
        "trade_balance": "NE.RSB.GNFS.CD",     # External balance on goods and services

        # População & Emprego
        "population": "SP.POP.TOTL",           # Population, total
        "labor_force": "SL.TLF.TOTL.IN",       # Labor force, total

        # Energia
        "energy_use": "EG.USE.PCAP.KG.OE",     # Energy use (kg of oil equivalent per capita)
        "electricity": "EG.USE.ELEC.KH.PC",    # Electric power consumption (kWh per capita)
    }

    def __init__(self, language: str = "en"):
        """
        Args:
            language: Idioma resposta (en, pt, es, etc.)
        """
        self.language = language
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "OpenClaw Economic Data Collector"
        })

    def get_indicator(
        self,
        country: str,
        indicator: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        per_page: int = 1000,
        ref_date: Optional[datetime] = None
    ) -> Dict:
        """
        Buscar indicador para um país

        Args:
            country: Código país ISO (PT para Portugal, BR para Brasil, etc.)
            indicator: Código indicador ou nome do dict INDICATORS
            start_year: Ano início (opcional)
            end_year: Ano fim (opcional)
            per_page: Resultados por página (max 32500)

        Returns:
            Dict com metadata e dados
        """
        # Resolver indicator se for alias
        if indicator in self.INDICATORS:
            indicator_code = self.INDICATORS[indicator]
            indicator_name = indicator
        else:
            indicator_code = indicator
            indicator_name = indicator

        # Construir URL
        url = f"{self.BASE_URL}/country/{country.lower()}/indicator/{indicator_code}"

        params = {
            "format": "json",
            "per_page": per_page,
        }

        # Filtro temporal
        anchor_year = ref_date.year if ref_date else datetime.now().year
        if start_year and end_year:
            params["date"] = f"{start_year}:{end_year}"
        elif start_year:
            params["date"] = f"{start_year}:{anchor_year}"

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # World Bank API retorna array com 2 elementos: [metadata, data]
            if len(data) < 2:
                return {"error": "No data returned", "indicator": indicator_name}

            metadata, values = data[0], data[1]

            # Processar valores
            processed = []
            for item in values:
                if item.get("value") is not None:
                    processed.append({
                        "year": int(item["date"]),
                        "value": float(item["value"]),
                        "country": item["country"]["value"],
                        "indicator": item["indicator"]["value"]
                    })

            # Ordenar por ano
            processed.sort(key=lambda x: x["year"])

            return {
                "indicator": indicator_name,
                "indicator_code": indicator_code,
                "country": country.upper(),
                "total_results": metadata.get("total", 0),
                "data": processed,
                "source": "World Bank",
                "url": url
            }

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "indicator": indicator_name,
                "country": country
            }

    def get_latest(self, country: str, indicator: str) -> Optional[Dict]:
        """Obter último valor disponível de um indicador"""
        result = self.get_indicator(country, indicator, per_page=10)

        if "error" in result or not result.get("data"):
            return None

        # Último valor (mais recente)
        latest = result["data"][-1]
        return latest

    def get_multiple(self, country: str, indicators: List[str],
                     start_year: Optional[int] = None,
                     ref_date: Optional[datetime] = None) -> Dict[str, Dict]:
        """
        Buscar múltiplos indicadores de uma vez

        Returns:
            Dict com chave = nome indicador, valor = resultado
        """
        results = {}
        for ind in indicators:
            results[ind] = self.get_indicator(country, ind, start_year=start_year,
                                              ref_date=ref_date)
        return results


# === Exemplos de Uso ===
if __name__ == "__main__":
    client = WorldBankClient()

    print("=== World Bank API - Teste Portugal ===\n")

    # Exemplo 1: GDP recente
    print("1. GDP Portugal (últimos 5 anos):")
    gdp = client.get_indicator("PT", "gdp", start_year=2019)
    if "data" in gdp and gdp["data"]:
        for item in gdp["data"][-5:]:
            print(f"  {item['year']}: ${item['value']:,.0f}")
    print()

    # Exemplo 2: Último valor de inflação
    print("2. Última taxa de inflação:")
    inflation = client.get_latest("PT", "inflation")
    if inflation:
        print(f"  {inflation['year']}: {inflation['value']:.2f}%")
    print()

    # Exemplo 3: Múltiplos indicadores
    print("3. Dashboard económico Portugal (2024):")
    dashboard = client.get_multiple("PT", ["gdp_growth", "inflation", "unemployment"], start_year=2024)
    for ind_name, result in dashboard.items():
        if "data" in result and result["data"]:
            latest = result["data"][-1]
            print(f"  {ind_name}: {latest['value']:.2f} ({latest['year']})")
