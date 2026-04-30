#!/usr/bin/env python3
"""
Dados.gov.pt collector — Portugal's open data portal (CKAN API).

Collects structured datasets from dados.gov.pt, the Portuguese government's
open data portal. Uses the CKAN API (v3) for metadata and resource access.

Target datasets (initial scope):
  - Execução orçamental do Estado (DGO)
  - PRR milestones e execução (Recuperar Portugal)
  - Transportes públicos (IMT)

Usage:
  python collectors/dadosgov.py                    # print results
  python collectors/dadosgov.py --parquet          # write to staging/
  python collectors/dadosgov.py --search "energia" # search datasets
"""
import csv
import io
import json
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from base import standardize_rows, write_parquet

BASE_URL = "https://dados.gov.pt/api/3"

# Known datasets with structured, machine-readable resources
KNOWN_DATASETS = {
    "execucao-orcamental": {
        "id": "execucao-orcamental-da-administracao-central",
        "description": "Execução orçamental — despesa e receita do Estado",
        "indicators": {
            "budget_revenue": {"label": "Receita do Estado", "unit": "€ milhões"},
            "budget_expenditure": {"label": "Despesa do Estado", "unit": "€ milhões"},
            "budget_balance": {"label": "Saldo orçamental", "unit": "€ milhões"},
        },
    },
    "prr-execucao": {
        "id": "plano-de-recuperacao-e-resiliencia",
        "description": "PRR — execução por componente",
        "indicators": {
            "prr_approved": {"label": "PRR aprovado", "unit": "€ milhões"},
            "prr_executed": {"label": "PRR executado", "unit": "€ milhões"},
            "prr_execution_rate": {"label": "Taxa execução PRR", "unit": "%"},
        },
    },
}


class DadosGovCollector:
    """Collector for dados.gov.pt open data portal."""

    SOURCE = "DADOSGOV"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Prumo/1.0 (https://joao.date/dados)",
        })

    def search_datasets(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for datasets on dados.gov.pt."""
        url = f"{BASE_URL}/action/package_search"
        params = {"q": query, "rows": limit}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("result", {}).get("results", [])
            return [{
                "id": r["name"],
                "title": r.get("title", ""),
                "organization": r.get("organization", {}).get("title", ""),
                "num_resources": r.get("num_resources", 0),
                "metadata_modified": r.get("metadata_modified", ""),
                "notes": (r.get("notes") or "")[:200],
            } for r in results]
        except Exception as e:
            print(f"  ⚠ search error: {e}", file=sys.stderr)
            return []

    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """Get metadata and resources for a specific dataset."""
        url = f"{BASE_URL}/action/package_show"
        params = {"id": dataset_id}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("result")
        except Exception as e:
            print(f"  ⚠ dataset {dataset_id}: {e}", file=sys.stderr)
            return None

    def download_csv_resource(self, resource_url: str) -> List[Dict]:
        """Download and parse a CSV resource."""
        try:
            resp = self.session.get(resource_url, timeout=30)
            resp.raise_for_status()
            text = resp.text
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)
        except Exception as e:
            print(f"  ⚠ CSV download: {e}", file=sys.stderr)
            return []

    def collect_all(self) -> List[Dict]:
        """Collect data from all known datasets. Returns DB-schema rows."""
        rows = []
        for key, config in KNOWN_DATASETS.items():
            try:
                dataset = self.get_dataset(config["id"])
                if not dataset:
                    continue

                # Find CSV resources (prefer most recently modified)
                csv_resources = [
                    r for r in dataset.get("resources", [])
                    if r.get("format", "").upper() == "CSV"
                ]
                if not csv_resources:
                    print(f"  ⚠ {key}: no CSV resources found", file=sys.stderr)
                    continue

                # Sort by last_modified descending
                csv_resources.sort(
                    key=lambda r: r.get("last_modified", ""), reverse=True
                )
                resource = csv_resources[0]
                resource_url = resource.get("url", "")
                if not resource_url:
                    continue

                csv_rows = self.download_csv_resource(resource_url)
                if not csv_rows:
                    continue

                parsed = self._parse_dataset(key, config, csv_rows)
                rows.extend(parsed)
                print(f"  ✓ {key}: {len(parsed)} rows from {resource.get('name', 'CSV')}")

            except Exception as e:
                print(f"  ✗ {key}: {e}", file=sys.stderr)

        return rows

    def _parse_dataset(self, key: str, config: dict, csv_rows: List[Dict]) -> List[Dict]:
        """Parse CSV rows into DB-schema rows. Override per dataset as needed."""
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = []

        # Generic parser: look for common column patterns
        # (period/data/ano, valor/value, indicador/indicator)
        period_cols = ["period", "periodo", "data", "ano", "year", "date", "mes"]
        value_cols = ["valor", "value", "montante", "amount"]
        indicator_cols = ["indicador", "indicator", "rubrica", "componente"]

        if not csv_rows:
            return rows

        # Find matching columns (case-insensitive)
        header = {k.lower().strip(): k for k in csv_rows[0].keys()}
        period_col = next((header[c] for c in period_cols if c in header), None)
        value_col = next((header[c] for c in value_cols if c in header), None)

        if not period_col or not value_col:
            print(f"  ⚠ {key}: could not identify period/value columns in CSV")
            print(f"    columns: {list(csv_rows[0].keys())}")
            return rows

        indicator_col = next((header[c] for c in indicator_cols if c in header), None)

        for row in csv_rows:
            try:
                period = str(row.get(period_col, "")).strip()
                value_str = str(row.get(value_col, "")).strip().replace(",", ".")
                if not period or not value_str:
                    continue
                value = float(value_str)
                indicator = row.get(indicator_col, key).strip() if indicator_col else key
                # Slugify indicator name
                indicator_slug = indicator.lower().replace(" ", "_")[:50]

                rows.append({
                    "source": self.SOURCE,
                    "indicator": f"dadosgov_{indicator_slug}",
                    "region": "PT",
                    "period": period,
                    "value": value,
                    "unit": "",
                    "category": config.get("description", ""),
                    "detail": indicator,
                    "fetched_at": fetched_at,
                    "source_id": config["id"],
                })
            except (ValueError, TypeError):
                continue

        return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dados.gov.pt collector")
    parser.add_argument("--parquet", action="store_true", help="Write Parquet to staging")
    parser.add_argument("--search", help="Search datasets by keyword")
    parser.add_argument("--dataset", help="Inspect a specific dataset ID")
    args = parser.parse_args()

    collector = DadosGovCollector()

    if args.search:
        results = collector.search_datasets(args.search)
        for r in results:
            print(f"\n{r['id']}")
            print(f"  {r['title']} ({r['organization']})")
            print(f"  {r['num_resources']} resources | modified: {r['metadata_modified'][:10]}")
            if r['notes']:
                print(f"  {r['notes']}")
        return

    if args.dataset:
        ds = collector.get_dataset(args.dataset)
        if ds:
            print(json.dumps({
                "title": ds.get("title"),
                "organization": ds.get("organization", {}).get("title"),
                "resources": [{
                    "name": r.get("name"),
                    "format": r.get("format"),
                    "url": r.get("url"),
                    "last_modified": r.get("last_modified"),
                } for r in ds.get("resources", [])],
            }, indent=2, ensure_ascii=False))
        return

    rows = collector.collect_all()
    print(f"\nCollected {len(rows)} rows from dados.gov.pt")

    if args.parquet and rows:
        write_parquet(rows, source="DADOSGOV")


if __name__ == "__main__":
    main()
