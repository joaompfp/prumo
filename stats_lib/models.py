from dataclasses import dataclass, field


@dataclass
class DataPoint:
    period: str       # "YYYY-MM"
    value: float
    region: str       # "PT", "DE", "EU27", ...
    indicator: str    # código interno, ex: "STS_INPR_M_C"
    source: str       # "EUROSTAT", "INE", ...
    unit: str = "I21"
    category: str = "compare"
    fetched_at: str = ""
