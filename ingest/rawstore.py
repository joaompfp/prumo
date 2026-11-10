"""Content-addressed store of unmodified source payloads.

Layout: <root>/<source>/<sha256[:2]>/<sha256>. Bytes are stored verbatim.
"""
import hashlib
import os
import tempfile
from pathlib import Path


class RawIntegrityError(Exception):
    """A stored raw file no longer matches the sha256 in its name."""


class RawStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, source: str, body: bytes) -> tuple[str, Path]:
        if source in ("", ".", "..") or "/" in source or "\\" in source or "\0" in source:
            raise ValueError(f"invalid source name: {source!r}")
        sha = hashlib.sha256(body).hexdigest()
        path = self.root / source / sha[:2] / sha
        if path.exists():
            return sha, path
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return sha, path

    def load(self, path: Path) -> bytes:
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(self.root.resolve()):
            raise ValueError(f"path outside raw store: {path}")
        body = resolved.read_bytes()
        if hashlib.sha256(body).hexdigest() != resolved.name:
            raise RawIntegrityError(f"sha256 mismatch for {path}")
        return body
