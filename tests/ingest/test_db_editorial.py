"""The composition store: version stamps, contiguous positions, one event per mutation."""

import pytest

from ingest.db import EditorialConflict, EditorialRefused

SLUG = "inicio"


def _series(db, n):
    """Real source and series rows: the slot table has a real FK, and a fake source name
    breaks the presentation catalogue in the read-path tests."""
    db.conn.execute(
        "INSERT INTO source(id, name, licence, licence_url, attribution, redistribution_ok) "
        "VALUES (1, 'INE', 'CC BY 4.0', 'https://www.ine.pt', 'INE', 1)")
    ids = []
    for i in range(n):
        sid = f"ine.series_{i}.PT"
        db.conn.execute(
            "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
            "frequency, unit, active) VALUES (?, 1, 'indicator', 'primary', 'economy', 'PT', "
            "'M', 'pct', 1)", (sid,))
        ids.append(sid)
    return ids


def _draft(db):
    return [s["series_id"] for s in db.editorial_slots(SLUG, "draft")]


def _published(db):
    return [s["series_id"] for s in db.editorial_slots(SLUG, "published")]


def _events(db):
    return db.editorial_events(SLUG, limit=100)


def test_the_first_add_creates_the_page_at_version_one(db):
    (sid,) = _series(db, 1)
    assert db.editorial_add(SLUG, sid, None, 0, "primeiro cartão") == 1
    page = db.editorial_page(SLUG)
    assert page["version"] == 1
    assert page["draft_count"] == 1
    assert page["published_count"] == 0
    assert page["published_version"] is None
    assert _draft(db) == [sid]
    assert [e["action"] for e in _events(db)] == ["slot_added"]
    assert _events(db)[0]["note"] == "primeiro cartão"


def test_positions_stay_contiguous_through_add_move_and_remove(db):
    ids = _series(db, 4)
    for position, sid in enumerate(ids):
        db.editorial_add(SLUG, sid, None, position, f"add {sid}")
    assert [s["position"] for s in db.editorial_slots(SLUG, "draft")] == [0, 1, 2, 3]

    db.editorial_move(SLUG, ids[0], 3, 4, "primeiro para o fim")
    assert _draft(db) == [ids[1], ids[2], ids[3], ids[0]]
    assert [s["position"] for s in db.editorial_slots(SLUG, "draft")] == [0, 1, 2, 3]

    db.editorial_remove(SLUG, ids[2], 5, "saiu o terceiro")
    assert _draft(db) == [ids[1], ids[3], ids[0]]
    assert [s["position"] for s in db.editorial_slots(SLUG, "draft")] == [0, 1, 2]


def test_move_to_the_middle_and_to_the_front(db):
    ids = _series(db, 3)
    version = 0
    for sid in ids:
        version = db.editorial_add(SLUG, sid, None, version, "add")
    db.editorial_move(SLUG, ids[2], 0, version, "para o início")
    assert _draft(db) == [ids[2], ids[0], ids[1]]
    db.editorial_move(SLUG, ids[2], 1, version + 1, "para o meio")
    assert _draft(db) == [ids[0], ids[2], ids[1]]


def test_a_move_to_a_position_that_does_not_exist_writes_nothing(db):
    ids = _series(db, 2)
    version = db.editorial_add(SLUG, ids[0], None, 0, "add")
    version = db.editorial_add(SLUG, ids[1], None, version, "add")
    with pytest.raises(EditorialRefused):
        db.editorial_move(SLUG, ids[0], 2, version, "fora do intervalo")
    with pytest.raises(EditorialRefused):
        db.editorial_move(SLUG, ids[0], -1, version, "negativo")
    with pytest.raises(EditorialRefused):
        db.editorial_move(SLUG, "ine.not_on_the_page.PT", 0, version, "não está")
    assert db.editorial_page(SLUG)["version"] == version
    assert _draft(db) == ids


def test_the_thirteenth_slot_is_refused_and_nothing_is_written(db):
    ids = _series(db, 13)
    version = 0
    for sid in ids[:12]:
        version = db.editorial_add(SLUG, sid, None, version, "add")
    with pytest.raises(EditorialRefused):
        db.editorial_add(SLUG, ids[12], None, version, "um a mais")
    assert db.editorial_page(SLUG)["version"] == version
    assert _draft(db) == ids[:12]
    assert len(_events(db)) == 12


def test_the_same_series_twice_is_refused(db):
    (sid,) = _series(db, 1)
    version = db.editorial_add(SLUG, sid, None, 0, "add")
    with pytest.raises(EditorialRefused):
        db.editorial_add(SLUG, sid, None, version, "outra vez")
    assert db.editorial_page(SLUG)["version"] == version


def test_a_stale_version_is_a_conflict_and_writes_nothing(db):
    (sid,) = _series(db, 1)
    db.editorial_add(SLUG, sid, None, 0, "add")
    with pytest.raises(EditorialConflict) as exc:
        db.editorial_add(SLUG, sid, None, 0, "outro separador")
    assert exc.value.slug == SLUG
    assert exc.value.expected == 0
    assert exc.value.actual == 1
    assert db.editorial_page(SLUG)["version"] == 1
    assert _draft(db) == [sid]


def test_a_stale_version_on_a_page_that_does_not_exist_is_a_conflict(db):
    (sid,) = _series(db, 1)
    with pytest.raises(EditorialConflict):
        db.editorial_add(SLUG, sid, None, 3, "nunca existiu")
    assert db.editorial_page(SLUG) is None


