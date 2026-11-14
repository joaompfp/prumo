"""Task 21 (B-I4): replay every stored item of a verified run through the verifier's pure
`reread` of its archived evidence, and prove a claim the evidence does not support fails."""
from ingest.verify import replay_check


def assert_replays_from_evidence(db, store, verifier, step: int = 1) -> int:
    ids = [i for (i,) in db.conn.execute(
        "SELECT id FROM verification_item WHERE match = 1 ORDER BY id").fetchall()][::step]
    assert ids, "nothing to replay"
    for item_id in ids:
        why = replay_check(db, store, item_id, verifier)
        assert why is None, (item_id, why)
    # forge the stored claim AND the expected side consistently: only re-reading the evidence
    # can notice that the verifier never saw this value
    victim = ids[0]
    db.conn.execute("UPDATE verification_item SET observed_text = '987654321', "
                    "expected_text = '987654321' WHERE id = ?", (victim,))
    why = replay_check(db, store, victim, verifier)
    assert why is not None and "disagrees with the stored claim" in why, why
    return len(ids)
