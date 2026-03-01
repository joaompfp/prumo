#!/usr/bin/env python3
"""
DGEG Real-Time Fuel Prices API Client
Portal: https://precoscombustiveis.dgeg.gov.pt
API: https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb/

Public REST API, no authentication needed.

Endpoints:
- GetTiposCombustiveis: List all fuel types with IDs
- GetDistritos: List all districts with IDs
- GetMunicipios: List municipalities for a district
- PesquisarPostos: Search fuel stations with prices

Known limitations:
- PMD (average prices) endpoint returns empty ("Nenhum preço encontrado")
- PesquisarPostos fuel type filter (IdTipoComb) is BROKEN — always returns GPL Auto
  regardless of the fuel ID passed. This is a backend bug in the DGEG API.
- Workaround: use the station search without fuel type filtering and aggregate
  by Combustivel field client-side, or use the weekly Excel data from DGEG
  (fuel_prices_weekly in energy-data.db) for historical prices.

Key fuel type IDs:
  2101: Gasóleo simples (diesel)
  2105: Gasóleo especial (premium diesel)
  3201: Gasolina simples 95
  3205: Gasolina especial 95
  3400: Gasolina 98
  1120: GPL Auto (LPG)
"""

import requests
from typing import Optional, Dict, List, Any


# Fuel type constants
FUEL_DIESEL = 2101
FUEL_DIESEL_PREMIUM = 2105
FUEL_GASOLINE_95 = 3201
FUEL_GASOLINE_95_PREMIUM = 3205
FUEL_GASOLINE_98 = 3400
FUEL_GPL = 1120


class DGEGFuelPricesClient:
    """Client for DGEG fuel prices REST API."""

    BASE_URL = "https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the API."""
        url = f"{self.BASE_URL}/{endpoint}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("status", False):
            return {
                "source": "DGEG-API",
                "error": data.get("mensagem", "Unknown error"),
                "data": [],
            }
        return {
            "source": "DGEG-API",
            "count": len(data.get("resultado", []) or []),
            "data": data.get("resultado", []) or [],
        }

    def get_fuel_types(self) -> Dict[str, Any]:
        """List all available fuel types with IDs.

        Returns: List of {Descritivo, UnidadeMedida, fl_rodoviario, Id}
        """
        result = self._get("GetTiposCombustiveis")
        # Enrich with standard names
        NAME_MAP = {
            2101: "diesel", 2105: "diesel_premium", 2115: "biodiesel_b15",
            2150: "diesel_colorido", 2155: "diesel_aquecimento",
            3201: "gasoline_95", 3205: "gasoline_95_premium",
            3400: "gasoline_98", 3405: "gasoline_98_premium",
            3210: "gasoline_2stroke", 1120: "gpl_auto",
            1141: "gnc_m3", 1142: "gnl_kg", 1143: "gnc_kg",
        }
        for item in result["data"]:
            item["standard_name"] = NAME_MAP.get(item.get("Id"), "unknown")
        return result

    def get_districts(self) -> Dict[str, Any]:
        """List all districts with IDs.

        Returns: List of {Descritivo, Id}
        """
        return self._get("GetDistritos")

    def get_municipalities(self, district_id: int) -> Dict[str, Any]:
        """List municipalities for a district.

        Args:
            district_id: District ID (from get_districts())

        Returns: List of {Descritivo, Id}
        """
        return self._get("GetMunicipios", params={"IdDistrito": district_id})

    def search_stations(self, fuel_type_id: int = FUEL_DIESEL,
                          district_id: Optional[int] = None,
                          municipality_id: Optional[int] = None,
                          sort: int = 1,
                          limit: int = 50) -> Dict[str, Any]:
        """Search fuel stations with current prices.

        NOTE: The fuel type filter (IdTipoComb) is currently broken in the DGEG API.
        All results return GPL Auto regardless of the fuel type ID passed.
        Use the Combustivel field in results to identify the actual fuel type.

        Args:
            fuel_type_id: Fuel type ID (default: diesel 2101)
            district_id: Filter by district
            municipality_id: Filter by municipality
            sort: Sort order (1=cheapest first)
            limit: Max stations (API returns up to 50)

        Returns: List of stations with {Id, Nome, TipoPosto, Municipio, Preco,
                 Marca, Combustivel, DataAtualizacao, Distrito, Morada,
                 Localidade, CodPostal, Latitude, Longitude}
        """
        params = {
            "IdTipoComb": fuel_type_id,
            "Ordenacao": sort,
            "Quantidade": min(limit, 50),
        }
        if district_id:
            params["IdDistrito"] = district_id
        if municipality_id:
            params["IdMunicipio"] = municipality_id

        result = self._get("PesquisarPostos", params=params)

        # Parse price strings like "0,799 €" to floats
        for station in result["data"]:
            price_str = station.get("Preco", "")
            try:
                station["price_eur"] = float(price_str.replace("€", "").replace(",", ".").strip())
            except (ValueError, AttributeError):
                station["price_eur"] = None

        return result

    def get_cheapest_stations(self, district_id: Optional[int] = None,
                                limit: int = 10) -> Dict[str, Any]:
        """Get cheapest fuel stations (sorted by price).

        NOTE: Due to DGEG API bug, only GPL Auto prices are returned.

        Args:
            district_id: Filter by district (None = all Portugal)
            limit: Max stations
        """
        return self.search_stations(district_id=district_id, sort=1, limit=limit)

    def get_district_id(self, name: str) -> Optional[int]:
        """Look up district ID by name (case-insensitive partial match)."""
        districts = self.get_districts()
        name_lower = name.lower()
        for d in districts["data"]:
            if name_lower in d.get("Descritivo", "").lower():
                return d["Id"]
        return None


if __name__ == "__main__":
    import json
    client = DGEGFuelPricesClient()

    print("=== Fuel Types ===")
    data = client.get_fuel_types()
    for ft in data["data"]:
        road = "road" if ft.get("fl_rodoviario") else "    "
        print(f"  ID={ft['Id']:4d}: {ft['Descritivo']:45s} [{road}] ({ft['standard_name']})")

    print("\n=== Districts ===")
    data = client.get_districts()
    for d in data["data"]:
        print(f"  ID={d['Id']:2d}: {d['Descritivo']}")

    print("\n=== Municipalities (Lisboa district) ===")
    lisboa_id = client.get_district_id("Lisboa")
    if lisboa_id:
        data = client.get_municipalities(lisboa_id)
        for m in data["data"][:10]:
            print(f"  ID={m['Id']:3d}: {m['Descritivo']}")

    print("\n=== Cheapest stations (Lisboa) ===")
    data = client.search_stations(district_id=lisboa_id, limit=5)
    for s in data["data"][:5]:
        print(f"  {s['Nome'][:40]:42s} {s['Preco']:>10s} ({s['Combustivel']}) - {s['Marca']}")

    print(f"\nNOTE: Fuel type filter is broken — API always returns GPL Auto.")
