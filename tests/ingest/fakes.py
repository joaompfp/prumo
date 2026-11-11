"""Test doubles for the pipeline: a scripted Http and a paginated JSON Source."""
import json

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

SOURCE = SourceSpec(name="fake", licence="CC-BY-4.0", licence_url="http://l", attribution="Fake",
                    redistribution_ok=True)


def spec(sid: str = "s1", frequency: str = "A", unit: str = "EUR") -> SeriesSpec:
    return SeriesSpec(id=sid, source=SOURCE, indicator_key=f"k_{sid}", role="primary",
                      theme="economy", geography="PT", frequency=frequency, unit=unit)


def payload(series: dict[str, list[list[str]]]) -> bytes:
    """JSON page {"series": {"s1": [["2024", 1.50], ...]}}. Numeric tokens are written verbatim
    as JSON numbers (so "1.50" stays "1.50"); anything else becomes a JSON string."""
    def tok(v: str) -> str:
        try:
            json.loads(v)
            return v if not v.startswith('"') else json.dumps(v)
        except ValueError:
            return json.dumps(v)
    parts = []
    for sid, rows in series.items():
        items = ", ".join(f"[{json.dumps(p)}, {tok(v)}]" for p, v in rows)
        parts.append(f"{json.dumps(sid)}: [{items}]")
    return ('{"series": {' + ", ".join(parts) + "}}").encode()


class FakeHttp:
    """Answers each get() with the next scripted item: an HttpResult, or an Exception to raise."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params))
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def ok(body: bytes, status: int = 200, url: str = "http://fake/data") -> HttpResult:
    return HttpResult(status=status, body=body, url=url)


class FakeSource:
    """Fetches `pages` pages (page=1..n) from http://fake/data; each page is a JSON payload()."""
    name = "fake"
    expected_format = "json"

    def __init__(self, pages: int = 1):
        self.pages = pages

    def fetch(self, specs, http):
        out = []
        for page in range(1, self.pages + 1):
            params = {"page": page}
            r = http.get("http://fake/data", params=params)
            out.append(RawResponse(url=r.url, params=params, status=r.status, body=r.body))
        return out

    def parse(self, specs, responses):
        rows: dict[str, list[RawRow]] = {s.id: [] for s in specs}
        for resp in responses:
            doc = json.loads(resp.body, parse_float=str, parse_int=str)
            for sid, pairs in doc["series"].items():
                rows.setdefault(sid, []).extend(
                    RawRow(period_raw=p, value_raw=v) for p, v in pairs)
        return rows
