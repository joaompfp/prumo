"""Source adapter contract. One adapter per publisher (Tasks 9-16) implements `Source`.

An adapter does two pure-ish things and nothing else (no DB, no raw store, no validation):
  fetch: talk to the publisher through the injected `Http` and return every response verbatim;
  parse: turn those responses into the publisher's tokens (`RawRow`), keyed by series id.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar, Literal, Protocol

from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.validate import RawRow

ExpectedFormat = Literal["json", "csv", "xml", "tsv"]


@dataclass(frozen=True)
class RawResponse:
    """One HTTP exchange, unmodified. `body` is stored byte-for-byte in the raw store."""
    url: str
    params: dict | None
    status: int
    body: bytes


class Source(Protocol):
    """Contract consumed by `ingest.pipeline.run_dataset`.

    name: equals the registry `SourceSpec.name` of every spec handed to this source.
    expected_format: optional. When set, a 2xx body that is clearly an HTML page is a failed
        fetch (publishers often answer 200 with an HTML error page). None = no sniffing.
        The pipeline reads it with getattr(..., None), so adapters may omit it.
    fetch: yield (or return a list of) ALL responses (every page) in fetch order. Prefer a
        generator: the pipeline stores each response as evidence as soon as it is yielded, so
        pages received before a failure are kept. Do not filter or retry on status; yield
        non-2xx responses as they are, the pipeline classifies them. Let exceptions from
        `http.get` propagate: the run then fails (failed-fetch) with no observations written.
    parse: map series_id -> RawRow list for every spec. Tokens must be the publisher's strings
        (e.g. json.loads(body, parse_float=str, parse_int=str)); validation happens later.
        Set RawRow.response_index to the index (in fetch order) of the response the row came
        from (default 0 is right for single-response sources). Raise on anything unexpected;
        never guess.
    """
    name: str
    expected_format: ClassVar[ExpectedFormat | None]

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterable[RawResponse]: ...

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]: ...
