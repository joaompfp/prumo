"""FakeVerifier, in its own module so it satisfies register_verifier's independence rule
(it imports nothing from the collector side: no FakeSource, no ingest.sources/validate)."""
from ingest.verifiers import ItemResult


class FakeVerifier:
    """Answers each check() from `truths[k]` (k = call number, the last one repeats):
    a dict {(series_id, period): observed_text}; a missing key observes None (not found).
    Echoes the key, records every call's (blinded) items, raises `raises` if set, and with
    evidence=True returns b"<series>,<period>,<text>" as evidence bytes."""
    source_name = "fake"

    def __init__(self, *truths: dict, decimal: str = ".", unit: str | None = None,
                 flag: str | None = None, raises: BaseException | None = None,
                 evidence: bool = False):
        self.truths = list(truths) or [{}]
        self.decimal, self.unit, self.flag, self.raises = decimal, unit, flag, raises
        self.evidence = evidence
        self.calls: list[list] = []

    def check(self, items, http):
        self.calls.append(list(items))
        if self.raises is not None:
            raise self.raises
        truth = self.truths[min(len(self.calls), len(self.truths)) - 1]
        out = []
        for i in items:
            text = truth.get((i.series_id, i.period))
            out.append(ItemResult(
                i.series_id, i.period, text, f"http://verify.fake/{i.series_id}/{i.period}",
                observed_decimal=self.decimal, observed_unit=self.unit, observed_flag=self.flag,
                evidence=f"{i.series_id},{i.period},{text}".encode() if self.evidence else None))
        return out
