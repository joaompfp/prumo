#!/usr/bin/env python3
"""
REN DataHub API Client — Portuguese Electricity Grid (Transmission)
API pública, sem autenticação — JSON
Docs: https://datahub.ren.pt/pt/instrucoes-api/

Complementa E-REDES (distribuição): REN = rede transporte nacional.
Inclui balanço mensal, produção por fonte, e preços OMIE (MIBEL).
"""

import requests
from typing import Optional, Dict
from datetime import datetime
from dateutil.relativedelta import relativedelta


class RENClient:
    """Cliente para REN DataHub API"""

    BASE_URL = "https://servicebus.ren.pt/datahubapi/electricity"

    # Types of interest from the monthly balance
    BALANCE_TYPES = {
        "CONSUMO": "consumption",
        "PRODUCAO_TOTAL": "production_total",
        "PRODUCAO_RENOVAVEL": "production_renewable",
        "PRODUCAO_NAO_RENOVAVEL": "production_non_renewable",
        "HIDRICA": "hydro",
        "EOLICA": "wind",
        "SOLAR": "solar",
        "BIOMASSA": "biomass",
        "GAS_NATURAL": "natural_gas",
        "GAS_NATURAL_CICLO_COMBINADO": "natural_gas_ccgt",
        "IMPORTACAO": "imports",
        "EXPORTACAO": "exports",
        "SALDO_IMPORTADOR": "net_imports",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "cae-reports/1.0",
        })

    def get_monthly_balance(self, months: int = 13,
                            ref_date: Optional[datetime] = None) -> Dict:
        """Monthly electricity balance: production by source, consumption, trade.

        Returns one observation per (period, type) pair, where type is one of
        the BALANCE_TYPES (consumption, hydro, wind, solar, etc.).
        """
        anchor = ref_date or datetime.now()
        all_data = []
        errors = []

        for i in range(months):
            dt = anchor - relativedelta(months=i)
            url = f"{self.BASE_URL}/ElectricityConsumptionSupplyMonthly"
            params = {
                "culture": "pt-PT",
                "year": str(dt.year),
                "month": f"{dt.month:02d}",
            }

            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                rows = resp.json()

                period = dt.strftime("%Y-%m")
                for row in rows:
                    rtype = row.get("type", "")
                    if rtype in self.BALANCE_TYPES:
                        val = row.get("monthly_Accumulation")
                        if val is not None:
                            all_data.append({
                                "period": period,
                                "type": self.BALANCE_TYPES[rtype],
                                "type_raw": rtype,
                                "value": float(val),
                                "unit": "GWh",
                            })

            except requests.exceptions.RequestException as e:
                errors.append(f"{dt.strftime('%Y-%m')}: {e}")

        # Pivot into per-type series
        from collections import defaultdict
        by_type = defaultdict(list)
        for obs in all_data:
            by_type[obs["type"]].append(obs)

        # Sort each series chronologically
        for typ in by_type:
            by_type[typ].sort(key=lambda x: x["period"])

        result = {}
        for typ, obs_list in by_type.items():
            result[typ] = {
                "indicator": f"electricity_{typ}",
                "count": len(obs_list),
                "data": obs_list,
                "unit": "GWh",
                "source": "REN DataHub",
                "url": "https://datahub.ren.pt/pt/eletricidade/balanco-mensal",
            }

        if errors:
            result["_errors"] = errors

        return result

    def get_market_prices(self, months: int = 13,
                          ref_date: Optional[datetime] = None) -> Dict:
        """Monthly average electricity market price (OMIE/MIBEL) for Portugal.

        This is the wholesale price — the precursor to ERSE retail tariffs.
        """
        anchor = ref_date or datetime.now()
        obs = []
        errors = []

        for i in range(months):
            dt = anchor - relativedelta(months=i)
            url = f"{self.BASE_URL}/ElectricityMarketPricesMonthly"
            params = {
                "culture": "pt-PT",
                "year": str(dt.year),
                "month": f"{dt.month:02d}",
            }

            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                raw = resp.json()

                # Response is nested: {month_name: {"PT.Preco Medio": value, ...}}
                period = dt.strftime("%Y-%m")
                pt_price = None
                es_price = None

                if isinstance(raw, dict):
                    for month_key, data in raw.items():
                        if isinstance(data, dict):
                            # PT prices nested under "PT" sub-dict
                            pt_data = data.get("PT", {})
                            if isinstance(pt_data, dict):
                                pt_price = pt_data.get("Preço Médio") or pt_data.get("Preco Medio")
                            else:
                                pt_price = data.get("PT.Preco Medio") or data.get("PT.Preço Médio")
                            es_data = data.get("ES", {})
                            if isinstance(es_data, dict):
                                es_price = es_data.get("Preço Médio") or es_data.get("Preco Medio")
                            else:
                                es_price = data.get("ES.Preco Medio") or data.get("ES.Preço Médio")
                            break

                if pt_price is not None:
                    obs.append({
                        "period": period,
                        "value": float(pt_price),
                        "value_es": float(es_price) if es_price else None,
                        "unit": "EUR/MWh",
                    })

            except requests.exceptions.RequestException as e:
                errors.append(f"{dt.strftime('%Y-%m')}: {e}")

        obs.sort(key=lambda x: x["period"])

        result = {
            "indicator": "electricity_price_mibel",
            "count": len(obs),
            "data": obs,
            "unit": "EUR/MWh",
            "source": "REN DataHub (OMIE/MIBEL)",
            "url": "https://datahub.ren.pt/pt/eletricidade/mercado-diario",
        }
        if errors:
            result["_errors"] = errors

        return result

    def get_energy_dashboard(self, months: int = 13,
                             ref_date: Optional[datetime] = None) -> Dict:
        """Full energy dashboard: balance + market prices."""
        dashboard = self.get_monthly_balance(months, ref_date)
        dashboard["market_price"] = self.get_market_prices(months, ref_date)
        return dashboard
