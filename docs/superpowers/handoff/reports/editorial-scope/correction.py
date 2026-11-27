"""One-off correction of the unrequested editorial wrapper, through the existing CMS.

Dry-run is the default. Never edit statistical tables, chart bodies, or immutable history.
An existing private/operator draft refuses the complete plan before the first write.
"""
import argparse
import json
from pathlib import Path

from backoffice.cms import Cms, CmsRefused
from ingest import cms as documents

UPDATED = frozenset({
    "energia-e-precos", "trabalho-produtividade-investigacao", "contas-publicas-portugal",
    "credito-e-poupanca-familias", "comercio-e-industria-portugal", "demografia-portugal",
})
RETIRED = frozenset({"debate-nacional", "fontes-debate-nacional"})


def preflight(cms, plan):
    if (plan.get("version") != 1
            or {item["slug"] for item in plan["updates"]} != UPDATED
            or {item["slug"] for item in plan["retire"]} != RETIRED
            or len(plan["updates"]) != len(UPDATED) or len(plan["retire"]) != len(RETIRED)):
        raise CmsRefused("the correction must target only the approved eight pages")
    jobs = []
    for item in (*plan["updates"], *plan["retire"]):
        slug = item["slug"]
        actual = cms.get("page", slug)
        before = documents.parse_body("page", item["before"])
        after = documents.parse_body("page", item["after"]) if slug in UPDATED else None
        if actual is None:
            raise CmsRefused(f"page/{slug}: expected existing content is missing")
        assert isinstance(before, documents.PageDocument)
        assert after is None or isinstance(after, documents.PageDocument)
        if after is not None:
            if (after.section != before.section
                    or [b for b in after.blocks if isinstance(b, documents.ChartBlock)]
                    != [b for b in before.blocks if isinstance(b, documents.ChartBlock)]):
                raise CmsRefused(f"page/{slug}: sections and chart references must stay unchanged")
            if "debate nacional" in after.model_dump_json().lower():
                raise CmsRefused(f"page/{slug}: wrapper label must not survive")
        already = ((actual["published"] == after and actual["draft"] == after)
                   if after is not None else
                   (actual["published"] is None and actual["draft"] == before))
        if already:
            jobs.append({"slug": slug, "state": "preserved", "version": actual["meta"]["version"]})
            continue
        if actual["draft"] != before or actual["published"] != before:
            raise CmsRefused(f"page/{slug}: operator content or a private draft differs; refusing all changes")
        jobs.append({"slug": slug, "state": "update" if after is not None else "unpublish",
                     "version": actual["meta"]["version"]})
    # Refuse to orphan an unexpected publication which links to a retired wrapper.
    for row in cms.list("page"):
        if row["slug"] in UPDATED | RETIRED:
            continue
        actual = cms.get("page", row["slug"])
        for body in (actual["draft"], actual["published"]):
            if body is not None and any(
                    "/paginas/" + slug in body.model_dump_json() for slug in RETIRED):
                raise CmsRefused(f"page/{row['slug']}: unexpected reference needs operator review")
    return jobs


def run(cms, plan, *, apply=False, actor="operator:jarbas"):
    if apply and (cms.writable_path is None or not cms.db_path.samefile(cms.writable_path)):
        raise CmsRefused("read and restricted write mounts must identify the same database")
    if not actor.strip() or not plan["reason"].strip():
        raise CmsRefused("actor and reason are required")
    jobs = preflight(cms, plan)
    untouched = {(kind, row["slug"]): cms.get(kind, row["slug"])
                 for kind in ("page", "chart") for row in cms.list(kind)
                 if kind == "chart" or row["slug"] not in UPDATED | RETIRED}
    updates = {item["slug"]: item for item in plan["updates"]}
    receipt = {"completed": False, "apply": apply, "jobs": [], "actor": actor}
    current = None
    try:
        for job in jobs:
            current = job["slug"]
            item = dict(job)
            receipt["jobs"].append(item)
            if not apply or job["state"] == "preserved":
                continue
            if job["state"] == "update":
                saved = cms.save("page", current, job["version"], updates[current]["after"],
                                 actor=actor, note=plan["reason"])
                item["state"] = "private_draft_saved"
                published = cms.publish("page", current, saved["version"],
                                        actor=actor, note=plan["reason"])
                actual = cms.get("page", current)
                expected = documents.parse_body("page", updates[current]["after"])
                if actual["published"] != expected or actual["draft"] != expected:
                    raise CmsRefused(f"page/{current}: exact publication readback failed")
                item["state"] = "updated"
            else:
                published = cms.unpublish("page", current, job["version"],
                                          actor=actor, note=plan["reason"])
                actual = cms.get("page", current)
                if actual["published"] is not None:
                    raise CmsRefused(f"page/{current}: unpublication readback failed")
                item["state"] = "unpublished"
            action = "published" if job["state"] == "update" else "unpublished"
            if not any(e["action"] == action and e["actor"] == actor
                       and e["note"] == plan["reason"] and e["version"] == published["version"]
                       for e in actual["events"]):
                raise CmsRefused(f"page/{current}: exact audit attribution missing")
            item["version"] = published["version"]
        if not all(cms.get(*key) == value for key, value in untouched.items()):
            raise CmsRefused("an unrelated document/chart or its history changed")
        receipt["unrelated_documents_preserved"] = True
        receipt["completed"] = True
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["failed_target"] = current
        receipt["target_readback"] = cms.get("page", current)["meta"] if current else None
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--editorial-db", type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    receipt = run(Cms(args.db, args.editorial_db), json.loads(args.plan.read_text()), apply=args.apply)
    print(json.dumps(receipt, ensure_ascii=False))
    raise SystemExit(0 if receipt["completed"] else 1)


if __name__ == "__main__":
    main()
