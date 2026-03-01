"""EurostatSource — fetch STS_INPR_M (industrial production) for multiple countries."""

import json
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import List
from urllib.request import Request, urlopen

from ..base import DataSource
from .._country_labels import COUNTRY_LABELS
from ..models import DataPoint

# In-memory cache for get_series results (6-hour TTL)
# Used as fallback when SQLite write is unavailable
_SERIES_CACHE: dict = {}
_SERIES_CACHE_TTL = 6 * 3600  # seconds


class EurostatSource(DataSource):
    source_name = "EUROSTAT"

    # dataset key → nace code, internal indicator code, PT label
    DATASETS = {
        "manufacturing": {
            "nace":      "C",
            "indicator": "STS_INPR_M_C",
            "label":     "Indústria Transformadora",
        },
        "total_industry": {
            "nace":      "B-D",
            "indicator": "STS_INPR_M_BD",
            "label":     "Índice Total Indústria",
        },
        "metals": {
            "nace":      "C24_C25",
            "indicator": "STS_INPR_M_C24C25",
            "label":     "Metais e Produtos Metálicos",
        },
        "chemicals": {
            "nace":      "C20_C21",
            "indicator": "STS_INPR_M_C20C21",
            "label":     "Química e Farmacêutica",
        },
        "transport": {
            "nace":      "C29_C30",
            "indicator": "STS_INPR_M_C29C30",
            "label":     "Equipamento de Transporte",
        },
    }

    # frontend / BD code → Eurostat API code
    GEO_IN = {"EU27": "EU27_2020", "GR": "EL"}
    # Eurostat API code → BD / display code
    GEO_OUT = {"EU27_2020": "EU27"}  # EL stays EL (código oficial)

    def _normalize(self, code: str) -> str:
        """Converte código de região do frontend para o formato do Eurostat."""
        return self.GEO_IN.get(code, code)

    def _denormalize(self, code: str) -> str:
        """Converte código de região do Eurostat para o formato da BD/frontend."""
        return self.GEO_OUT.get(code, code)

    def fetch_remote(self, indicator: str, regions: List[str], since: str) -> List[DataPoint]:
        """Vai ao Eurostat REST API e devolve lista de DataPoint."""
        ds = next((d for d in self.DATASETS.values() if d["indicator"] == indicator), None)
        if not ds:
            print(f"[EUROSTAT] unknown indicator: {indicator}", flush=True)
            return []

        geo_codes = [self._normalize(r) for r in regions]
        geo_params = "&".join(f"geo={c}" for c in geo_codes)
        url = (
            f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/STS_INPR_M"
            f"?format=JSON&lang=EN&indic_bt=PRD&nace_r2={ds['nace']}&s_adj=SCA&unit=I21"
            f"&{geo_params}&sinceTimePeriod={since}"
        )

        req = Request(url, headers={
            "Accept":     "application/json",
            "User-Agent": "CAE-Dashboard/2.0",
        })
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        dims   = data.get("dimension", {})
        size   = data.get("size", [])
        values = data.get("value", {})

        if not dims or not size:
            return []

        time_dim = dims.get("time", {}).get("category", {}).get("index", {})
        geo_dim  = dims.get("geo",  {}).get("category", {}).get("index", {})
        n_time   = size[-1]
        time_by_pos = {v: k for k, v in time_dim.items()}

        today = date.today().isoformat()
        points: List[DataPoint] = []

        for country_code, g_pos in geo_dim.items():
            region = self._denormalize(country_code)
            for t_pos, period in time_by_pos.items():
                val = values.get(str(g_pos * n_time + t_pos))
                if val is not None:
                    points.append(DataPoint(
                        source=self.source_name,
                        indicator=indicator,
                        region=region,
                        period=period,
                        value=float(val),
                        unit="I21",
                        category="compare",
                        fetched_at=today,
                    ))

        return points

    def get_series(self, dataset: str, regions: List[str], months: int) -> List[dict]:
        """API pública para o server.py usar.

        Retorna lista de dicts compatível com o formato do endpoint /api/europa:
          [{"country": "PT", "label": "Portugal", "data": [{"period": ..., "value": ...}]}]

        Usa cache in-memory (6h TTL) quando o SQLite está em modo read-only.
        """
        ds = self.DATASETS.get(dataset)
        if not ds:
            return []

        cache_key = f"{dataset}:{','.join(sorted(regions))}:{months}"
        cached = _SERIES_CACHE.get(cache_key)
        if cached and cached["expires"] > time.time():
            return cached["data"]

        cutoff = date.today() - timedelta(days=months * 30)
        since = cutoff.strftime("%Y-%m")

        points = self.fetch_or_cache(ds["indicator"], regions, since)

        by_region: dict = defaultdict(list)
        for p in points:
            by_region[p.region].append({"period": p.period, "value": p.value})

        result = []
        for region, data in sorted(by_region.items()):
            data.sort(key=lambda x: x["period"])
            result.append({
                "country": region,
                "label":   COUNTRY_LABELS.get(region, region),
                "data":    data,
            })

        if result:
            _SERIES_CACHE[cache_key] = {"data": result, "expires": time.time() + _SERIES_CACHE_TTL}

        return result
