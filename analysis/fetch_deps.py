"""Fetch resolved dependency graphs from deps.dev for the top-N PyPI packages."""
import json, os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

data, n = sys.argv[1], int(sys.argv[2])
rows = json.load(open(f"{data}/top/top30d.json"))["rows"][:n]
API = "https://api.deps.dev/v3/systems/pypi/packages/"

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)

def fetch(name):
    out = f"{data}/deps/{name}.json"
    if os.path.exists(out):
        return "cached"
    try:
        pkg = get(API + urllib.parse.quote(name, safe=""))
        default = [v for v in pkg["versions"] if v.get("isDefault")]
        recent = sorted((v for v in pkg["versions"] if not v.get("isDefault")), key=lambda v: v.get("publishedAt", ""), reverse=True)
        last_error = None
        # deps.dev may not have resolved the newest release yet; fall back to recent ones.
        for v in (default + recent)[:8]:
            version = v["versionKey"]["version"]
            try:
                graph = get(API + urllib.parse.quote(name, safe="") + "/versions/" + urllib.parse.quote(version, safe="") + ":dependencies")
            except Exception as e:
                last_error = e
                continue
            json.dump({"version": version, "fallback": not v.get("isDefault"), "graph": graph}, open(out, "w"))
            return "ok"
        raise last_error
    except Exception as e:
        json.dump({"error": repr(e)}, open(out, "w"))
        return "error"

with ThreadPoolExecutor(4) as pool:
    results = list(pool.map(fetch, [r["project"] for r in rows]))
from collections import Counter
print(Counter(results))
