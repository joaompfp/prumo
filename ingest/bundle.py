"""Original-file bundle capture and replay infrastructure (Task 17B).

A bundle is a directory with:

    manifest.json            schema "prumo-bundle" version 1 (operator receipt: exact request
                             identities, ACTUAL statuses, ORIGINAL timezone-aware fetch times,
                             byte counts and sha256 of every recorded response)
    responses/<sha[:2]>/<sha>  exact response bodies, addressed by content, never rewritten

Capture (only from `python -m ingest capture`): a RECORDING wrapper around a bounded capture
HTTP client, driven by the full registered source/verifier flow on a throwaway scratch DB
under TMPDIR. It archives what the publisher actually answered (healthy entries AND honest
failure records) and never opens the configured real DB or raw store.

Replay (`python -m ingest run <source> --bundle DIR`): `load_bundle` validates EVERY manifest
entry and body BEFORE any DB is opened (schema/version/source/url/params/status/fetch
time/hash/byte counts, member and size caps, safe relative regular files contained under the
bundle root - no traversal, symlink or absolute paths). `PinnedHttp` then answers ONLY the
exact pinned requests and fails closed on anything else; there is NO network fallback in
recorded mode. `RecordedSource` re-drives the real source adapter against the pinned
responses and attaches each receipt's ORIGINAL fetched_at, which the pipeline validates
(ingest.pipeline._receipt_ts) and stores as raw_fetch.fetched_at / observation.fetched_at,
while run.started_at stays the actual import attempt time.

No browser automation, no auth, no uploads, no production mutation, no secrets. Supported
scope is the keyless World Bank and E-REDES channels only. Nothing here fabricates publisher
bytes, statuses or fetch dates; a user-side browser download without a genuine HTTP receipt
is never assigned an invented status by this module.
"""
import hashlib
import json
import math
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from ingest.http import MAX_REDIRECTS, HttpResult
from ingest.sources import RawResponse

SCHEMA = "prumo-bundle"
VERSION = 1

# Physical safety bounds (loads and capture). The observed genuine payloads are KB-scale
# (E-REDES ~17 KB, World Bank CSV ZIP ~300 KB); the caps leave wide headroom.
MAX_ENTRIES = 4096
MAX_ENTRY_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024

_SHA256 = set("0123456789abcdef")


class BundleError(ValueError):
    """Any bundle contract violation (capture-side or load-side). Raised before ANY database
    open or mutation: a bad bundle cannot touch state."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def request_key(url: str, params: dict | None) -> tuple:
    """The request identity an entry is pinned under: exact URL + the params as the adapter
    passed them, stringified and sorted (adapters mix int/str values; replay computes the same
    key from the same adapter call)."""
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise BundleError(f"bundle request url is not http(s): {url!r}")
    if params is not None:
        if not isinstance(params, dict) or not all(isinstance(k, str) for k in params):
            raise BundleError(f"bundle request params must be a str-keyed dict: {params!r}")
        if any(isinstance(v, (dict, list, tuple, set)) or v is None for v in params.values()):
            raise BundleError(f"bundle request params must hold scalar values: {params!r}")
    return (url, tuple(sorted((k, str(v)) for k, v in (params or {}).items())))


def _entry_ts(raw: object) -> str:
    """Validate and normalize an entry's tz-aware ISO fetched_at to UTC ISO text."""
    if not isinstance(raw, str):
        raise BundleError(f"bundle entry fetched_at must be a string, got {type(raw).__name__}")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as e:
        raise BundleError(f"bundle entry fetched_at is not ISO-8601: {raw!r}") from e
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise BundleError(f"bundle entry fetched_at must be timezone-aware: {raw!r}")
    return dt.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class BundleEntry:
    """One validated receipt: exact request identity, ACTUAL status/final URL, ORIGINAL
    fetch time, and the content address of the exact body under the bundle root."""
    url: str
    params: dict | None
    final_url: str
    status: int
    fetched_at: str  # normalized UTC ISO-8601
    sha256: str
    n_bytes: int
    file: str  # bundle-root-relative posix path

    def key(self) -> tuple:
        return request_key(self.url, self.params)


