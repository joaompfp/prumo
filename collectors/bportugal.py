#!/usr/bin/env python3
"""
BPstat (Banco de Portugal) API Client — Financial & Monetary Statistics
API pública, sem autenticação — JSON-stat v2.0
Docs: https://bpstat.bportugal.pt/data/docs

Séries disponíveis: 210.000+ séries incluindo Euribor, yields OT,
câmbios, crédito, depósitos, balança de pagamentos.
"""

import requests
from typing import Optional, Dict, List
from datetime import datetime
from dateutil.relativedelta import relativedelta


class BPortugalClient:
    """Cliente para BPstat API (Banco de Portugal)"""

    BASE_URL = "https://bpstat.bportugal.pt/data/v1"

    # ── Séries pré-definidas: (series_id, domain_id, dataset_id, label) ──

    SERIES = {
        # Euribor (monthly averages)
        "euribor_1m":  {"id": 13168439, "domain": 22, "dataset": "2829cb9155cb4f6ba6906db6b204c4bc", "label": "Euribor 1M"},
        "euribor_3m":  {"id": 13168436, "domain": 22, "dataset": "2829cb9155cb4f6ba6906db6b204c4bc", "label": "Euribor 3M"},
        "euribor_6m":  {"id": 13168438, "domain": 22, "dataset": "2829cb9155cb4f6ba6906db6b204c4bc", "label": "Euribor 6M"},
        "euribor_12m": {"id": 13168437, "domain": 22, "dataset": "2829cb9155cb4f6ba6906db6b204c4bc", "label": "Euribor 12M"},

        # Exchange rates (monthly averages)
        "eur_usd":     {"id": 12531993, "domain": 29, "dataset": "23e0cdd56bddb4ad3016a9c3ad63a539", "label": "EUR/USD (monthly avg)"},

        # Government bond yields (monthly averages)
        "pt_10y":      {"id": 12099464, "domain": 26, "dataset": "690b7b36fd36c0dbe249c48cbbc39524", "label": "OT Portugal 10 anos"},
        "de_10y":      {"id": 12560098, "domain": 26, "dataset": "690b7b36fd36c0dbe249c48cbbc39524", "label": "Bund Alemanha 10 anos"},

        # Household credit (stock, M EUR, monthly)
        "credit_housing":  {"id": 12557378, "domain": 19, "dataset": "28b6a921e1a4a9e326e724ab3e043d97", "label": "Crédito habitação (stock)"},
        "credit_consumer": {"id": 12557382, "domain": 19, "dataset": "28b6a921e1a4a9e326e724ab3e043d97", "label": "Crédito consumo (stock)"},

        # Deposits (households, stock, M EUR, monthly)
        "deposits_households": {"id": 12556700, "domain": 19, "dataset": "d5bf6198a39f1e77b0d14dda97103de0", "label": "Depósitos famílias (stock)"},

        # Interest rates on new operations — TODO: verify series IDs via BPstat domain 21
        # "rate_housing_new": {"id": TBD, "domain": 21, "dataset": "TBD", "label": "Taxa juro crédito habitação (novas op.)"},
        # "rate_deposit_new": {"id": TBD, "domain": 21, "dataset": "TBD", "label": "Taxa juro depósitos (novas op.)"},
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "cae-reports/1.0",
        })

    def _fetch_series(self, series_key: str, months: int = 13,
                      ref_date: Optional[datetime] = None) -> Dict:
        """Fetch observations for a pre-defined series.

        Args:
            series_key: Key from SERIES dict (e.g., 'euribor_3m')
            months: Number of months to fetch
            ref_date: Reference date anchor (default: now)

        Returns:
            Standardized response dict with 'data' array.
        """
        if series_key not in self.SERIES:
            return {"error": f"Unknown series: {series_key}",
                    "series": series_key, "source": "BPstat"}

        spec = self.SERIES[series_key]
        anchor = ref_date or datetime.now()
        obs_since = (anchor - relativedelta(months=months)).strftime("%Y-%m-%d")
        obs_to = anchor.strftime("%Y-%m-%d")

        url = (f"{self.BASE_URL}/domains/{spec['domain']}"
               f"/datasets/{spec['dataset']}/")

        params = {
            "lang": "EN",
            "series_ids": str(spec["id"]),
            "obs_since": obs_since,
            "obs_to": obs_to,
        }

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            return self._parse_jsonstat(data, spec)

        except requests.exceptions.RequestException as e:
            return {"error": str(e), "series": series_key,
                    "source": "BPstat"}
        except (KeyError, IndexError, ValueError) as e:
            return {"error": f"Parse error: {e}", "series": series_key,
                    "source": "BPstat"}

    def _parse_jsonstat(self, raw: Dict, spec: Dict) -> Dict:
        """Parse JSON-stat v2.0 response into standardized format."""
        # JSON-stat has flat value[] array aligned with reference_date index
        values = raw.get("value", [])
        statuses = raw.get("status", [])

        # Get date dimension
        dims = raw.get("dimension", {})
        ref_dim = dims.get("reference_date", {})
        date_index = list(ref_dim.get("category", {}).get("index", {}).keys()
                          if isinstance(ref_dim.get("category", {}).get("index"), dict)
                          else ref_dim.get("category", {}).get("index", []))

        # For multi-series requests, we need to figure out the stride
        # For single-series, values align directly with dates
        num_dates = len(date_index)
        if not num_dates or not values:
            return {
                "series": spec.get("label", ""),
                "series_id": str(spec["id"]),
                "count": 0,
                "data": [],
                "source": "BPstat",
                "url": f"https://bpstat.bportugal.pt/serie/{spec['id']}",
            }

        # For single series, values[0..N-1] = observations
        obs = []
        for i, date_str in enumerate(date_index):
            if i >= len(values):
                break
            val = values[i]
            if val is None:
                continue
            # BPstat dates are end-of-month: "2025-12-31" → period "2025-12"
            period = date_str[:7] if len(date_str) >= 7 else date_str
            obs.append({
                "period": period,
                "date": date_str,
                "value": val,
                "status": statuses[i] if i < len(statuses) else "",
            })

        return {
            "series": spec.get("label", ""),
            "series_id": str(spec["id"]),
            "count": len(obs),
            "data": obs,
            "source": "BPstat",
            "url": f"https://bpstat.bportugal.pt/serie/{spec['id']}",
        }

    def _fetch_multiple(self, series_keys: List[str], months: int = 13,
                        ref_date: Optional[datetime] = None) -> Dict:
        """Fetch multiple series, grouped by dataset for efficiency."""
        # Group series by (domain, dataset) to batch requests
        from collections import defaultdict
        groups = defaultdict(list)
        for key in series_keys:
            if key in self.SERIES:
                spec = self.SERIES[key]
                groups[(spec["domain"], spec["dataset"])].append((key, spec))

        results = {}
        anchor = ref_date or datetime.now()
        obs_since = (anchor - relativedelta(months=months)).strftime("%Y-%m-%d")
        obs_to = anchor.strftime("%Y-%m-%d")

        for (domain, dataset), items in groups.items():
            series_ids = ",".join(str(spec["id"]) for _, spec in items)
            url = f"{self.BASE_URL}/domains/{domain}/datasets/{dataset}/"
            params = {
                "lang": "EN",
                "series_ids": series_ids,
                "obs_since": obs_since,
                "obs_to": obs_to,
            }

            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                raw = resp.json()

                # Multi-series JSON-stat: need to split by series
                self._split_multi_series(raw, items, results)

            except requests.exceptions.RequestException as e:
                for key, spec in items:
                    results[key] = {"error": str(e), "series": key,
                                    "source": "BPstat"}

        return results

    def _split_multi_series(self, raw: Dict, items: list,
                            results: Dict):
        """Split a multi-series JSON-stat response into individual results."""
        values = raw.get("value", [])
        statuses = raw.get("status", [])
        dims = raw.get("dimension", {})
        ref_dim = dims.get("reference_date", {})

        date_cat = ref_dim.get("category", {})
        if isinstance(date_cat.get("index"), dict):
            date_index = list(date_cat["index"].keys())
        else:
            date_index = list(date_cat.get("index", []))

        num_dates = len(date_index)
        num_series = len(items)

        if not num_dates or not values:
            for key, spec in items:
                results[key] = {
                    "series": spec.get("label", ""),
                    "series_id": str(spec["id"]),
                    "count": 0, "data": [],
                    "source": "BPstat",
                    "url": f"https://bpstat.bportugal.pt/serie/{spec['id']}",
                }
            return

        # JSON-stat v2.0 multi-series: values are in row-major order
        # dimensions × dates. For N series × D dates → N*D values.
        # Series order matches the extension.series order from the API.
        # If we have exactly num_series * num_dates values, split evenly.
        ext_series = raw.get("extension", {}).get("series", [])
        ext_ids = [s["id"] for s in ext_series] if ext_series else []

        for idx, (key, spec) in enumerate(items):
            # Find this series' position in the response
            if ext_ids:
                try:
                    pos = ext_ids.index(spec["id"])
                except ValueError:
                    pos = idx
            else:
                pos = idx

            start = pos * num_dates
            end = start + num_dates

            obs = []
            for i, date_str in enumerate(date_index):
                vi = start + i
                if vi >= len(values):
                    break
                val = values[vi]
                if val is None:
                    continue
                period = date_str[:7] if len(date_str) >= 7 else date_str
                obs.append({
                    "period": period,
                    "date": date_str,
                    "value": val,
                    "status": statuses[vi] if vi < len(statuses) else "",
                })

            results[key] = {
                "series": spec.get("label", ""),
                "series_id": str(spec["id"]),
                "count": len(obs),
                "data": obs,
                "source": "BPstat",
                "url": f"https://bpstat.bportugal.pt/serie/{spec['id']}",
            }

    # ── Public convenience methods ────────────────────────────────

    def get_euribor(self, months: int = 13,
                    ref_date: Optional[datetime] = None) -> Dict:
        """All Euribor maturities (1M, 3M, 6M, 12M)."""
        return self._fetch_multiple(
            ["euribor_1m", "euribor_3m", "euribor_6m", "euribor_12m"],
            months=months, ref_date=ref_date)

    def get_bond_yields(self, months: int = 13,
                        ref_date: Optional[datetime] = None) -> Dict:
        """Portuguese and German 10-year government bond yields."""
        results = self._fetch_multiple(
            ["pt_10y", "de_10y"], months=months, ref_date=ref_date)
        # Add spread calculation
        pt = results.get("pt_10y", {})
        de = results.get("de_10y", {})
        if pt.get("data") and de.get("data"):
            de_map = {o["period"]: o["value"] for o in de["data"]}
            spread_data = []
            for o in pt["data"]:
                de_val = de_map.get(o["period"])
                if de_val is not None:
                    spread_data.append({
                        "period": o["period"],
                        "date": o["date"],
                        "value": round(o["value"] - de_val, 4),
                    })
            results["spread_pt_de"] = {
                "series": "Spread PT-DE 10 anos",
                "series_id": "computed",
                "count": len(spread_data),
                "data": spread_data,
                "source": "BPstat (calculado)",
                "url": "",
            }
        return results

    def get_exchange_rates(self, months: int = 13,
                           ref_date: Optional[datetime] = None) -> Dict:
        """EUR/USD monthly average."""
        return {"eur_usd": self._fetch_series("eur_usd", months, ref_date)}

    def get_credit(self, months: int = 13,
                   ref_date: Optional[datetime] = None) -> Dict:
        """Household credit (housing + consumer) stock."""
        return self._fetch_multiple(
            ["credit_housing", "credit_consumer"],
            months=months, ref_date=ref_date)

    def get_deposits(self, months: int = 13,
                     ref_date: Optional[datetime] = None) -> Dict:
        """Household deposits stock."""
        return {"deposits": self._fetch_series("deposits_households", months, ref_date)}

    def get_financial_dashboard(self, months: int = 13,
                                ref_date: Optional[datetime] = None) -> Dict:
        """Full financial dashboard: Euribor, yields, FX, credit, deposits."""
        dashboard = {}
        dashboard.update(self.get_euribor(months, ref_date))
        dashboard.update(self.get_bond_yields(months, ref_date))
        dashboard.update(self.get_exchange_rates(months, ref_date))
        dashboard.update(self.get_credit(months, ref_date))
        dashboard.update(self.get_deposits(months, ref_date))
        return dashboard
