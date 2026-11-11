"""Independent verifier contract (spec 6b). One verifier per source (Tasks 9-16) implements
`Verifier`; it re-reads sampled observations through a channel different from the collector's
(another endpoint or format, the publisher's web table, a downloadable file) and must not reuse the
collector's parser.
"""
from dataclasses import dataclass
from typing import Literal, Protocol

from ingest.http import Http
from ingest.models import SeriesSpec


@dataclass(frozen=True)
class SampleItem:
    """One sampled observation, as stored by the run under verification."""
    series_id: str
    period: str  # canonical period
    expected_text: str  # stored value_text (publisher token, in spec.decimal format)
    spec: SeriesSpec
    expected_unit: str
    expected_flag: str | None


@dataclass(frozen=True)
class ItemResult:
    """What the independent channel shows for one SampleItem.

    observed_text: the publisher's number as shown there, None = not found (a mismatch).
    evidence_url: where it was read (URL incl. query, or file URL + locator), for the audit.
    observed_decimal: decimal separator of observed_text.
    observed_unit / observed_flag: None = this channel does not expose them (not compared).
    series_id / period: SHOULD echo the item's key; when given they must equal it, so a result
        returned out of order is caught instead of being compared against the wrong item.
    """
    observed_text: str | None
    evidence_url: str
    observed_decimal: Literal[".", ","] = "."
    observed_unit: str | None = None
    observed_flag: str | None = None
    series_id: str | None = None
    period: str | None = None


class Verifier(Protocol):
    """source_name: the registry source this verifier checks.
    check: one ItemResult per item, same length and order; may raise (counted as a failure)."""
    source_name: str

    def check(self, items: list[SampleItem], http: Http) -> list[ItemResult]: ...
