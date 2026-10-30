"""Count yanked releases per package using PyPI's PEP 691 JSON simple index."""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from packaging.utils import parse_sdist_filename, parse_wheel_filename, InvalidSdistFilename, InvalidWheelFilename

data, n = sys.argv[1], int(sys.argv[2])
names = [r["project"] for r in json.load(open(f"{data}/top/top30d.json"))["rows"][:n]]

def version_of(fn):
    try:
        if fn.endswith(".whl"):
            return str(parse_wheel_filename(fn)[1])
        return str(parse_sdist_filename(fn)[1])
    except (InvalidSdistFilename, InvalidWheelFilename, Exception):
        return None

def fetch(name):
    out = f"{data}/simple/{name}.json"
    if os.path.exists(out):
        return "cached"
    req = urllib.request.Request(f"https://pypi.org/simple/{name}/", headers={"Accept": "application/vnd.pypi.simple.v1+json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            idx = json.load(r)
    except Exception as e:
        json.dump({"error": repr(e)}, open(out, "w")); return "error"
    versions, yanked, reasons = set(idx.get("versions", [])), {}, {}
    for f in idx["files"]:
        v = version_of(f["filename"])
        if v and f.get("yanked"):
            yanked[v] = True
            if isinstance(f["yanked"], str):
                reasons[v] = f["yanked"]
    json.dump({"n_versions": len(versions), "yanked": sorted(yanked), "reasons": reasons}, open(out, "w"))
    return "ok"

with ThreadPoolExecutor(4) as pool:
    from collections import Counter
    print(Counter(pool.map(fetch, names)))
