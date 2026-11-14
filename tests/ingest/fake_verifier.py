"""FakeVerifier, in its own module so it satisfies register_verifier's independence rule
(it imports nothing from the collector side: no FakeSource, no ingest.sources/validate)."""
import json

from ingest.verifiers import ItemResult


class FakeVerifier:
    """Answers each check() from `truths[k]` (k = call number, the last one repeats):
    a dict {(series_id, period): observed_text}; a missing key observes None (not found).
    Echoes the key, records every call's (blinded) items, raises `raises` if set. Evidence
    (mandatory since Task 21) is a small JSON document of everything the result claims, which
    `reread` decodes; evidence=False returns none (an item without evidence fails)."""
    source_name = "fake"
    not_compared = {"unit": "fake channel: unit not exposed unless configured",
                    "flag": "fake channel: flag not exposed unless configured"}

    def __init__(self, *truths: dict, decimal: str = ".", unit: str | None = None,
                 flag: str | None = None, raises: BaseException | None = None,
                 evidence: bool = True):
        self.truths = list(truths) or [{}]
        self.decimal, self.unit, self.flag, self.raises = decimal, unit, flag, raises
        self.evidence = evidence
        self.calls: list[list] = []

    def request_key(self, item):
        return item.series_id, item.period

    def reread(self, evidence, item):
        d = json.loads(evidence)
        if (d["series_id"], d["period"]) != (item.series_id, item.period):
            raise ValueError("evidence is for another item")
        return ItemResult(d["series_id"], d["period"], d["text"], d["url"],
                          observed_decimal=d["decimal"], observed_unit=d["unit"],
                          observed_flag=d["flag"], evidence=evidence)

    def check(self, items, http):
        self.calls.append(list(items))
        if self.raises is not None:
            raise self.raises
        truth = self.truths[min(len(self.calls), len(self.truths)) - 1]
        out = []
        for i in items:
            text = truth.get((i.series_id, i.period))
            url = f"http://verify.fake/{i.series_id}/{i.period}"
            doc = {"series_id": i.series_id, "period": i.period, "text": text, "url": url,
                   "decimal": self.decimal, "unit": self.unit, "flag": self.flag}
            out.append(ItemResult(
                i.series_id, i.period, text, url,
                observed_decimal=self.decimal, observed_unit=self.unit, observed_flag=self.flag,
                evidence=json.dumps(doc, sort_keys=True).encode() if self.evidence else None))
        return out
