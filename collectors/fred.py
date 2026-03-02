#!/usr/bin/env python3
"""
FRED API Client - Federal Reserve Economic Data
Requer API key (grátis): https://fred.stlouisfed.org/docs/api/api_key.html
Documentação: https://fred.stlouisfed.org/docs/api/fred/
"""

import requests
import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta

class FREDClient:
    """Cliente para FRED (Federal Reserve Economic Data)"""

    BASE_URL = "https://api.stlouisfed.org/fred"

    # Séries de Commodities
    COMMODITIES = {
        # Energia
        "brent_oil": "POILBREUSDM",           # Global price of Brent Crude (monthly avg)
        "brent_oil_daily": "DCOILBRENTEU",    # Crude Oil Prices: Brent - Europe (daily)
        "wti_oil": "DCOILWTICO",              # West Texas Intermediate (daily)
        "natural_gas": "MHHNGSP",             # Henry Hub Natural Gas Spot Price
        "coal": "PCOALAUUSDM",                # Global price of Coal, Australia

        # Metais
        "copper": "PCOPPUSDM",                # Global price of Copper
        "aluminum": "PALUMUSDM",              # Global price of Aluminum
        "iron_ore": "PIORECRUSDM",            # Global price of Iron Ore
        "steel": "WPU101",                      # PPI Iron and Steel (US, monthly)
        "zinc": "PZINCUSDM",                  # Global price of Zinc
        "nickel": "PNICKUSDM",                # Global price of Nickel

        # Agrícolas
        "wheat": "PWHEAMTUSDM",               # Global price of Wheat
        "corn": "PMAIZMTUSDM",                # Global price of Corn (Maize)
        "soybean": "PSOYBUSDM",               # Global price of Soybeans
        "coffee": "PCOFFOTMUSDM",             # Global price of Coffee, Other Mild Arabica
        "sugar": "PSUGAISAUSDM",              # Global price of Sugar
        "cotton": "PCOTTINDUSDM",             # Global price of Cotton

        # Metais preciosos
        "gold_price": "GOLDAMGBD228NLBM",     # Gold Fixing Price (LBMA), USD/troy oz
        "silver_price": "SLVPRUSD",           # Silver Price, USD/troy oz

        # Forex (contexto exportações)
        "eur_usd": "DEXUSEU",                 # U.S. / Euro Foreign Exchange Rate
    }

    # Índices compostos
    INDICES = {
        "commodity_index": "PPIACO",          # Producer Price Index: All Commodities
        "energy_index": "PPIENG",             # PPI: Fuels and Related Products
        "metals_index": "PPIIDC",             # PPI: Industrial Commodities
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: FRED API key (ou via env FRED_API_KEY)
        """
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        if not self.api_key:
            # Fallback: read from config file (supports bind-mounted workspace on f3nix)
            import pathlib
            _cfg = pathlib.Path(__file__).parent.parent / ".fred_api_key"
            if _cfg.exists():
                self.api_key = _cfg.read_text().strip()
        if not self.api_key:
            raise ValueError(
                "FRED API key necessária. Obtenha em: "
                "https://fred.stlouisfed.org/docs/api/api_key.html\n"
                "Depois: export FRED_API_KEY='sua_chave' ou passe no construtor"
            )

        self.session = requests.Session()

    def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: Optional[str] = None
    ) -> Dict:
        """
        Buscar série temporal

        Args:
            series_id: ID da série FRED ou nome do dict COMMODITIES/INDICES
            start_date: Data início (YYYY-MM-DD)
            end_date: Data fim (YYYY-MM-DD)
            frequency: Frequência (d=diária, m=mensal, q=trimestral, a=anual)

        Returns:
            Dict com observações
        """
        # Resolver series_id se for alias
        if series_id in self.COMMODITIES:
            fred_id = self.COMMODITIES[series_id]
            series_name = series_id
        elif series_id in self.INDICES:
            fred_id = self.INDICES[series_id]
            series_name = series_id
        else:
            fred_id = series_id
            series_name = series_id

        url = f"{self.BASE_URL}/series/observations"

        params = {
            "series_id": fred_id,
            "api_key": self.api_key,
            "file_type": "json"
        }

        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date
        if frequency:
            params["frequency"] = frequency

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Processar observações
            observations = []
            for obs in data.get("observations", []):
                if obs["value"] != ".":  # FRED usa "." para missing values
                    observations.append({
                        "date": obs["date"],
                        "value": float(obs["value"]),
                        "series_id": fred_id
                    })

            return {
                "series": series_name,
                "series_id": fred_id,
                "count": len(observations),
                "data": observations,
                "source": "FRED",
                "url": f"https://fred.stlouisfed.org/series/{fred_id}"
            }

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "series": series_name
            }

    def get_latest(self, series_id: str, n: int = 1) -> Optional[List[Dict]]:
        """Obter últimas N observações"""
        # Buscar últimos 30 dias para garantir
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        result = self.get_series(series_id, start_date=start_date, end_date=end_date)

        if "error" in result or not result.get("data"):
            return None

        # Retornar últimas N observações
        return result["data"][-n:]

    def get_multiple(self, series_ids: List[str], start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> Dict[str, Dict]:
        """Buscar múltiplas séries de uma vez"""
        results = {}
        for sid in series_ids:
            results[sid] = self.get_series(sid, start_date=start_date, end_date=end_date)
        return results

    def get_commodity_dashboard(self, months: int = 12,
                               ref_date: Optional[datetime] = None) -> Dict[str, Dict]:
        """
        Dashboard de commodities principais

        Args:
            months: Quantos meses de histórico
            ref_date: Reference date for period calculation (default: now)

        Returns:
            Dict com commodities principais
        """
        anchor = ref_date or datetime.now()
        start_date = (anchor - timedelta(days=months*30)).strftime("%Y-%m-%d")
        end_date = anchor.strftime("%Y-%m-%d") if ref_date else None

        key_commodities = [
            "brent_oil", "natural_gas", "copper", "aluminum",
            "wheat", "corn", "coffee"
        ]

        return self.get_multiple(key_commodities, start_date=start_date,
                                 end_date=end_date)


# === Exemplos de Uso ===
if __name__ == "__main__":
    # Nota: Precisa de FRED_API_KEY no environment
    try:
        client = FREDClient()

        print("=== FRED API - Teste Commodities ===\n")

        # Exemplo 1: Preço atual Brent
        print("1. Preço atual Brent Oil:")
        brent = client.get_latest("brent_oil", n=5)
        if brent:
            for obs in brent:
                print(f"  {obs['date']}: ${obs['value']:.2f}/barrel")
        print()

        # Exemplo 2: Dashboard commodities
        print("2. Dashboard Commodities (últimos 3 meses):")
        dashboard = client.get_commodity_dashboard(months=3)
        for commodity, result in dashboard.items():
            if "data" in result and result["data"]:
                latest = result["data"][-1]
                print(f"  {commodity}: ${latest['value']:.2f} ({latest['date']})")

    except ValueError as e:
        print(f"Erro: {e}")
        print("\nPara obter API key:")
        print("1. Aceda https://fred.stlouisfed.org/docs/api/api_key.html")
        print("2. Registe-se (grátis)")
        print("3. Depois: export FRED_API_KEY='sua_chave'")
