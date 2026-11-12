"""Receipt fetch-time validation: the ONE clock-skew policy for recorded receipts.

A receipt's `fetched_at` claims WHEN the publisher was reached. Two trust boundaries
validate it, and both share this module so the rule cannot drift between them:

- `ingest.bundle._entry_ts`  - bundle manifest load, BEFORE any DB open;
- `ingest.pipeline._receipt_ts` - the recorded-replay RawResponse at the run/write
  boundary (checked again there because the pipeline must not trust the loader for its
  own invariant).

Rule: a timezone-aware ISO-8601 datetime, normalized to UTC ISO text, and not beyond
`now + MAX_CLOCK_SKEW`. The small skew allowance covers ordinary clock drift between the
capture machine and the importer; a receipt further in the future is refused because
future-stamped data would beat every stale guard, be served as false 'freshness', and then
lock every genuine (real-time) update out until real time catches up with the fake date.
Historical receipts are accepted and normalized exactly as before.
"""

from datetime import datetime, timedelta, timezone

MAX_CLOCK_SKEW = timedelta(minutes=5)


def receipt_fetched_at(raw: object, *, now: datetime, what: str = "receipt") -> str:
    """Validate and normalize a receipt fetched_at to UTC ISO-8601 text.

    `now` is the caller's actual import-time clock (injected in tests; the real aware-UTC
    now in production via each boundary's `_utc_now()`). `what` prefixes the error with the
    calling context ("bundle entry" / "recorded receipt"). Raises ValueError on a
    non-string, non-ISO, naive, or future-beyond-skew value: a bad receipt is NEVER
    silently replaced by 'now'.
    """
    if not isinstance(raw, str):
        raise ValueError(f"{what} fetched_at must be a string, got {type(raw).__name__}")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as e:
        raise ValueError(f"{what} fetched_at is not ISO-8601: {raw!r}") from e
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{what} fetched_at must be timezone-aware: {raw!r}")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError(f"{what} clock (now) must be timezone-aware: {now!r}")
    dt = dt.astimezone(timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    if dt > now_utc + MAX_CLOCK_SKEW:
        raise ValueError(
            f"{what} fetched_at is in the future beyond the {MAX_CLOCK_SKEW} clock-skew "
            f"allowance: {dt.isoformat()} > now {now_utc.isoformat()}"
        )
    return dt.isoformat()
