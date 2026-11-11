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


def ok(body: bytes, status: int = 200, url: str = "http://fake/data/1") -> HttpResult:
    return HttpResult(status=status, body=body, url=url)


class FakeSource:
    """Yields `pages` pages (page=1..n) from http://fake/data/<page>, one at a time (a generator,
    like a real paginating adapter); each page is a JSON payload(). Rows carry their page's
    response_index."""
    name = "fake"
    expected_format = "json"

    def __init__(self, pages: int = 1):
        self.pages = pages

    def fetch(self, specs, http):
        for page in range(1, self.pages + 1):
            params = {"page": page}
            r = http.get(f"http://fake/data/{page}", params=params)
            yield RawResponse(url=r.url, params=params, status=r.status, body=r.body)

    def parse(self, specs, responses):
        rows: dict[str, list[RawRow]] = {s.id: [] for s in specs}
        for i, resp in enumerate(responses):
            doc = json.loads(resp.body, parse_float=str, parse_int=str)
            for sid, pairs in doc["series"].items():
                rows.setdefault(sid, []).extend(
                    RawRow(period_raw=p, value_raw=v, response_index=i) for p, v in pairs)
        return rows


class ListFakeSource(FakeSource):
    """Same as FakeSource, but fetch returns a plain list (the other allowed shape)."""

    def fetch(self, specs, http):
        return list(super().fetch(specs, http))


class FakeVerifier:
    """Answers each check() from `truths[k]` (k = call number, the last one repeats):
    a dict {(series_id, period): observed_text}; a missing key observes None (not found).
    Echoes series_id/period, records every call's items, and raises `raises` if set."""
    source_name = "fake"

    def __init__(self, *truths: dict, decimal: str = ".", unit: str | None = None,
                 flag: str | None = None, raises: BaseException | None = None):
        self.truths = list(truths) or [{}]
        self.decimal, self.unit, self.flag, self.raises = decimal, unit, flag, raises
        self.calls: list[list] = []

    def check(self, items, http):
        from ingest.verifiers import ItemResult
        self.calls.append(list(items))
        if self.raises is not None:
            raise self.raises
        truth = self.truths[min(len(self.calls), len(self.truths)) - 1]
        return [ItemResult(observed_text=truth.get((i.series_id, i.period)),
                           evidence_url=f"http://verify.fake/{i.series_id}/{i.period}",
                           observed_decimal=self.decimal, observed_unit=self.unit,
                           observed_flag=self.flag, series_id=i.series_id, period=i.period)
                for i in items]


def truth_of(series: dict[str, list[list[str]]]) -> dict[tuple[str, str], str]:
    """The FakeVerifier truth that agrees with payload(series)."""
    return {(sid, p): v for sid, rows in series.items() for p, v in rows}
