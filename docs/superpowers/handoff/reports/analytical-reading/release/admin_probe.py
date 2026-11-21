"""Read-only checks of the installed editorial authoring boundary and preview."""
import argparse
import json
import runpy
import subprocess
from html.parser import HTMLParser
from pathlib import Path

SLUGS = (
    "inflacao-e-desemprego", "euribor-e-inflacao", "credito-e-taxa",
    "taxas-juro-credito-depositos", "divida-saldo-pib-per-capita",
    "comercio-externo-pib-per-capita", "eletricidade-domestica",
    "pib-por-habitante", "divida-publica",
)


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.selects = []
        self.forms = []
        self.scripts = []
        self.links = []
        self.assets = []
        self.svgs = 0
        self.workspaces = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and "notebook-workspace" in attrs.get("class", "").split():
            self.workspaces.append(set(attrs["class"].split()))
        if tag == "select":
            self.selects.append(attrs.get("name", ""))
        if tag == "form":
            self.forms.append(attrs)
        if tag == "script":
            self.scripts.append(attrs)
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "link":
            self.assets.append(attrs.get("href", ""))
        if tag == "svg" and "chart" in attrs.get("class", "").split():
            self.svgs += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    args = parser.parse_args()
    get = runpy.run_path(str(args.probe))["get"]
    item = json.loads(subprocess.check_output(["docker", "inspect", "prumo-backoffice"]))[0]
    env = dict(value.split("=", 1) for value in item["Config"]["Env"] if "=" in value)
    headers = {"Host": "joao.date", "X-Forwarded-Prefix": "/dados/admin",
               "X-Prumo-Proxy-Secret": env["PRUMO_ADMIN_PROXY_SECRET"],
               "Remote-User": env.get("PRUMO_ADMIN_USER", "joao")}
    checks = []
    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        assert condition, name
    try:
        base = "http://100.118.19.6:8089"
        for slug in SLUGS:
            route = "/cms/chart/" + slug
            status, _, body = get(base + route, headers)
            check(slug + "-editor-200", status == 200)
            doc = Document()
            doc.feed(body.decode())
            check(slug + "-six-authoring-slots", sum(name.startswith("series_") for name in doc.selects) == 6)
            check(slug + "-six-axis-controls", sum(name.startswith("axis_") for name in doc.selects) == 6)
            check(slug + "-save-private", any(form.get("action") == "/dados/admin" + route + "/save"
                  and form.get("method", "").lower() == "post" for form in doc.forms))
            check(slug + "-publish-deliberate", any(form.get("action") == "/dados/admin" + route + "/publish"
                  and form.get("method", "").lower() == "post" for form in doc.forms))
        route = "/cms/chart/taxas-juro-credito-depositos/preview"
        status, response_headers, body = get(base + route, headers)
        check("preview-200", status == 200)
        doc = Document()
        doc.feed(body.decode())
        lower = {key.lower(): value for key, value in response_headers.items()}
        directives = {part.split()[0]: part.split()[1:] for part in lower.get("content-security-policy", "").split(";") if part.strip()}
        check("preview-private", "no-store" in lower.get("cache-control", ""))
        check("preview-no-executable-scripts", all(script.get("type") == "application/json" and not script.get("src")
              for script in doc.scripts))
        check("preview-script-csp-none", directives.get("script-src", directives.get("default-src", [])) == ["'none'"])
        check("preview-svg", doc.svgs == 1)
        check("preview-shared-analytical-layout", any({"notebook-workspace", "authored-workspace"} <= classes for classes in doc.workspaces))
        check("preview-inspector-css-admin-base", "/dados/admin/static/css/chart-inspector.css" in doc.assets)
        status, _, actual = get(base + "/static/css/chart-inspector.css", headers)
        source = Path("/home/joao/docker/stacks/web/images/prumo/static/css/chart-inspector.css").read_bytes()
        check("preview-css-exact", status == 200 and actual == source)
        check("preview-series-public-base", any(link.startswith("/dados/series/") for link in doc.links))
    finally:
        args.output.write_text(json.dumps({"checks": checks, "passed": sum(item["passed"] for item in checks)}, indent=2) + "\n")
        print(json.dumps({"passed": sum(item["passed"] for item in checks), "checks": len(checks), "editors": len(SLUGS)}))


if __name__ == "__main__":
    main()
