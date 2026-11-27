"""Publish a reviewed, additive content collection through the existing CMS service.

No application routes or statistical data are created here. Default is preflight only.
Existing operator documents are never saved, restored, published or overwritten.
Each creation/publication is atomic in the CMS; the collection is not a single transaction.
An interrupted publication therefore leaves an explicit partial receipt, not a false pass.
"""
import argparse
import json
from pathlib import Path

from app import cms_reads
from backoffice.cms import Cms, CmsRefused
from ingest import cms as documents
from ingest.db import read_db_readonly


class CollectionFailure(RuntimeError):
    """A partial collection is explicit and retains the underlying failure for the operator."""

    def __init__(self, receipt: dict):
        super().__init__(receipt["error"])
        self.receipt = receipt


def preflight(cms: Cms, bundle: dict) -> tuple[dict, ...]:
    """Validate the complete set before writing, rejecting every existing draft collision."""
    if set(bundle) != {"version", "title", "documents"} or bundle["version"] != 1:
        raise CmsRefused("formato da coleção inválido")
    entries = bundle["documents"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise CmsRefused("a coleção deve ter entre um e cem documentos")
    identities = set()
    parsed = []
    for entry in entries:
        if set(entry) != {"kind", "slug", "body"}:
            raise CmsRefused("campos inesperados num documento da coleção")
        kind = documents.validate_kind(entry["kind"])
        slug = documents.validate_slug(entry["slug"])
        if (kind, slug) in identities or (kind == "page" and slug == "inicio"):
            raise CmsRefused("a coleção repete um endereço ou tenta substituir a homepage")
        identities.add((kind, slug))
        doc = documents.parse_body(kind, entry["body"])
        if problem := documents.shape_problem(doc):
            raise CmsRefused(problem)
        parsed.append((entry, doc))
    result = []
    for entry, doc in parsed:
        kind, slug = entry["kind"], entry["slug"]
        existing = cms.get(kind, slug)
        if existing is not None:
            if (existing["published"] is None or existing["draft"] != doc
                    or existing["published"] != doc):
                raise CmsRefused(f"{kind}/{slug}: já existe conteúdo diferente; nada substituído")
            result.append({**entry, "status": "preserved"})
            continue
        if kind == "chart":
            problem = read_db_readonly(
                cms.db_path, lambda db, document=doc: cms_reads.chart_problem(db, document))
            if problem:
                raise CmsRefused(f"chart/{slug}: {problem}")
        else:
            for block in doc.blocks:
                if isinstance(block, documents.ChartBlock):
                    if ("chart", block.chart_slug) not in identities:
                        chart = cms.get("chart", block.chart_slug)
                        if chart is None or chart["published"] is None:
                            raise CmsRefused(f"page/{slug}: gráfico sem publicação")
        result.append({**entry, "status": "pending"})
    # Library charts must be published before pages which refer to them.
    return tuple(sorted(result, key=lambda entry: entry["kind"] != "chart"))


def install(cms: Cms, bundle: dict, *, actor: str, note: str,
            publish: bool = False) -> dict:
    if not actor.strip() or not note.strip():
        raise CmsRefused("o ator e o motivo são obrigatórios")
    if publish and (cms.writable_path is None
                    or not cms.db_path.samefile(cms.writable_path)):
        raise CmsRefused("a leitura e a escrita devem apontar para o mesmo ficheiro da base")
    plan = preflight(cms, bundle)
    result = []
    current = None
    try:
        for entry in plan:
            kind, slug = entry["kind"], entry["slug"]
            current = {"kind": kind, "slug": slug}
            if entry["status"] == "preserved":
                result.append({**current, "status": "preserved"})
                continue
            if not publish:
                result.append({**current, "status": "ready"})
                continue
            meta = cms.create(kind, slug, entry["body"], actor=actor, note=note)
            item = {**current, "status": "draft", "version": meta["version"],
                    "draft_revision_id": meta["draft_revision_id"]}
            result.append(item)
            meta = cms.publish(kind, slug, meta["version"], actor=actor, note=note)
            # Exact post-write readback, including the stored configuration and audit actor.
            actual = cms.get(kind, slug)
            expected = documents.parse_body(kind, entry["body"])
            if (actual is None or actual["published"] != expected
                    or actual["draft"] != expected
                    or actual["meta"]["version"] != meta["version"]
                    or not any(event["action"] == "published" and event["actor"] == actor
                               and event["note"] == note for event in actual["events"])):
                raise CmsRefused(f"{kind}/{slug}: leitura após publicação não confirmou conteúdo")
            item.update({"status": "published", "version": meta["version"],
                         "published_revision_id": meta["published_revision_id"]})
    except Exception as exc:
        # No destructive retry: a created private draft needs deliberate operator review.
        # The exact target is read again because publish may have committed before a read failed.
        actual = None
        if current is not None:
            try:
                target = cms.get(current["kind"], current["slug"])
                actual = target["meta"] if target else None
            except Exception:
                actual = {"readback_failed": True}
        raise CollectionFailure({"completed": False, "mode": "publish" if publish else "preflight",
                                 "documents": result, "failed_target": current,
                                 "target_readback": actual,
                                 "error": f"{type(exc).__name__}: {exc}"}) from exc
    return {"completed": True, "mode": "publish" if publish else "preflight",
            "title": bundle["title"], "documents": result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--editorial-db", type=Path)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if args.publish and args.editorial_db is None:
        parser.error("--publish requires --editorial-db")
    bundle = json.loads(args.bundle.read_text())
    try:
        result = install(Cms(args.db, args.editorial_db), bundle, actor=args.actor,
                         note=args.note, publish=args.publish)
    except CollectionFailure as exc:
        print(json.dumps(exc.receipt, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
