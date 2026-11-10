"""HTTP client contract for source adapters, plus the production implementation.

Adapters depend on the `Http` protocol only; tests pass a fake. `RequestsHttp` is the real one.
"""
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlsplit

import requests

USER_AGENT = "prumo-ingest/1.0 (+https://cae.joao.date)"
MAX_REDIRECTS = 5


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes
    url: str  # final URL (after redirects), including the query string


class Http(Protocol):
    def get(self, url: str, params: dict | None = None,
            headers: dict | None = None) -> HttpResult: ...


class RequestsHttp:
    """Polite GET client.

    - At most `throttle_rps` requests per second (every attempt, retry and redirect counts).
    - Connection errors, timeouts and 5xx are retried up to `retries` (3) times with exponential
      backoff (`backoff * 2**n` seconds). A final network failure raises the `requests` exception;
      a final 5xx is returned as an `HttpResult` so the caller records it as evidence.
    - Redirects are followed manually (max 5) and only to http/https; anything else raises ValueError.
    - Non-2xx statuses other than 5xx are returned, not raised: classifying them is the pipeline's job.
    """

    def __init__(self, throttle_rps: float = 1.0, timeout: float = 30.0, *,
                 retries: int = 3, backoff: float = 1.0):
        if throttle_rps <= 0:
            raise ValueError("throttle_rps must be > 0")
        self.min_interval = 1.0 / throttle_rps
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._last: float | None = None
        self._session = requests.Session()

    def get(self, url: str, params: dict | None = None,
            headers: dict | None = None) -> HttpResult:
        hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
        for _ in range(MAX_REDIRECTS + 1):
            resp = self._get_with_retries(url, params, hdrs)
            if not resp.is_redirect:
                return HttpResult(status=resp.status_code, body=resp.content, url=resp.url)
            url = urljoin(resp.url, resp.headers["Location"])
            if urlsplit(url).scheme not in ("http", "https"):
                raise ValueError(f"refusing redirect to non-http(s) URL: {url!r}")
            params = None  # the Location already carries its own query
        raise ValueError(f"too many redirects (>{MAX_REDIRECTS}) from {url!r}")

    def _get_with_retries(self, url, params, headers) -> requests.Response:
        for attempt in range(self.retries + 1):
            last_try = attempt == self.retries
            self._throttle()
            try:
                resp = self._session.get(url, params=params, headers=headers,
                                         timeout=self.timeout, allow_redirects=False)
            except (requests.ConnectionError, requests.Timeout):
                if last_try:
                    raise
            else:
                if resp.status_code < 500 or last_try:
                    return resp
            time.sleep(self.backoff * 2 ** attempt)
        raise AssertionError("unreachable")

    def _throttle(self) -> None:
        if self._last is not None:
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
        self._last = time.monotonic()
