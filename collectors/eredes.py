#!/usr/bin/env python3
"""
E-REDES Open Data Portal Client — OpenDataSoft API v2.1
Portal: https://e-redes.opendatasoft.com
API Docs: https://help.opendatasoft.com/apis/ods-explore-v2/

No authentication needed. All datasets are public.

Key datasets (8):
- consumption_postal: Monthly consumption by postal code (5 years)
- consumption_municipality: Monthly consumption by municipality (10 years)
- total_consumption: 15-min national consumption by voltage level
- production: 15-min national energy production (market + special regime)
- injected_energy: 15-min distributed generation by technology
- forecast: Consumption forecast by voltage level
- cae_geography: CAE economic activity codes by geography
- renewable_connections: New renewable generation connections (PLR)
"""

import requests
from typing import Optional, Dict, List, Any


class EREDESClient:
    """Client for E-REDES OpenDataSoft API v2.1"""

    BASE_URL = "https://e-redes.opendatasoft.com/api/explore/v2.1"

    # Dataset IDs
    DATASETS = {
        "consumption_postal": "02-consumos-faturados-por-codigo-postal-ultimos-5-anos",
        "consumption_municipality": "3-consumos-faturados-por-municipio-ultimos-10-anos",
        "total_consumption": "consumo-total-nacional",
        "production": "energia-produzida-total-nacional",
        "injected_energy": "energia-injetada-na-rede-de-distribuicao",
        "forecast": "previsao-de-consumo",
        "cae_geography": "codigo-de-atividade-economica-por-distrito-concelho-e-freguesia",
        "renewable_connections": "25-plr-producao-renovavel",
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, dataset_id: str, where: Optional[str] = None,
             select: Optional[str] = None, group_by: Optional[str] = None,
             order_by: Optional[str] = None, limit: int = 100,
             offset: int = 0) -> Dict[str, Any]:
        """Generic record fetch from a dataset."""
        url = f"{self.BASE_URL}/catalog/datasets/{dataset_id}/records"
        params = {"limit": min(limit, 100), "offset": offset}
        if where:
            params["where"] = where
        if select:
            params["select"] = select
        if group_by:
            params["group_by"] = group_by
        if order_by:
            params["order_by"] = order_by

        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        return {
            "source": "E-REDES",
            "dataset": dataset_id,
            "total_count": data.get("total_count", 0),
            "count": len(data.get("results", [])),
            "data": [r.get("record", {}).get("fields", r) if "record" in r else r
                     for r in data.get("results", [])],
        }

    def _get_all(self, dataset_id: str, where: Optional[str] = None,
                 limit: int = 1000) -> List[Dict]:
        """Fetch all records with pagination."""
        all_records = []
        offset = 0
        batch = min(limit, 100)
        while offset < limit:
            result = self._get(dataset_id, where=where, limit=batch, offset=offset)
            records = result["data"]
            if not records:
                break
            all_records.extend(records)
            offset += len(records)
            if len(records) < batch:
                break
        return all_records

    def get_data(self, dataset_id: str, where: Optional[str] = None,
                 limit: int = 100) -> Dict[str, Any]:
        """Generic query for any dataset by ID.

        Args:
            dataset_id: OpenDataSoft dataset identifier
            where: ODSQL where clause (e.g., 'ano="2024"')
            limit: Max records to return
        """
        return self._get(dataset_id, where=where, limit=limit)

    # ─── Consumption by postal code (5 years) ─────────────────

    def get_consumption_by_postal_code(self, postal_code: Optional[str] = None,
                                        year: Optional[int] = None,
                                        limit: int = 100) -> Dict[str, Any]:
        """Monthly billed consumption by 4-digit postal code.

        Fields: ano (text), mes (text), date, codigopostal (text), energiaativa (kWh)

        Args:
            postal_code: 4-digit postal code (e.g., "1000", "4000")
            year: Filter by year
            limit: Max records
        """
        ds = self.DATASETS["consumption_postal"]
        clauses = []
        if postal_code:
            clauses.append(f'codigopostal="{postal_code}"')
        if year:
            clauses.append(f'ano="{year}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         order_by="ano DESC, mes DESC")

    # ─── Consumption by municipality (10 years) ───────────────

    def get_consumption_by_municipality(self, municipality: Optional[str] = None,
                                         district: Optional[str] = None,
                                         year: Optional[int] = None,
                                         voltage: Optional[str] = None,
                                         limit: int = 100) -> Dict[str, Any]:
        """Monthly billed consumption by municipality, parish, and voltage level.

        Fields: ano (text), mes (text), data (date), distrito (text), concelho (text),
                freguesia (text), nivel_de_tensao (text), energia_ativa_kwh (double)

        Args:
            municipality: Municipality name (e.g., "Lisboa", "Porto")
            district: District name (e.g., "Lisboa", "Porto")
            year: Filter by year
            voltage: Voltage level filter (e.g., "BT", "MT", "AT")
            limit: Max records
        """
        ds = self.DATASETS["consumption_municipality"]
        clauses = []
        if municipality:
            clauses.append(f'search(concelho, "{municipality}")')
        if district:
            clauses.append(f'search(distrito, "{district}")')
        if year:
            clauses.append(f'ano="{year}"')
        if voltage:
            clauses.append(f'search(nivel_de_tensao, "{voltage}")')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         order_by="ano DESC, mes DESC")

    # ─── Total national consumption (15-min intervals) ────────

    def get_total_consumption(self, year: Optional[int] = None,
                                month: Optional[int] = None,
                                limit: int = 100) -> Dict[str, Any]:
        """Total national consumption in 15-min intervals by voltage level.

        Fields: datahora (datetime), dia, mes, ano (text), date, time,
                bt (kWh), mt (kWh), at (kWh), mat (kWh), total (kWh)

        Args:
            year: Filter by year
            month: Filter by month (1-12)
            limit: Max records (100 = ~25 hours of data)
        """
        ds = self.DATASETS["total_consumption"]
        clauses = []
        if year:
            clauses.append(f'ano="{year}"')
        if month:
            clauses.append(f'mes="{month:02d}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         order_by="datahora DESC")

    def get_daily_consumption(self, year: Optional[int] = None,
                                month: Optional[int] = None,
                                limit: int = 100) -> Dict[str, Any]:
        """Daily national consumption aggregated from 15-min data.

        Args:
            year: Filter by year
            month: Filter by month
            limit: Max records
        """
        ds = self.DATASETS["total_consumption"]
        clauses = []
        if year:
            clauses.append(f'ano="{year}"')
        if month:
            clauses.append(f'mes="{month:02d}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         select="date, SUM(bt) as bt_kwh, SUM(mt) as mt_kwh, SUM(at) as at_kwh, SUM(mat) as mat_kwh, SUM(total) as total_kwh",
                         group_by="date",
                         order_by="date DESC")

    # ─── National energy production (15-min intervals) ────────

    def get_national_production(self, year: Optional[int] = None,
                                  month: Optional[int] = None,
                                  limit: int = 100) -> Dict[str, Any]:
        """National energy production in 15-min intervals.

        Fields: datahora (datetime), dia, mes, ano, date, time,
                dgm (Market kWh), pre (Special Regime kWh), total (kWh)

        Args:
            year: Filter by year
            month: Filter by month
            limit: Max records
        """
        ds = self.DATASETS["production"]
        clauses = []
        if year:
            clauses.append(f'ano="{year}"')
        if month:
            clauses.append(f'mes="{month:02d}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         order_by="datahora DESC")

    def get_daily_production(self, year: Optional[int] = None,
                               month: Optional[int] = None,
                               limit: int = 100) -> Dict[str, Any]:
        """Daily national production aggregated from 15-min data.

        Args:
            year: Filter by year
            month: Filter by month
            limit: Max records
        """
        ds = self.DATASETS["production"]
        clauses = []
        if year:
            clauses.append(f'ano="{year}"')
        if month:
            clauses.append(f'mes="{month:02d}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         select="date, SUM(dgm) as market_kwh, SUM(pre) as special_regime_kwh, SUM(total) as total_kwh",
                         group_by="date",
                         order_by="date DESC")

    # ─── Distributed generation injected energy ───────────────

    def get_injected_energy(self, year: Optional[int] = None,
                              month: Optional[int] = None,
                              limit: int = 100) -> Dict[str, Any]:
        """Energy injected into distribution network by technology (15-min).

        Fields: datahora (datetime), date, time,
                cogeracao (Cogeneration kWh), eolica (Wind kWh),
                fotovoltaica (PV kWh), hidrica (Hydro kWh),
                outras_tecnologias (Other kWh), rede_dist (Distribution kWh)

        Args:
            year: Filter by year
            month: Filter by month
            limit: Max records
        """
        ds = self.DATASETS["injected_energy"]
        clauses = []
        if year:
            clauses.append(f'ano="{year}"')
        if month:
            clauses.append(f'mes="{month:02d}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         order_by="datahora DESC")

    def get_daily_injected_energy(self, year: Optional[int] = None,
                                    month: Optional[int] = None,
                                    limit: int = 100) -> Dict[str, Any]:
        """Daily injected energy by technology.

        Args:
            year: Filter by year
            month: Filter by month
            limit: Max records
        """
        ds = self.DATASETS["injected_energy"]
        clauses = []
        if year:
            clauses.append(f'ano="{year}"')
        if month:
            clauses.append(f'mes="{month:02d}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         select="date, SUM(eolica) as wind_kwh, SUM(fotovoltaica) as pv_kwh, SUM(hidrica) as hydro_kwh, SUM(cogeracao) as cogen_kwh, SUM(outras_tecnologias) as other_kwh",
                         group_by="date",
                         order_by="date DESC")

    # ─── Consumption forecast ─────────────────────────────────

    def get_consumption_forecast(self, limit: int = 100) -> Dict[str, Any]:
        """Consumption forecast by voltage level (15-min intervals).

        Fields: datahora (datetime), data (date), hora, ano, mes, dia,
                mat (kWh), at (kWh), mt (kWh), bt (kWh), total (kWh)

        Args:
            limit: Max records
        """
        ds = self.DATASETS["forecast"]
        return self._get(ds, limit=limit, order_by="datahora DESC")

    # ─── CAE economic activity by geography ───────────────────

    def get_cae_by_municipality(self, municipality: Optional[str] = None,
                                  district: Optional[str] = None,
                                  cae_code: Optional[str] = None,
                                  year: Optional[int] = None,
                                  limit: int = 100) -> Dict[str, Any]:
        """CAE economic activity codes by district/municipality/parish.

        Fields: ano, nuts_iii, codigo_cae, cae, no_de_empresas,
                dis_name (district), con_name (municipality), freguesia (parish)

        Args:
            municipality: Municipality name (con_name field)
            district: District name (dis_name field)
            cae_code: CAE code filter (e.g., "24" for metalurgia)
            year: Filter by year
            limit: Max records
        """
        ds = self.DATASETS["cae_geography"]
        clauses = []
        if municipality:
            clauses.append(f'search(con_name, "{municipality}")')
        if district:
            clauses.append(f'search(dis_name, "{district}")')
        if cae_code:
            clauses.append(f'codigo_cae="{cae_code}"')
        if year:
            clauses.append(f'ano="{year}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit)

    # ─── Renewable generation connections (PLR) ───────────────

    def get_renewable_connections(self, municipality: Optional[str] = None,
                                   year: Optional[int] = None,
                                   limit: int = 100) -> Dict[str, Any]:
        """New renewable generation connections (Production Licence Registry).

        Fields: ano, mes, con_name (municipality), cod_concelho,
                potencia_ligacao (connection power), pedidos_ligacao_rede_executados_nr

        Args:
            municipality: Municipality name (con_name field)
            year: Filter by year
            limit: Max records
        """
        ds = self.DATASETS["renewable_connections"]
        clauses = []
        if municipality:
            clauses.append(f'search(con_name, "{municipality}")')
        if year:
            clauses.append(f'ano="{year}"')
        where = " AND ".join(clauses) if clauses else None
        return self._get(ds, where=where, limit=limit,
                         order_by="ano DESC, mes DESC")

    # ─── Utility / Discovery ──────────────────────────────────

    def list_datasets(self) -> Dict[str, Any]:
        """List all available datasets on the E-REDES portal."""
        url = f"{self.BASE_URL}/catalog/datasets"
        resp = self.session.get(url, params={"limit": 100}, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        datasets = []
        for item in data.get("results", []):
            ds = item.get("dataset", item)
            datasets.append({
                "id": ds.get("dataset_id", ""),
                "title": ds.get("metas", {}).get("default", {}).get("title", ""),
                "records_count": ds.get("metas", {}).get("default", {}).get("records_count", 0),
            })
        return {
            "source": "E-REDES",
            "count": len(datasets),
            "data": datasets,
        }

    def get_dataset_schema(self, dataset_id: str) -> Dict[str, Any]:
        """Get field schema for a dataset."""
        url = f"{self.BASE_URL}/catalog/datasets/{dataset_id}"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        fields = data.get("fields", [])
        return {
            "dataset": dataset_id,
            "fields": [{"name": f["name"], "type": f.get("type", ""),
                         "label": f.get("label", "")} for f in fields],
        }


if __name__ == "__main__":
    import json
    client = EREDESClient()

    print("=== Datasets ===")
    ds = client.list_datasets()
    for d in ds["data"]:
        print(f"  {d['id']}: {d['title']} ({d['records_count']} records)")

    print("\n=== Consumption by postal code (latest 3) ===")
    data = client.get_consumption_by_postal_code(limit=3)
    print(json.dumps(data["data"][:3], indent=2, ensure_ascii=False))

    print(f"\n=== Consumption by municipality (Lisboa, 2024) ===")
    data = client.get_consumption_by_municipality(municipality="LISBOA", year=2024, limit=3)
    print(json.dumps(data["data"][:3], indent=2, ensure_ascii=False))

    print(f"\n=== Daily production (latest 5 days) ===")
    data = client.get_daily_production(limit=5)
    print(json.dumps(data["data"][:5], indent=2, ensure_ascii=False))

    print(f"\n=== Daily injected energy (latest 5 days) ===")
    data = client.get_daily_injected_energy(limit=5)
    print(json.dumps(data["data"][:5], indent=2, ensure_ascii=False))

    print(f"\n=== CAE by municipality (Lisboa, code 24) ===")
    data = client.get_cae_by_municipality(municipality="LISBOA", cae_code="24", limit=3)
    print(json.dumps(data["data"][:3], indent=2, ensure_ascii=False))

    print(f"\n=== Renewable connections (latest 5) ===")
    data = client.get_renewable_connections(limit=5)
    print(json.dumps(data["data"][:5], indent=2, ensure_ascii=False))
