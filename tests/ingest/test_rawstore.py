import hashlib
import os

import pytest

from ingest.rawstore import RawIntegrityError, RawStore

BODY = b"<xml>\r\nline two\n</xml>"


def test_save_returns_sha256_and_path(tmp_path):
    store = RawStore(tmp_path)
    sha, path = store.save("ine", BODY)
    assert sha == hashlib.sha256(BODY).hexdigest()
    assert path == tmp_path / "ine" / sha[:2] / sha
    assert path.read_bytes() == BODY


def test_save_is_idempotent(tmp_path):
    store = RawStore(tmp_path)
    sha, path = store.save("ine", BODY)
    before = os.stat(path)
    assert store.save("ine", BODY) == (sha, path)
    after = os.stat(path)
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert [p.name for p in path.parent.iterdir()] == [sha]


def test_load_roundtrip_is_byte_identical(tmp_path):
    store = RawStore(tmp_path)
    _, path = store.save("ine", BODY)
    assert store.load(path) == BODY


def test_partial_write_never_visible(tmp_path, monkeypatch):
    store = RawStore(tmp_path)

    def boom(src, dst):
        raise OSError("rename failed")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        store.save("ine", BODY)
    sha = hashlib.sha256(BODY).hexdigest()
    assert not (tmp_path / "ine" / sha[:2] / sha).exists()
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


@pytest.mark.parametrize("bad", ["", ".", "..", "../x", "a/b", "a\\b"])
def test_save_rejects_path_traversal_source(tmp_path, bad):
    with pytest.raises(ValueError):
        RawStore(tmp_path / "raw").save(bad, BODY)
    assert not (tmp_path / "x").exists()


def test_load_detects_tampering(tmp_path):
    store = RawStore(tmp_path)
    _, path = store.save("ine", BODY)
    path.write_bytes(BODY + b"x")
    with pytest.raises(RawIntegrityError):
        store.load(path)


def test_load_refuses_path_outside_root(tmp_path):
    outside = tmp_path / "outside"
    outside.write_bytes(b"x")
    with pytest.raises(ValueError):
        RawStore(tmp_path / "raw").load(outside)