def test_a_mutation_without_a_note_is_refused(db):
    (sid,) = _series(db, 1)
    with pytest.raises(ValueError):
        db.editorial_add(SLUG, sid, None, 0, "  ")
    assert db.editorial_page(SLUG) is None


def test_publish_copies_the_draft_and_records_the_list(db):
    ids = _series(db, 3)
    version = 0
    for sid in ids:
        version = db.editorial_add(SLUG, sid, None, version, "add")
    version = db.editorial_publish(SLUG, version, "primeira publicação")
    page = db.editorial_page(SLUG)
    assert page["published_version"] == version
    assert page["published_at"]
    assert _published(db) == ids
    assert _draft(db) == ids  # the draft stays as it was
    published_event = _events(db)[0]
    assert published_event["action"] == "published"
    assert published_event["note"] == "primeira publicação"
    assert '"series_id"' in published_event["detail_json"]


def test_editing_the_draft_does_not_change_what_is_published(db):
    ids = _series(db, 2)
    version = db.editorial_add(SLUG, ids[0], None, 0, "add")
    version = db.editorial_publish(SLUG, version, "publica um")
    version = db.editorial_add(SLUG, ids[1], None, version, "prepara o segundo")
    assert _published(db) == [ids[0]]
    assert _draft(db) == ids


def test_publish_with_an_empty_draft_is_refused(db):
    (sid,) = _series(db, 1)
    version = db.editorial_add(SLUG, sid, None, 0, "add")
    version = db.editorial_publish(SLUG, version, "publica")
    version = db.editorial_remove(SLUG, sid, version, "retira")
    with pytest.raises(EditorialRefused):
        db.editorial_publish(SLUG, version, "publica vazio")
    assert _published(db) == [sid]
    assert _events(db)[0]["action"] == "slot_removed"


def test_discard_puts_the_published_list_back_in_the_draft(db):
    ids = _series(db, 2)
    version = db.editorial_add(SLUG, ids[0], None, 0, "add")
    version = db.editorial_publish(SLUG, version, "publica")
    version = db.editorial_add(SLUG, ids[1], None, version, "rascunho")
    version = db.editorial_discard(SLUG, version, "deita fora o rascunho")
    assert _draft(db) == [ids[0]]
    assert _events(db)[0]["action"] == "draft_discarded"


def test_discard_with_nothing_published_empties_the_draft(db):
    (sid,) = _series(db, 1)
    version = db.editorial_add(SLUG, sid, None, 0, "add")
    db.editorial_discard(SLUG, version, "nada publicado")
    assert _draft(db) == []


def test_reset_clears_the_composition_and_keeps_the_version_moving(db):
    ids = _series(db, 2)
    version = db.editorial_add(SLUG, ids[0], None, 0, "add")
    version = db.editorial_publish(SLUG, version, "publica")
    new_version = db.editorial_reset(SLUG, version, "volta à lista do código")
    assert new_version == version + 1
    page = db.editorial_page(SLUG)
    # The row stays: deleting it would restart the counter and let a stale form match a later
    # composition. Zero slots and no published state is what "back to the code list" means.
    assert page["version"] == new_version
    assert page["published_version"] is None
    assert page["published_at"] is None
    assert page["draft_count"] == 0 and page["published_count"] == 0
    assert db.editorial_slots(SLUG, "draft") == []
    assert db.editorial_slots(SLUG, "published") == []
    reset = _events(db)[0]
    assert reset["action"] == "reset_to_code"
    assert reset["detail_json"] is not None
    assert ids[0] in reset["detail_json"]


def test_reset_on_a_page_without_a_composition_is_refused(db):
    with pytest.raises(EditorialRefused):
        db.editorial_reset(SLUG, 0, "nada para apagar")


def test_each_mutation_writes_exactly_one_event(db):
    ids = _series(db, 2)
    version = db.editorial_add(SLUG, ids[0], None, 0, "add")
    version = db.editorial_add(SLUG, ids[1], None, version, "add")
    version = db.editorial_move(SLUG, ids[1], 0, version, "move")
    version = db.editorial_remove(SLUG, ids[0], version, "remove")
    version = db.editorial_publish(SLUG, version, "publica")
    version = db.editorial_discard(SLUG, version, "descarta")
    db.editorial_reset(SLUG, version, "reset")
    assert [e["action"] for e in _events(db)] == [
        "reset_to_code", "draft_discarded", "published", "slot_removed", "slot_moved",
        "slot_added", "slot_added"]


def test_a_failed_mutation_leaves_no_event_and_no_page(db, monkeypatch):
    (sid,) = _series(db, 1)

    def boom(*args, **kwargs):
        raise RuntimeError("falha a meio")

    monkeypatch.setattr(type(db), "_editorial_store", boom)
    with pytest.raises(RuntimeError):
        db.editorial_add(SLUG, sid, None, 0, "add")
    assert db.editorial_page(SLUG) is None
    assert _events(db) == []


def test_pages_lists_every_composed_page(db):
    (sid,) = _series(db, 1)
    db.editorial_add("inicio", sid, None, 0, "add")
    db.editorial_add("outra-pagina", sid, None, 0, "add")
    assert [p["slug"] for p in db.editorial_pages()] == ["inicio", "outra-pagina"]