class CaptureHttp:
    """The bounded real-network client of `capture` (retries=0 by contract).

    Every PHYSICAL request - redirects included - counts against max_requests and is
    gated by the deadline BEFORE it starts, so the network budget is genuinely finite and no
    post-hoc elapsed check masquerades as a deadline. `transport` is the test seam (bounded
    fake responses, no requests dependency); the default transport is a requests Session with
    allow_redirects=False + per-request timeout, wrapped exactly once per physical request.
    """

    def __init__(self, *, timeout: float = 30.0, max_requests: int = 256,
                 deadline_s: float = 300.0, transport=None, clock=time.monotonic):
        for name, v in (("timeout", timeout), ("deadline_s", deadline_s)):
            if isinstance(v, bool) or not (math.isfinite(v) and v > 0):
                raise ValueError(f"capture {name} must be a positive finite number, got {v!r}")
        if isinstance(max_requests, bool) or not (1 <= max_requests <= 100000):
            raise ValueError(f"capture max_requests must be an integer in 1..100000, "
                             f"got {max_requests!r}")
        self.timeout, self.max_requests, self.deadline_s = timeout, max_requests, deadline_s
        self._transport = transport or self._requests_transport
        self._clock = clock
        self._start = clock()
        self.n_requests = 0
        self._session = None

    def _requests_transport(self, url, params, headers, timeout):
        import requests  # local import: the capture-only network dependency
        if self._session is None:
            self._session = requests.Session()
        from ingest.http import USER_AGENT
        resp = self._session.get(url, params=params,
                                 headers={"User-Agent": USER_AGENT, **(headers or {})},
                                 timeout=timeout, allow_redirects=False)
        return resp.status_code, resp.url, resp.content, dict(resp.headers)

    def _budget(self) -> None:
        if self.n_requests >= self.max_requests:
            raise BundleError(f"capture network budget exhausted: {self.n_requests} physical "
                              f"requests reached the cap of {self.max_requests} (redirects "
                              f"count) - refusing to spend more")
        if self._clock() - self._start > self.deadline_s:
            raise BundleError(f"capture deadline of {self.deadline_s} s exceeded before "
                              f"request {self.n_requests + 1}; the capture is abandoned, "
                              f"healthy already-recorded responses stay on disk")

    def get(self, url: str, params: dict | None = None, headers: dict | None = None,
            timeout: float | None = None) -> HttpResult:
        if timeout is not None:
            if isinstance(timeout, bool) or not (math.isfinite(timeout) and timeout > 0):
                raise ValueError(f"timeout must be a positive finite number, got {timeout!r}")
        eff = self.timeout if timeout is None else timeout
        for _ in range(MAX_REDIRECTS + 1):
            self._budget()
            self.n_requests += 1
            status, final, body, resp_headers = self._transport(url, params, headers, eff)
            if status in (301, 302, 303, 307, 308) and "Location" in resp_headers:
                from urllib.parse import urljoin, urlsplit
                url = urljoin(final, resp_headers["Location"])
                if urlsplit(url).scheme not in ("http", "https"):
                    raise ValueError(f"refusing redirect to non-http(s) URL: {url!r}")
                params = None  # the Location already carries its own query
                continue
            return HttpResult(status=status, body=body, url=final)
        raise ValueError(f"too many redirects (>{MAX_REDIRECTS}) from {url!r}")


