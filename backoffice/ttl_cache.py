"""A one-value in-process cache with a time-to-live (for the full status report).

build_status scans the whole database (about 3 s at production size), and every page shows
it; reusing one report for a few seconds keeps pages fast. A failure is never cached.
"""
import threading
import time
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TtlCache(Generic[T]):
    def __init__(self, ttl_s: float, monotonic: Callable[[], float] = time.monotonic):
        self._ttl = ttl_s
        self._clock = monotonic
        self._lock = threading.Lock()  # concurrent misses compute once, not N times
        self._value: T | None = None
        self._at: float | None = None

    def get(self, compute: Callable[[], T]) -> T:
        with self._lock:
            now = self._clock()
            if self._at is None or now - self._at >= self._ttl:
                self._value = compute()
                self._at = now
            return self._value
