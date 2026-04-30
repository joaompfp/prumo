#!/usr/bin/env python3
"""
Habitação collector — Housing market indicators for Portugal.

Sources:
  - INE: Índice de Preços da Habitação (quarterly), Rendas medianas
  - BPstat: Crédito à habitação concedido (monthly)

Indicators collected:
  - housing_price_index: Índice de preços da habitação (base 2015=100)
  - housing_price_yoy: Variação homóloga preços habitação (%)
  - median_rent: Renda mediana dos novos contratos (€/m2)
  - housing_credit: Novo crédito à habitação concedido (€ milhões)
  - housing_credit_rate: Taxa média crédito habitação (%)

Usage:
  python collectors/habitacao.py              # print results
  python collectors/habitacao.py --parquet    # write to staging/
"""
import json
import sys
from datetime import datetime
from typing import List, Dict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from base import standardize_rows, write_parquet


class HabitacaoCollector:
    """Housing market data from INE + BPstat."""

    SOURCE = "INE"

    def collect_all(self) -> List[Dict]:
        """Collect all housing indicators. Returns DB-schema rows."""
        rows = []
        rows.extend(self._collect_housing_price_index())
        rows.extend(self._collect_median_rent())
        rows.extend(self._collect_housing_credit())
        return rows

    def _collect_housing_price_index(self) -> List[Dict]:
        """INE: Índice de Preços da Habitação (quarterly, 0010527)."""
        import requests

        url = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        params = {
            "op": 2,
            "varcd": "0010527",
            "Ession": "1",
            "lang": "PT",
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ⚠ housing_price_index: {e}", file=sys.stderr)
            return []

        raw = []
        try:
            # INE API returns nested structure: Dados → {period: [{valor, ...}]}
            series = data[0].get("Dados", {})
            for period_raw, values in series.items():
                for v in values:
                    if v.get("valor") and v.get("geocod") == "PT":
                        # Convert INE quarter format (e.g. "2025T1") to ISO
                        period = period_raw.replace("T", "-Q")
                        raw.append({"period": period, "value": float(v["valor"])})
        except (KeyError, IndexError, TypeError) as e:
            print(f"  ⚠ housing_price_index parse: {e}", file=sys.stderr)
            return []

        rows = standardize_rows(raw, "INE", "housing_price_index",
                                unit="índice 2015=100", category="Habitação")

        # Compute YoY from index values
        by_q = {r["period"]: r["value"] for r in raw}
        for r in raw:
            q = r["period"]  # e.g. "2025-Q3"
            try:
                year = int(q.split("-")[0])
                quarter = q.split("-")[1]
                prev_q = f"{year - 1}-{quarter}"
                if prev_q in by_q and by_q[prev_q]:
                    yoy = ((r["value"] - by_q[prev_q]) / by_q[prev_q]) * 100
                    rows.append({
                        "source": "INE", "indicator": "housing_price_yoy",
                        "region": "PT", "period": q, "value": round(yoy, 1),
                        "unit": "%", "category": "Habitação",
                        "detail": None, "fetched_at": rows[0]["fetched_at"]
                        if rows else None, "source_id": None,
                    })
            except (ValueError, IndexError):
                continue

        return rows

    def _collect_median_rent(self) -> List[Dict]:
        """INE: Renda mediana dos novos contratos de arrendamento (€/m2, quarterly).

        Dataset 0011606 — Mediana das rendas de novos contratos.
        """
        import requests

        url = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        params = {"op": 2, "varcd": "0011606", "Ession": "1", "lang": "PT"}
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ⚠ median_rent: {e}", file=sys.stderr)
            return []

        raw = []
        try:
            series = data[0].get("Dados", {})
            for period_raw, values in series.items():
                for v in values:
                    if v.get("valor") and v.get("geocod") == "PT":
                        period = period_raw.replace("T", "-Q")
                        raw.append({"period": period, "value": float(v["valor"])})
        except (KeyError, IndexError, TypeError) as e:
            print(f"  ⚠ median_rent parse: {e}", file=sys.stderr)
            return []

        return standardize_rows(raw, "INE", "median_rent",
                                unit="€/m2", category="Habitação")

    def _collect_housing_credit(self) -> List[Dict]:
        """BPstat: Novo crédito à habitação concedido (monthly).

        Uses BPortugalClient for credit_housing series.
        """
        try:
            from bportugal import BPortugalClient
            client = BPortugalClient()
            # credit_housing is in the default SERIES dict
            result = client.get_series("credit_housing")
            if not result or "data" not in result:
                return []

            raw = []
            for obs in result["data"]:
                if obs.get("value") is not None:
                    raw.append({
                        "period": obs["period"],
                        "value": obs["value"],
                    })

            return standardize_rows(raw, "BPORTUGAL", "housing_credit",
                                    unit="€ milhões", category="Habitação")
        except Exception as e:
            print(f"  ⚠ housing_credit: {e}", file=sys.stderr)
            return []


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Housing market data collector")
    parser.add_argument("--parquet", action="store_true", help="Write Parquet to staging")
    args = parser.parse_args()

    collector = HabitacaoCollector()
    rows = collector.collect_all()

    print(f"\nCollected {len(rows)} housing rows:")
    sources = {}
    for r in rows:
        key = f"{r['source']}/{r['indicator']}"
        sources[key] = sources.get(key, 0) + 1
    for key, count in sorted(sources.items()):
        print(f"  {key}: {count} rows")

    if args.parquet and rows:
        write_parquet(rows, source="HABITACAO")

    return rows


if __name__ == "__main__":
    main()
