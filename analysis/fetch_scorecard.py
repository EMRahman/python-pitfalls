"""Fetch OpenSSF Scorecard data via deps.dev for hidden-layer packages."""
import json, os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
d = sys.argv[1]
rows = json.load(open(f"{d}/joined.json"))["rows"]
targets = [r for r in rows if r["reach"] >= 20 and r["only_indirect"] / r["reach"] >= 0.5]
q = lambda s: urllib.parse.quote(s, safe="")
def get(u):
    with urllib.request.urlopen(u, timeout=60) as r: return json.load(r)
def cached(path):
    """A cache hit only counts if it holds data; failed fetches are retried."""
    try:
        return "error" not in json.load(open(path))
    except (OSError, ValueError):
        return False

def fetch(r):
    p = r["pkg"]; out = f"{d}/scorecard/{p}.json"
    if cached(out): return
    try:
        version = json.load(open(f"{d}/deps/{p}.json"))["version"] if os.path.exists(f"{d}/deps/{p}.json") else \
            next(v["versionKey"]["version"] for v in get(f"https://api.deps.dev/v3/systems/pypi/packages/{q(p)}")["versions"] if v.get("isDefault"))
        ver = get(f"https://api.deps.dev/v3/systems/pypi/packages/{q(p)}/versions/{q(version)}")
        proj = next((x["projectKey"]["id"] for x in ver.get("relatedProjects", []) if x.get("relationType") == "SOURCE_REPO"), None)
        res = {"project": proj}
        if proj:
            pj = get(f"https://api.deps.dev/v3/projects/{q(proj)}")
            sc = pj.get("scorecard") or {}
            res.update(stars=pj.get("starsCount"), score=sc.get("overallScore"), date=sc.get("date"),
                       checks={c["name"]: c["score"] for c in sc.get("checks", [])})
        json.dump(res, open(out, "w"))
    except Exception as e:
        json.dump({"error": repr(e)}, open(out, "w"))
with ThreadPoolExecutor(4) as pool: list(pool.map(fetch, targets))
print(len(targets), "targets")
