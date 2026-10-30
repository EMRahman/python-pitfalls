"""Aggregate OSV PyPI advisories into unique vulnerabilities per package."""
import glob, json, re, sys, collections

data = sys.argv[1]
norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()

recs, mal = {}, collections.Counter()
for f in glob.glob(f"{data}/osv/json/*.json"):
    r = json.load(open(f))
    if r.get("withdrawn"):
        continue
    if r["id"].startswith("MAL-"):
        for a in r.get("affected", []):
            mal[norm(a["package"]["name"])] += 1
        continue
    recs[r["id"]] = r

# Union-find over ids and aliases so PYSEC/GHSA copies of one CVE merge.
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b): parent[find(a)] = find(b)
for rid, r in recs.items():
    for a in r.get("aliases", []):
        union(rid, a)

clusters = collections.defaultdict(list)
for rid in recs:
    clusters[find(rid)].append(recs[rid])

SEV = {"LOW": 1, "MODERATE": 2, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
vulns = []
for group in clusters.values():
    pkgs, cwes, sev, published, ids, summary = set(), set(), 0, None, [], ""
    for r in group:
        ids.append(r["id"])
        for a in r.get("affected", []):
            if a["package"].get("ecosystem") == "PyPI":
                pkgs.add(norm(a["package"]["name"]))
        ds = r.get("database_specific") or {}
        cwes.update(ds.get("cwe_ids") or [])
        sev = max(sev, SEV.get(str(ds.get("severity", "")).upper(), 0))
        p = r.get("published", "")
        published = min(published, p) if published else p
        summary = summary or r.get("summary", "")
    cve = sorted({a for r in group for a in r.get("aliases", []) if a.startswith("CVE-")})
    vulns.append(dict(ids=sorted(ids), cves=cve, pkgs=sorted(pkgs), cwes=sorted(cwes),
                      sev=sev, published=published, summary=summary))

json.dump({"vulns": vulns, "malicious": mal}, open(f"{data}/vulns.json", "w"))
print("raw non-MAL records:", len(recs), "unique vulns:", len(vulns), "malicious pkgs:", len(mal), "MAL entries:", sum(mal.values()))
per = collections.Counter(p for v in vulns for p in v["pkgs"])
print("packages with >=1 vuln:", len(per))
print("top 25 all-time:", per.most_common(25))
