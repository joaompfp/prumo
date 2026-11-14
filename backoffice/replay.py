"""Replay one stored verification item for an auditor (spec G6).

Delegates the decision to ingest.verify.replay_check, the same offline re-read that
`replay_item` and the tests use, with the verifier obtained through the production wiring
(ingest.operations.ensure_verifier over VERIFIER_OPS, as `python -m ingest verify` does).
Read-only by construction: the Db handle comes from read_db_readonly and the raw store is only
loaded from (RawStore.load reads and re-hashes; nothing is saved).
"""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ingest.db import Db
from ingest.models import SeriesSpec
from ingest.operations import VERIFIER_OPS, ensure_verifier
from ingest.rawstore import RawIntegrityError, RawStore
from ingest.verifiers import Verifier
from ingest.verify import replay_check

Outcome = Literal["match", "mismatch", "evidence missing", "evidence corrupt", "cannot replay"]
NO_EVIDENCE = "no evidence archived for this item"  # replay_check's own wording


def production_verifier(source_name: str) -> Verifier:
    """The registered verifier of a source, registering it on first use (KeyError if the
    source has no verifier at all)."""
    return ensure_verifier(VERIFIER_OPS[source_name])


@dataclass(frozen=True)
class ItemReplay:
    item_id: int
    source: str
    item: dict          # the stored verification_item row, verbatim
    outcome: Outcome
    reason: str | None  # why it is not a match (None for a match)


def replay(db: Db, raw_dir: Path | None, item_id: int, specs: list[SeriesSpec],
           verifier_for: Callable[[str], Verifier] = production_verifier) -> ItemReplay:
    """The stored item and what re-reading its archived evidence says now.
    KeyError if the item does not exist."""
    item = db.verification_item(item_id)
    source = db.verification_item_source(item_id)

    def result(outcome: Outcome, reason: str | None) -> ItemReplay:
        return ItemReplay(item_id, source, item, outcome, reason)

    if raw_dir is None:
        return result("cannot replay", "no raw store configured (PRUMO_RAW_DIR)")
    try:
        verifier = verifier_for(source)
    except (KeyError, ValueError) as e:
        return result("cannot replay", f"no usable verifier for source {source!r}: {e}")
    try:
        why = replay_check(db, RawStore(raw_dir), item_id, verifier, specs=specs)
    except RawIntegrityError as e:
        return result("evidence corrupt", str(e))
    except FileNotFoundError as e:
        return result("evidence missing", f"archived evidence file not found: {e.filename}")
    except ValueError as e:
        return result("cannot replay", str(e))
    if why is None:
        return result("match", None)
    if why == NO_EVIDENCE:
        return result("evidence missing", why)
    return result("mismatch", why)