class BundleRecorder:
    """Capture-side writer behind RecordingHttp: exact bodies to content-addressed files
    (atomic, never rewritten), duplicate-request policy, and the atomic manifest.

    Duplicate identity policy (tested): the SAME request answered twice with byte-identical
    body, status and final URL is deduplicated and keeps the FIRST recorded fetched_at (the
    pinned original timestamp is an explicit choice, never 'latest'); the same request
    answered with ANY different byte/status/final URL fails the capture loudly
    (BundleError) - no silent overwrite, ever.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        if self.root.exists() and (not self.root.is_dir() or any(self.root.iterdir())):
            raise FileExistsError(
                f"capture output {self.root} already exists and is not empty; refusing to "
                f"overwrite unseen files - choose a fresh directory")
        self.entries: list[BundleEntry] = []
        self._by_key: dict[tuple, BundleEntry] = {}
        self.failures: list[dict] = []  # honest failed-attempt receipts (no status invented)

    def _write_body(self, body: bytes) -> tuple[str, str]:
        if len(body) > MAX_ENTRY_BYTES:
            raise BundleError(f"capture response is {len(body)} bytes > per-entry cap "
                              f"{MAX_ENTRY_BYTES}")
        sha = hashlib.sha256(body).hexdigest()
        rel = PurePosixPath("responses") / sha[:2] / sha
        path = self.root / rel
        if path.exists():
            if path.read_bytes() != body:
                raise BundleError(f"content collision at {rel}: refusing to rewrite bytes")
            return sha, str(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".cap-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return sha, str(rel)

    def record(self, url: str, params: dict | None, result: HttpResult) -> None:
        """Archive one actual response. Raises BundleError on a CHANGED duplicate identity;
        byte-identical repeats are deduplicated (refetch attempts re-answer the same bytes)."""
        key = request_key(url, params)
        sha, rel = self._write_body(result.body)
        if not isinstance(result.status, int) or isinstance(result.status, bool):
            raise BundleError(f"captured status must be an int, got {result.status!r}")
        entry = BundleEntry(url=url, params={k: str(v) for k, v in params.items()}
                            if params is not None else None,
                            final_url=result.url, status=result.status,
                            fetched_at=_utc_now().isoformat(), sha256=sha,
                            n_bytes=len(result.body), file=rel)
        prev = self._by_key.get(key)
        if prev is not None:
            if (prev.sha256, prev.status, prev.final_url) == (sha, result.status, result.url):
                return  # identical duplicate: pinned to the FIRST receipt on purpose
            raise BundleError(f"capture saw a CHANGED response for an identical request "
                              f"{key!r}: {prev.sha256[:12]}/{prev.status}/{prev.final_url} vs "
                              f"{sha[:12]}/{result.status}/{result.url}; the bundle stays "
                              f"unsealed (no manifest) and cannot be mistaken for a clean one")
        self._by_key[key] = entry
        self.entries.append(entry)

    def record_failure(self, url: str, params: dict | None, error: str) -> None:
        """Archive a failed ATTEMPT honestly (operator receipt: actual error class + attempt
        time; no invented HTTP status). The loader refuses runs from unsealed bundles."""
        key = (url, tuple(sorted((str(k), str(v)) for k, v in (params or {}).items())))
        if any((f["url"], tuple(sorted((str(k), str(v))
                                      for k, v in (f.get("params") or {}).items()))) == key
               for f in self.failures):
            return  # one failure receipt per request identity is enough
        self.failures.append({"url": url, "params": params, "error": error,
                              "fetched_at": _utc_now().isoformat()})

    def seal(self, source: str) -> Path:
        """Write manifest.json atomically (the operator's receipt of the whole capture, never
        publisher bytes). Raises BundleError when the entry caps would be exceeded."""
        if len(self.entries) > MAX_ENTRIES:
            raise BundleError(f"capture holds {len(self.entries)} entries > cap {MAX_ENTRIES}")
        if sum(e.n_bytes for e in self.entries) > MAX_TOTAL_BYTES:
            raise BundleError(f"capture total bytes exceed the cap {MAX_TOTAL_BYTES}")
        doc = {"schema": SCHEMA, "version": VERSION, "source": source,
               "note": "operator receipt of an exact original-file capture; the publisher "
                       "payload bytes live under responses/ and are addressed by sha256",
               "entries": [{"url": e.url, "params": e.params, "final_url": e.final_url,
                            "status": e.status, "fetched_at": e.fetched_at,
                            "sha256": e.sha256, "bytes": e.n_bytes, "file": e.file}
                           for e in self.entries],
               "failures": self.failures}
        payload = json.dumps(doc, ensure_ascii=True, indent=1, sort_keys=True).encode("ascii")
        target = self.root / "manifest.json"
        fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".manifest-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return target


class RecordingHttp:
    """Http wrapper used by capture only: answers come from `inner` (the bounded real
    network), every response is recorded verbatim into the recorder, every raised failure is
    archived honestly and re-raised. Reading a body back from disk is never a new fetch."""

    def __init__(self, inner, recorder: BundleRecorder):
        self._inner = inner
        self._recorder = recorder

    def get(self, url, params=None, headers=None, timeout=None) -> HttpResult:
        try:
            result = self._inner.get(url, params=params, headers=headers, timeout=timeout)
        except Exception as e:
            self._recorder.record_failure(url, params, f"{type(e).__name__}: {e}")
            raise
        self._recorder.record(url, params, result)
        return result


_ENTRY_KEYS = {"url", "params", "final_url", "status", "fetched_at", "sha256", "bytes",
               "file"}
_FAILURE_KEYS = {"url", "params", "error", "fetched_at"}


def load_bundle(root: Path, *, source: str) -> "Bundle":
    """Validate the ENTIRE bundle (manifest + every referenced body) before returning a
    Bundle. Runs BEFORE any DB open/mutation by contract of the CLI call sites. Raises
    BundleError on any violation: schema/version/source mismatch, unknown entry keys, bad
    url/params/status/fetch time/hash/byte counts, entry/member/member-size caps, unsafe
    paths (traversal/absolute/symlink), missing bodies and duplicate request identities that
    disagree. Duplicate identities with identical bytes, status and final URL are folded to
    the earliest pinned receipt."""
    root = Path(root)
    if not root.is_dir():
        raise BundleError(f"bundle directory not found: {root}")
    manifest = root / "manifest.json"
    if not manifest.is_file():
        raise BundleError(f"{root} has no manifest.json; an unsealed/partial capture is not "
                          f"loadable (its healthy files stay on disk for audit)")
    try:
        doc = json.loads(manifest.read_bytes())
    except (ValueError, UnicodeDecodeError) as e:
        raise BundleError(f"bundle manifest is not valid JSON: {e}") from e
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or doc.get("version") != VERSION:
        raise BundleError(f"bundle manifest must be schema {SCHEMA!r} version {VERSION}, got "
                          f"schema={doc.get('schema')!r} version={doc.get('version')!r}")
    if set(doc) - {"schema", "version", "source", "note", "entries", "failures"}:
        raise BundleError(f"bundle manifest carries unknown keys: "
                          f"{sorted(set(doc) - {'schema', 'version', 'source', 'note', 'entries', 'failures'})}")
    if doc.get("source") != source:
        raise BundleError(f"bundle is for source {doc.get('source')!r}, not {source!r}")
    raw_entries = doc.get("entries")
    if not isinstance(raw_entries, list) or not 1 <= len(raw_entries) <= MAX_ENTRIES:
        raise BundleError(f"bundle entries must be a non-empty list of at most "
                          f"{MAX_ENTRIES}; an empty bundle pins no request at all")
    failures = doc.get("failures") or []
    if not isinstance(failures, list) or any(not isinstance(f, dict)
                                             or set(f) != _FAILURE_KEYS for f in failures):
        raise BundleError(f"bundle failures must be shape-exact receipts: {failures!r}")

    entries: list[BundleEntry] = []
    by_key: dict[tuple, BundleEntry] = {}
    total = 0
    for i, raw in enumerate(raw_entries):
        what = f"entry[{i}]"
        if not isinstance(raw, dict) or set(raw) != _ENTRY_KEYS:
            raise BundleError(f"bundle {what} keys must be exactly {sorted(_ENTRY_KEYS)}, "
                              f"got {sorted(raw) if isinstance(raw, dict) else raw!r}")
        key = request_key(raw["url"], raw["params"])
        if not isinstance(raw["final_url"], str) or not raw["final_url"]:
            raise BundleError(f"bundle {what} final_url must be a non-empty string")
        status = raw["status"]
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise BundleError(f"bundle {what} status must be an integer HTTP status, got {status!r}")
        fetched_at = _entry_ts(raw["fetched_at"])
        sha = raw["sha256"]
        if not isinstance(sha, str) or len(sha) != 64 or set(sha) - _SHA256:
            raise BundleError(f"bundle {what} sha256 must be 64 lowercase hex: {sha!r}")
        n_bytes = raw["bytes"]
        if isinstance(n_bytes, bool) or not isinstance(n_bytes, int) or n_bytes < 0:
            raise BundleError(f"bundle {what} bytes must be a non-negative int, got {n_bytes!r}")
        if n_bytes > MAX_ENTRY_BYTES:
            raise BundleError(f"bundle {what} is {n_bytes} bytes > per-entry cap {MAX_ENTRY_BYTES}")
        total += n_bytes
        if total > MAX_TOTAL_BYTES:
            raise BundleError(f"bundle total bytes exceed the cap {MAX_TOTAL_BYTES}")
        rel = raw["file"]
        if not isinstance(rel, str) or not rel:
            raise BundleError(f"bundle {what} file must be a non-empty relative path")
        p = PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts or "\\" in rel:
            raise BundleError(f"bundle {what} file is not a safe relative path: {rel!r}")
        path = root.joinpath(*p.parts)
        if path.is_symlink():
            raise BundleError(f"bundle {what} file must not be a symlink: {rel!r}")
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
            raise BundleError(f"bundle {what} file escapes the bundle root or is missing: {rel!r}")
        entry = BundleEntry(url=raw["url"], params=raw["params"],
                            final_url=raw["final_url"], status=status, fetched_at=fetched_at,
                            sha256=sha, n_bytes=n_bytes, file=str(p))
        prev = by_key.get(key)
        if prev is not None:
            if (prev.sha256, prev.status, prev.final_url) == (sha, status, raw["final_url"]):
                continue  # pinned to the FIRST receipt on purpose (explicit dedupe policy)
            raise BundleError(f"bundle pins TWO different responses for one request {key!r} "
                              f"(entries {prev.file!r} and {entry.file!r}); ambiguous bundles "
                              f"are rejected, never silently overwritten")
        by_key[key] = entry
        entries.append(entry)
    # Body integrity check AFTER all shape checks, still before returning.
    for entry in entries:
        body = (root / entry.file).read_bytes()
        if len(body) != entry.n_bytes:
            raise BundleError(f"bundle body {entry.file!r} is {len(body)} bytes, manifest "
                              f"says {entry.n_bytes}")
        if hashlib.sha256(body).hexdigest() != entry.sha256:
            raise BundleError(f"bundle body {entry.file!r} sha256 mismatch (manifest "
                              f"{entry.sha256[:12]}...) - bytes were altered after capture")
    return Bundle(root=root, source=source, entries=tuple(entries),
                  failures=tuple(json.dumps(f, sort_keys=True) for f in failures))


@dataclass(frozen=True)
class Bundle:
    """A fully validated bundle. `failures` non-empty means the capture was partial: kept
    for audit, never loadable for a run (PinnedHttp refuses it)."""
    root: Path
    source: str
    entries: tuple[BundleEntry, ...]
    failures: tuple[str, ...]

    def max_fetched_at(self) -> datetime | None:
        """NEWEST ORIGINAL receipt fetch time (parsed), or None for an empty bundle. The
        stale-bundle rule refuses a bundle only when the held verified data is STRICTLY newer
        than every receipt in it; an equal-time bundle replays idempotently (the identical-
        payload shortcut keeps it a no-op), and a genuinely newer bundle advances the data."""
        stamps = [datetime.fromisoformat(e.fetched_at) for e in self.entries]
        return max(stamps, default=None)

    def body(self, entry: BundleEntry) -> bytes:
        """Read one entry's body from disk with a fresh integrity check (a body read from
        disk is not a new HTTP fetch)."""
        data = (self.root / entry.file).read_bytes()
        if len(data) != entry.n_bytes or hashlib.sha256(data).hexdigest() != entry.sha256:
            raise BundleError(f"bundle body {entry.file!r} no longer matches its receipt "
                              f"(altered after validation) - refusing to serve it")
        return data


class PinnedHttp:
    """Read-only Http over a validated Bundle: answers ONLY exact pinned requests (url +
    params identity), any missing request fails closed; there is no network fallback, ever.
    `served` records the entry each get() answered so RecordedSource can attach the receipt's
    original fetched_at."""

    def __init__(self, bundle: Bundle):
        if bundle.failures:
            raise BundleError(f"bundle capture was partial ({len(bundle.failures)} failed "
                              f"request receipt(s)); partial bundles are audit evidence, not "
                              f"runnable input - capture a complete bundle instead")
        self.bundle = bundle
        self._by_key = {e.key(): e for e in bundle.entries}
        self.served: list[BundleEntry] = []

    def get(self, url, params=None, headers=None, timeout=None) -> HttpResult:
        entry = self._by_key.get(request_key(url, params))
        if entry is None:
            raise BundleError(f"the recorded bundle has NO response for {url!r} params "
                              f"{params!r}; recorded mode fails closed (no network fallback, "
                              f"no invented response)")
        self.served.append(entry)
        return HttpResult(status=entry.status, body=self.bundle.body(entry),
                          url=entry.final_url)


class RecordedSource:
    """Recorded Source wrapper (Task 17B): re-drives the REAL adapter (its own fetch/parse,
    unchanged) against a PinnedHttp, and attaches each served receipt's ORIGINAL fetched_at
    to the yielded RawResponse. One adapter request maps to exactly one pinned response -
    anything else means the bundle does not describe this source's request plan."""

    def __init__(self, source, pinned: PinnedHttp):
        self._source = source
        self._pinned = pinned
        self.name = source.name
        self.expected_format = getattr(source, "expected_format", None)

    def fetch(self, specs, http):  # `http` ignored on purpose: recorded mode is offline
        base = len(self._pinned.served)
        for resp in self._source.fetch(specs, self._pinned):
            n = len(self._pinned.served)
            if n != base + 1:
                raise BundleError(f"source {self.name!r} issued {n - base} requests for one "
                                  f"response; the bundle request plan must be one-to-one")
            receipt = self._pinned.served[base]
            base = n
            yield RawResponse(url=resp.url, params=resp.params, status=resp.status,
                              body=resp.body, fetched_at=receipt.fetched_at)

    def parse(self, specs, responses):
        return self._source.parse(specs, responses)
