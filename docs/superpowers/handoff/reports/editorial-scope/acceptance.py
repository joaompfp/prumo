"""Controller acceptance of the content-only scope correction on an isolated database."""
import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from backoffice.cms import Cms, CmsRefused
from ingest import cms as documents
from ingest.db import read_db_readonly

ROOT = Path(__file__).resolve().parents[5]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    correction = module("scope_correction", Path(__file__).with_name("correction.py"))
    qa = module("collection_qa", Path(__file__).parents[1] / "national-debate/acceptance.py")
    plan = json.loads((ROOT / "docs/editorial/2026-11-27-existing-sections-correction/plan.json").read_text())
    dest = sqlite3.connect(args.output)
    read_db_readonly(args.baseline, lambda db: db.conn.backup(dest))
    dest.close()
    owner = sqlite3.connect(args.output)
    owner.execute("PRAGMA journal_mode=WAL")
    owner.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
    cms = Cms(args.output, args.output)
    before = qa.fingerprint(args.output)
    checks = []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})
        assert value, name

    preflight = correction.run(cms, plan)
    check("dry-run is complete and makes no writes", preflight["completed"] and before == qa.fingerprint(args.output))
    applied = correction.run(cms, plan, apply=True)
    check("all planned corrections read back and unrelated CMS stays exact", applied["completed"])
    for entry in plan["updates"]:
        stored = cms.get("page", entry["slug"])
        assert stored is not None
        expected = documents.parse_body("page", entry["after"])
        check(entry["slug"] + ": exact revised published and draft body", stored["published"] == expected and stored["draft"] == expected)
    for entry in plan["retire"]:
        stored = cms.get("page", entry["slug"])
        assert stored is not None
        check(entry["slug"] + ": unpublished with history retained", stored["published"] is None)
    after = qa.fingerprint(args.output)
    check("every non-CMS table and schema unchanged", all(before[key] == after[key] for key in before if not key.startswith("cms_")))
    check("no documents added or deleted", before["cms_document"]["rows"] == after["cms_document"]["rows"])
    check("only six new revisions", after["cms_revision"]["rows"] - before["cms_revision"]["rows"] == len(plan["updates"]))
    check("only intended save/publish/unpublish audit events", after["cms_event"]["rows"] - before["cms_event"]["rows"] == len(plan["updates"]) * 2 + len(plan["retire"]))
    client = TestClient(create_app(str(args.output)))
    for prefix in ("", "/dados"):
        headers = {"X-Forwarded-Prefix": prefix} if prefix else {}
        index = client.get("/paginas", headers=headers)
        check(prefix + ": existing page directory works without the invented label", index.status_code == 200 and "debate nacional" not in index.text.lower())
        catalogue = client.get("/comparar", headers=headers)
        for slug in plan["preserve_charts"]:
            check(prefix + ": comparison listed " + slug, prefix + "/comparar/" + slug in catalogue.text)
            response = client.get("/comparar/" + slug, headers=headers)
            parsed = qa.PageParser(response.text)
            check(prefix + ": comparison still fully plotted " + slug, response.status_code == 200 and len(parsed.payloads) == 1 and len(parsed.payloads[0]["series"]) >= 2 and len(parsed.payloads[0]["x"]) > 1)
        for entry in plan["updates"]:
            slug = entry["slug"]
            response = client.get("/paginas/" + slug, headers=headers)
            check(prefix + ": thematic page is still discoverable " + slug, prefix + "/paginas/" + slug in index.text and response.status_code == 200)
            check(prefix + ": no orphan wrapper links " + slug, all("/paginas/" + retired["slug"] not in response.text for retired in plan["retire"]))
            theme = client.get("/temas/" + entry["after"]["section"], headers=headers)
            check(prefix + ": page stays in existing theme " + slug, prefix + "/paginas/" + slug in theme.text)
        for retired in plan["retire"]:
            check(prefix + ": retired wrapper returns 404 " + retired["slug"], client.get("/paginas/" + retired["slug"], headers=headers).status_code == 404)
    repeated = correction.run(cms, plan, apply=True)
    check("repeat makes no writes", repeated["completed"] and all(job["state"] == "preserved" for job in repeated["jobs"]) and after == qa.fingerprint(args.output))
    # A private operator edit must refuse the whole correction without additional writes.
    conflict_path = args.output.with_name(args.output.stem + "-conflict.sqlite3")
    if conflict_path.exists():
        raise FileExistsError(conflict_path)
    conflict_owner = sqlite3.connect(conflict_path)
    owner.backup(conflict_owner)
    conflict_owner.execute("PRAGMA journal_mode=WAL")
    conflict_owner.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
    conflict = Cms(conflict_path, conflict_path)
    edited = conflict.get("page", "energia-e-precos")
    assert edited is not None
    private_body = edited["draft"].model_dump(mode="json")
    private_body["title"] = "Rascunho privado do operador"
    conflict.save("page", "energia-e-precos", edited["meta"]["version"], private_body,
                  actor="joao", note="Ensaio isolado de proteção de autoria")
    private_before = qa.fingerprint(conflict_path)
    try:
        correction.run(conflict, plan, apply=True)
    except CmsRefused:
        check("private draft refuses all writes", private_before == qa.fingerprint(conflict_path))
    else:
        raise AssertionError("a private operator draft was not refused")
    conflict_owner.close()
    output = {"completed": True, "checks": checks, "before": before, "after": after, "operation": applied}
    args.receipt.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    owner.close()
    print(json.dumps({"completed": True, "checks": len(checks), "receipt": str(args.receipt)}))


if __name__ == "__main__":
    main()
