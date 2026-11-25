"""Read-only installed-release proof on f0nix; never outputs proxy credentials."""
import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path("/home/joao/docker/stacks/web/images/prumo")
DATA = Path("/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3")
SERVICES = ("prumo", "prumo-ingest", "prumo-backoffice")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get(url, headers=None, body=None):
    request = Request(url, headers=headers or {}, data=body)
    try:
        response = build_opener(NoRedirect).open(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        return response.code, dict(response.headers.items()), response.read()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    inspections = json.loads(subprocess.check_output(["docker", "inspect", *SERVICES]))
    report = {"at": datetime.now(timezone.utc).isoformat(), "containers": {}, "checks": [], "completed": False, "passed": False}
    for item in inspections:
        name = item["Name"].removeprefix("/")
        report["containers"][name] = {
            "id": item["Id"], "image": item["Image"], "started": item["State"]["StartedAt"],
            "restarts": item["RestartCount"], "running": item["State"]["Running"],
            "health": item["State"].get("Health", {}).get("Status"),
        }
    report["checkout"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    report["infra_status"] = subprocess.check_output(["git", "-C", "/home/joao/docker", "status", "--porcelain"], text=True).splitlines()
    report["preexisting_infra_diff"] = {
        path: digest(subprocess.check_output(["git", "-C", "/home/joao/docker", "diff", "--", path]))
        for path in ("secrets/web.enc.env", "stacks/web/compose/prumo-backoffice.yml")
    }
    report["unrelated_infra_sha256"] = digest(subprocess.check_output(["git", "-C", "/home/joao/docker", "diff", "--binary", "HEAD", "--", ".", ":!stacks/web/images/prumo"]))
    with sqlite3.connect(DATA.resolve(strict=True).as_uri() + "?mode=ro&readonly_shm=1", uri=True) as db:
        db.execute("BEGIN")
        report["schema"] = digest(json.dumps(db.execute("SELECT name,type,sql FROM sqlite_master ORDER BY name").fetchall(), ensure_ascii=False).encode())
        report["migrations"] = [list(row) for row in db.execute("SELECT version FROM schema_migration ORDER BY version")]
        report["cms"] = {}
        for table in ("cms_document", "cms_revision", "cms_event"):
            rows = db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            report["cms"][table] = {"rows": len(rows), "sha256": digest(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode())}
        report["quick_check"] = db.execute("PRAGMA quick_check").fetchone()[0]
        report["foreign_keys"] = db.execute("PRAGMA foreign_key_check").fetchall()
    if args.verify:
        def check(label, condition):
            report["checks"].append({"check": label, "passed": bool(condition)})
            if not condition:
                args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
                raise AssertionError(label)

        check("all services running", all(c["running"] for c in report["containers"].values()))
        check("web and admin healthy", all(report["containers"][s]["health"] == "healthy" for s in ("prumo", "prumo-backoffice")))
        check("integrity and FK", report["quick_check"] == "ok" and not report["foreign_keys"])
        if args.baseline:
            before = json.loads(args.baseline.read_text())
            check("worker identity/image/start/restarts unchanged", report["containers"]["prumo-ingest"] == before["containers"]["prumo-ingest"])
            check("schema/migrations unchanged", report["schema"] == before["schema"] and report["migrations"] == before["migrations"])
            check("authored CMS/history unchanged", report["cms"] == before["cms"])
            check("all unrelated tracked infra edits preserved", report["unrelated_infra_sha256"] == before["unrelated_infra_sha256"])
            check("preexisting infra edits preserved", report["preexisting_infra_diff"] == before["preexisting_infra_diff"])
            for service in ("prumo", "prumo-backoffice"):
                check(service + " recreated", report["containers"][service]["id"] != before["containers"][service]["id"])
                logs = subprocess.check_output(["docker", "logs", "--since", report["containers"][service]["started"], service], stderr=subprocess.STDOUT, text=True)
                failures = re.findall(r"Traceback|\bERROR\b|MissingText|database unusable", logs)
                check(service + " logs free of error-class lines", not failures)
        admin_item = next(x for x in inspections if x["Name"] == "/prumo-backoffice")
        env = dict(item.split("=", 1) for item in admin_item["Config"]["Env"] if "=" in item)
        assert env.get("PRUMO_ADMIN_PROXY_SECRET"), "proxy mode must remain configured"
        headers = {"Host": "joao.date", "X-Forwarded-Prefix": "/dados/admin", "X-Prumo-Proxy-Secret": env["PRUMO_ADMIN_PROXY_SECRET"], "Remote-User": env.get("PRUMO_ADMIN_USER", "joao"), "Origin": "https://joao.date"}
        base = "http://100.118.19.6:8089"
        for route in ("/cms", "/cms/page/inicio", "/cms/page/inicio/preview", "/queue", "/series", "/derived"):
            status, response_headers, body = get(base + route, headers)
            check("trusted proxy " + route, status == 200)
            lower_headers = {k.lower(): v for k, v in response_headers.items()}
            directives = {part.split()[0]: part.split()[1:] for part in lower_headers.get("content-security-policy", "").split(";") if part.strip()}
            scripts = directives.get("script-src", directives.get("default-src", []))
            check("private strict CSP " + route, "no-store" in lower_headers.get("cache-control", "") and scripts in (["'self'"], ["'none'"]) and directives.get("frame-ancestors") == ["'none'"] and directives.get("base-uri") == ["'none'"])
            if route == "/cms/page/inicio":
                text = body.decode()
                check("new editor with local toolkit", "vendor/tabler/1.7.5/tabler.min.css" in text and "btn-primary" in text and "Guardar rascunho" in text)
        report["assets"] = {}
        for asset in ("static/css/prumo.css", "static/css/discovery.css", "static/css/admin.css", "static/js/admin.js", "static/images/prumo/favicon.svg", "static/vendor/tabler/1.7.5/tabler.min.css"):
            if asset == "static/css/discovery.css" and not (ROOT / asset).exists():
                check("pre-release checkout has no discovery asset", args.baseline is None)
                continue
            status, _, body = get(base + "/" + asset, headers)
            check("installed admin asset " + asset, status == 200 and body == (ROOT / asset).read_bytes())
            report["assets"][asset] = {"bytes": len(body), "sha256": digest(body)}
        for label, offered in (
            ("direct anonymous refused", {"Host": "joao.date"}),
            ("forged identity refused", {"Host": "joao.date", "Remote-User": headers["Remote-User"]}),
            ("non-owner refused", {**headers, "Remote-User": "not-the-owner"}),
            ("wrong proxy secret refused", {**headers, "X-Prumo-Proxy-Secret": "incorrect"}),
        ):
            check(label, get(base + "/cms", offered)[0] == 401)
        check("cross-origin form refused without write", get(base + "/cms/page/inicio/save", {**headers, "Origin": "https://invalid.example"}, b"")[0] == 403)
    report["completed"] = True
    report["passed"] = all(row["passed"] for row in report["checks"])
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({"at": report["at"], "checkout": report["checkout"], "checks": len(report["checks"]), "containers": report["containers"], "quick_check": report["quick_check"], "fk": len(report["foreign_keys"])}))


if __name__ == "__main__":
    main()
