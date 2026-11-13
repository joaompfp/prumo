"""Test-only hard bounds for the OECD live phase (Task 15 verifier fix 1, review point I1/M3).

The controller's live gate requires the whole network phase to be bounded WHILE IT RUNS, not
reported after the fact. Two independent mechanisms, both test-local (the production contracts
ingest.http / ingest.verify keep no timing policy and are untouched):

- BoundedRequestsHttp: a RequestsHttp subclass whose _get_with_retries override enforces the
  physical attempt budget and wall deadline on EVERY delegated call. RequestsHttp.get
  re-enters _get_with_retries per redirect hop, so hops (and any retry attempts) count; with
  the live contract retries=0, one call is exactly one physical attempt. Each attempt's
  socket timeout is capped to min(client timeout, remaining deadline, 12.0 s) so a single
  hanging call cannot overrun the phase.
- hard_deadline: a SIGALRM wall deadline (signal.setitimer) for the pytest main thread that
  can abort even a blocking socket read that ignores nothing, then restores the previous
  SIGALRM handler AND the previously armed timer exactly as found, so it composes with any
  other alarm user of the process.

rolling_start_month is the live test's window arithmetic: month-index based subtraction that
survives the December -> January -> February rollover (review point M3).
"""
import signal
import threading
import time
from contextlib import contextmanager
from datetime import date

from ingest.http import RequestsHttp

__all__ = ["BoundedRequestsHttp", "LiveBoundExceeded", "hard_deadline", "rolling_start_month"]


class LiveBoundExceeded(RuntimeError):
    """The live phase hit its attempt budget or wall deadline while it was running."""


class BoundedRequestsHttp(RequestsHttp):
    """RequestsHttp with the live bounds enforced INSIDE the network phase.

    - max_attempts physical attempts total; every _get_with_retries call counts, so redirect
      hops and retry attempts are never invisible to the budget. retries other than 0 are
      refused: the live contract is retries=0, so one call == one physical attempt.
    - deadline_s is the wall budget for the WHOLE phase (throttle pacing included): an
      attempt starting with <= 1 s left is refused, and every attempt's socket timeout is
      capped to min(client timeout, remaining, max_per_request_s) (12 s by default), so one
      blocked request can never push the phase past its deadline.
    Pair with hard_deadline in the caller to also abort a read already in flight.
    """

    def __init__(self, *args, max_attempts: int = 18, deadline_s: float = 150.0,
                 max_per_request_s: float = 12.0, **kw):
        # retries is the 3rd positional parameter of RequestsHttp.__init__; the live
        # contract is retries=0 (one _get_with_retries call per physical attempt), and a
        # retrying client would blur the attempt counter, so anything else is refused.
        if len(args) > 2 or kw.get("retries", 3) != 0:
            raise ValueError("the bounded live client requires explicit retries=0 (one "
                             "_get_with_retries call per physical attempt)")
        super().__init__(*args, **kw)
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts!r}")
        self.max_attempts = max_attempts
        self.max_per_request_s = float(max_per_request_s)
        self.attempts = 0
        self.deadline = time.monotonic() + deadline_s

    def _get_with_retries(self, url, params, headers, timeout):
        remaining = self.deadline - time.monotonic()
        if remaining <= 1.0:
            raise LiveBoundExceeded(
                f"live phase deadline exhausted ({remaining:.3f}s of wall budget left): "
                f"refusing attempt {self.attempts + 1} to {url!r}")
        self.attempts += 1
        if self.attempts > self.max_attempts:
            raise LiveBoundExceeded(
                f"live phase attempt budget {self.max_attempts} exhausted: refusing "
                f"physical attempt {self.attempts} to {url!r}")
        capped = min(timeout, remaining, self.max_per_request_s)
        return super()._get_with_retries(url, params, headers, capped)


@contextmanager
def hard_deadline(seconds: float):
    """SIGALRM wall deadline for the pytest main thread: raises LiveBoundExceeded inside the
    with-body at `seconds` even from a blocking socket read. On exit (any outcome) the
    previous SIGALRM handler and the previously armed setitimer timer are restored exactly as
    found; a foreign handler or armed timer is never clobbered or left behind."""
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("hard_deadline only delivers signals on the main thread")
    if isinstance(seconds, bool) or not seconds > 0:
        raise ValueError(f"hard_deadline seconds must be a positive number, got {seconds!r}")

    def _abort(signum, frame):
        raise LiveBoundExceeded(f"live hard deadline of {seconds}s reached "
                                "(SIGALRM aborted the network phase while it ran)")

    prev_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _abort)
    prev_timer = signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)  # disarm ours while our handler is live
        signal.signal(signal.SIGALRM, prev_handler)
        if prev_timer[0] > 0.0:
            signal.setitimer(signal.ITIMER_REAL, *prev_timer)


def rolling_start_month(today: date, months_back: int = 14) -> str:
    """Canonical YYYY-MM `months_back` months before `today`, computed on the month index
    (year * 12 + month - 1) so the December -> January -> February rollover stays exact
    (e.g. 2027-02 minus 14 months is 2025-12, never 2026-12). The live collector window
    starts 14 months back: bounded, non-stale, nothing frozen."""
    idx = today.year * 12 + (today.month - 1) - months_back
    return f"{idx // 12}-{idx % 12 + 1:02d}"
