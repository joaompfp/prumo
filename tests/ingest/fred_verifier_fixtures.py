"""Test-only doubles for the FRED independent channel: serves the recorded server-rendered
/data/<CODE> table pages (tests/ingest/fixtures/fred/table-<CODE>.html, 2026-11-12,
sha256-pinned byte copies of the Task-14 preflight originals, via MANIFEST.json).

This channel is KEYLESS (public publication UI): any query param on a request fails the test —
in particular the collector's api_key must never touch it. `override[file]` replaces a body
and `status[code]` forces an HTTP status (tamper/error tests, always built in-test).
"""
from urllib.parse import urlsplit

from ingest.http import HttpResult
from tests.ingest.fred_fixtures import body, entry


class TableFixtureHttp:
    def __init__(self, override: dict[str, bytes] | None = None,
                 status: dict[str, int] | None = None):
        self.calls: list[str] = []
        self.override = override or {}
        self.status = status or {}

    def get(self, url, params=None, headers=None, timeout=None):
        if params:
            raise AssertionError(f"the FRED data-table channel takes no query params: {params}")
        parts = urlsplit(url)
        if parts.netloc != "fred.stlouisfed.org" or not parts.path.startswith("/data/"):
            raise AssertionError(f"not a fred.stlouisfed.org/data/<CODE> URL: {url}")
        code = parts.path[len("/data/"):]
        file = f"table-{code}.html"
        try:
            e = entry(file)
        except KeyError:
            raise AssertionError(f"no recorded fred table page for {code!r}") from None
        self.calls.append(code)
        return HttpResult(status=int(self.status.get(code, e["status"])),
                          body=self.override.get(file, body(file)), url=e["url"])
