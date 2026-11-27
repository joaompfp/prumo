"""A reviewed collection is additive CMS content, not an application bootstrap."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from backoffice.cms import Cms, CmsRefused
from ingest import cms as documents
from scripts.publish_cms_collection import CollectionFailure, install
from tests.backoffice.test_cms_routes import Env

COLLECTION = Path(__file__).resolve().parents[2] / (
    "docs/editorial/debate-nacional-2026-11-27/collection.json")


def page(slug="collection-page"):
    return {"kind": "page", "slug": slug, "body": {
        "title": "Leitura de Portugal", "introduction": "", "section": "economy",
        "blocks": [{"type": "text", "text": "Contexto editorial independente dos dados."}]}}


def bundle(*entries):
    return {"version": 1, "title": "Coleção de aceitação", "documents": list(entries)}


@pytest.fixture
def cms(tmp_path):
    env = Env(tmp_path)
    return Cms(env.db_path, env.db_path)


def run(cms, data, **kwargs):
    return install(cms, data, actor="operator:test", note="Publicação deliberada", **kwargs)


def test_preflight_does_not_write(cms):
    before = hashlib.sha256(cms.db_path.read_bytes()).hexdigest()
    result = run(cms, bundle(page()))
    assert result["completed"]
    assert result["documents"][0]["status"] == "ready"
    assert cms.get("page", "collection-page") is None
    assert hashlib.sha256(cms.db_path.read_bytes()).hexdigest() == before


def test_publish_readback_and_repeat_do_not_append_history(cms):
    data = bundle(page())
    result = run(cms, data, publish=True)
    assert result["completed"]
    before = cms.get("page", "collection-page")
    assert before["meta"]["version"] == 2
    assert {event["action"] for event in before["events"]} == {"created", "published"}
    assert all(event["actor"] == "operator:test" for event in before["events"])
    assert run(cms, data, publish=True)["documents"][0]["status"] == "preserved"
    assert cms.get("page", "collection-page") == before


def test_every_collision_is_checked_before_any_creation(cms):
    occupied = page("occupied")
    cms.create("page", "occupied", occupied["body"], actor="joao", note="Rascunho meu")
    before = cms.get("page", "occupied")
    with pytest.raises(CmsRefused, match="conteúdo diferente"):
        run(cms, bundle(page(), occupied), publish=True)
    assert cms.get("page", "collection-page") is None
    assert cms.get("page", "occupied") == before


def test_changed_published_content_and_pending_draft_are_preserved(cms):
    data = bundle(page())
    run(cms, data, publish=True)
    changed = copy.deepcopy(data["documents"][0]["body"])
    changed["title"] = "Título decidido pelo operador"
    cms.save("page", "collection-page", 2, changed, actor="joao", note="Editar o meu conteúdo")
    before = cms.get("page", "collection-page")
    with pytest.raises(CmsRefused):
        run(cms, data, publish=True)
    assert cms.get("page", "collection-page") == before


def test_homepage_and_duplicate_identity_refused(cms):
    for data in (bundle(page("inicio")), bundle(page(), page())):
        with pytest.raises(CmsRefused):
            run(cms, data, publish=True)
    assert not cms.list("page")


def test_different_read_write_database_refused(cms, tmp_path):
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other = Env(other_dir)
    wrong = Cms(cms.db_path, other.db_path)
    with pytest.raises(CmsRefused, match="mesmo ficheiro"):
        run(wrong, bundle(page()), publish=True)
    assert not cms.list("page")
    assert not Cms(other.db_path, other.db_path).list("page")


def test_late_failure_is_incomplete_and_exact_draft_is_reported(cms, monkeypatch):
    original_publish = cms.publish

    def fail_second(kind, slug, *args, **kwargs):
        if slug == "second":
            raise CmsRefused("Recusa simulada após a primeira publicação")
        return original_publish(kind, slug, *args, **kwargs)

    monkeypatch.setattr(cms, "publish", fail_second)
    with pytest.raises(CollectionFailure) as error:
        run(cms, bundle(page("first"), page("second")), publish=True)
    receipt = error.value.receipt
    assert receipt["completed"] is False
    assert [row["status"] for row in receipt["documents"]] == ["published", "draft"]
    assert receipt["failed_target"] == {"kind": "page", "slug": "second"}
    assert receipt["target_readback"]["published_revision_id"] is None
    assert cms.get("page", "first")["published"] is not None
    assert cms.get("page", "second")["published"] is None


def test_chart_is_published_before_referring_page(cms):
    body = {"title": "Inflação portuguesa", "note": "Uma taxa, não um nível de preços.",
            "series_a": "ine.hicp_yoy.PT", "window": "max", "scale": "single"}
    article = page()
    article["body"]["blocks"] = [{"type": "chart", "chart_slug": "price-chart"}]
    data = bundle(article, {"kind": "chart", "slug": "price-chart", "body": body})
    result = run(cms, data, publish=True)
    assert [row["kind"] for row in result["documents"]] == ["chart", "page"]
    assert cms.preview("page", article["slug"])[1].has_charts


def test_collection_contract_complete_and_content_only():
    data = json.loads(COLLECTION.read_text())
    identities = {(entry["kind"], entry["slug"]) for entry in data["documents"]}
    assert len(identities) == len(data["documents"]) == 23
    assert sum(kind == "chart" for kind, _ in identities) == 15
    assert sum(kind == "page" for kind, _ in identities) == 8
    assert ("page", "inicio") not in identities
    for entry in data["documents"]:
        doc = documents.parse_body(entry["kind"], entry["body"])
        assert documents.shape_problem(doc) is None
        if isinstance(doc, documents.ChartDocument):
            if entry["slug"] == "euribor-tres-seis-doze-meses":
                assert all(s.endswith(".EA") for s in doc.series_ids)
            else:
                assert any(s.endswith(".PT") for s in doc.series_ids)
            assert 2 <= len(doc.series_ids) <= 6
        else:
            for block in doc.blocks:
                if isinstance(block, documents.ChartBlock):
                    assert ("chart", block.chart_slug) in identities
    raw = COLLECTION.read_text()
    assert chr(0x2014) not in raw
    assert "eletricidade-e-inflacao-portugal" not in raw
    assert "taxas-juro-credito-depositos" not in raw
