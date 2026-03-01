from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import List

from .db import db_get, db_get_periods, db_write
from .models import DataPoint

RECENT_CUTOFF_DAYS = 60  # períodos mais recentes podem ter revisões


def _all_months(since: str, until: str) -> List[str]:
    """Gera lista de 'YYYY-MM' entre since e until inclusive."""
    result = []
    cur = datetime.strptime(since, "%Y-%m")
    end = datetime.strptime(until, "%Y-%m")
    while cur <= end:
        result.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return result


class DataSource(ABC):
    source_name: str

    @abstractmethod
    def fetch_remote(self, indicator: str, regions: List[str], since: str) -> List[DataPoint]:
        """Vai à API externa. Implementado por cada source."""

    def fetch_or_cache(
        self,
        indicator: str,
        regions: List[str],
        since: str,
        until: str = None,
    ) -> List[DataPoint]:
        """Padrão principal.

        Para cada region verifica quais períodos faltam:
          - histórico (> 60 dias): só fetch se não está na BD
          - recente  (< 60 dias): re-fetch se períodos ausentes

        Escreve o que veio da rede → BD.
        Serve sempre da BD.
        """
        until = until or date.today().strftime("%Y-%m")
        cutoff = (date.today() - timedelta(days=RECENT_CUTOFF_DAYS)).strftime("%Y-%m")
        all_periods = set(_all_months(since, until))

        regions_need_fetch = []
        for region in regions:
            have = db_get_periods(indicator, region, since)
            missing_hist = [p for p in all_periods if p < cutoff and p not in have]
            missing_recent = [p for p in all_periods if p >= cutoff and p not in have]
            if missing_hist or missing_recent:
                regions_need_fetch.append(region)

        # Points fetched from remote but not yet persisted (fallback if DB write fails)
        fallback_points: List[DataPoint] = []

        if regions_need_fetch:
            try:
                remote = self.fetch_remote(indicator, regions_need_fetch, since)
                if remote:
                    fallback_points = remote
                    try:
                        written = db_write(remote)
                        print(f"[{self.source_name}] wrote {written} points to DB", flush=True)
                        fallback_points = []  # cleared — will serve from DB below
                    except Exception as write_err:
                        print(
                            f"[{self.source_name}] db_write failed ({write_err}), "
                            f"serving {len(remote)} points from memory",
                            flush=True,
                        )
                else:
                    print(
                        f"[{self.source_name}] fetch_remote returned empty for "
                        f"{indicator} / {regions_need_fetch}",
                        flush=True,
                    )
            except Exception as e:
                print(f"[{self.source_name}] fetch_remote failed: {e}", flush=True)

        # If we have in-memory points (write failed), merge with whatever is in DB
        db_points = db_get(indicator, regions, since, source=self.source_name)

        if fallback_points:
            # Merge: DB points + in-memory points, deduplicated by (region, period)
            seen = {(p.region, p.period) for p in db_points}
            merged = list(db_points)
            for p in fallback_points:
                if (p.region, p.period) not in seen:
                    merged.append(p)
                    seen.add((p.region, p.period))
            return merged

        return db_points
