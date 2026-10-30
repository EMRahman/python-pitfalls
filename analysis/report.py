import collections, datetime as dt, glob, json, os, re, sys
d = sys.argv[1]
norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
J = json.load(open(f"{d}/joined.json")); rows = {r["pkg"]: r for r in J["rows"]}
vulns = json.load(open(f"{d}/vulns.json"))
V, MAL = vulns["vulns"], vulns["malicious"]
top = json.load(open(f"{d}/top/top30d.json"))["rows"]
top_names = [norm(r["project"]) for r in top[:1000]]
top_set = set(top_names)

hidden = [r for r in rows.values() if r["reach"] >= 10 and r["only_indirect"] / r["reach"] >= 0.5]
print("== HIDDEN LAYER: reach>=10 and >=50% of reach is indirect-only:", len(hidden))
for r in sorted(hidden, key=lambda r: -r["reach"])[:40]:
    print(f"  {r['pkg']:24} reach={r['reach']:>3} indirect%={100*r['only_indirect']/r['reach']:>3.0f} rank={r['rank']} vulns={r['vulns']} since23={r['vulns_2023']} hi/crit={r['high_crit']} yanked={r['yanked']}")

# Burstiness: share of a package's vulns published in its busiest 7-day window.
print("\n== BURSTINESS (packages with >=8 vulns since 2023, reach>=10 or rank<=1000)")
by_pkg = collections.defaultdict(list)
for v in V:
    for p in v["pkgs"]:
        if v["published"] >= "2023": by_pkg[p].append(dt.date.fromisoformat(v["published"][:10]))
for p, dates in sorted(by_pkg.items(), key=lambda kv: -len(kv[1])):
    r = rows.get(p)
    if len(dates) < 8 or not r or r["reach"] < 10: continue
    dates.sort(); best = max(sum(1 for x in dates if 0 <= (x - s).days < 7) for s in dates)
    print(f"  {p:16} since23={len(dates):>3} busiest_week={best:>3} ({100*best/len(dates):.0f}%)")

# Year trend for the hidden layer vs everything.
hid = {r["pkg"] for r in hidden}
yr_all, yr_hid = collections.Counter(), collections.Counter()
for v in V:
    y = v["published"][:4]; yr_all[y] += 1
    if hid & set(v["pkgs"]): yr_hid[y] += 1
print("\n== PER YEAR (all unique vulns / hidden-layer vulns)")
print("  ", {y: (yr_all[y], yr_hid[y]) for y in sorted(yr_all) if y >= "2018"})

# CWE mix in the hidden layer + other popular dependencies (reach>=10).
deps = {r["pkg"] for r in rows.values() if r["reach"] >= 10}
cw = collections.Counter(); n_with = 0
for v in V:
    if deps & set(v["pkgs"]) and v["published"] >= "2023":
        if v["cwes"]: n_with += 1
        cw.update(set(v["cwes"]))
print(f"\n== CWE mix, dependencies with reach>=10, since 2023 ({n_with} vulns with CWE data)")
for c, n in cw.most_common(15): print(f"  {c:10} {n}")

# Yanked releases among the top 1000 (bug proxy).
print("\n== YANKED RELEASES, top 1000 packages")
ys = []
for f in glob.glob(f"{d}/simple/*.json"):
    y = json.load(open(f)); p = norm(os.path.basename(f)[:-5])
    if p in top_set and y.get("n_versions"): ys.append((p, len(y["yanked"]), y["n_versions"], y["reasons"]))
print("  packages with >=1 yanked release:", sum(1 for x in ys if x[1]), "of", len(ys), "| total yanked:", sum(x[1] for x in ys))
for p, n, tot, reasons in sorted(ys, key=lambda x: -x[1])[:15]:
    r = rows.get(p, {}); sample = next(iter(reasons.values()), "")[:70]
    print(f"  {p:26} yanked={n:>3}/{tot:<5} reach={r.get('reach', 0):>3}  e.g. {sample!r}")

# Malicious packages: year trend and typosquat targets among the top 1000.
def dl1(a, b):
    if abs(len(a) - len(b)) > 1 or a == b: return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    if len(a) > len(b): a, b = b, a
    return any(b[:i] + b[i+1:] == a for i in range(len(b)))
mal_years = collections.Counter()
for f in glob.glob(f"{d}/osv/json/MAL-*.json"):
    mal_years[json.load(open(f)).get("published", "")[:4]] += 1
targets = collections.Counter()
by_len = collections.defaultdict(list)
for t in top_names: by_len[len(t)].append(t)
squats = 0
for m in MAL:
    hits = [t for L in (len(m)-1, len(m), len(m)+1) for t in by_len.get(L, []) if dl1(m, t)]
    if hits: squats += 1; targets.update(hits)
print("\n== MALICIOUS: per year", dict(sorted(mal_years.items())))
print(f"  {len(MAL)} malicious package names; {squats} are one edit from a top-1000 name")
print("  most-targeted:", targets.most_common(15))

# Monthly trend, DoS share by population, and Scorecard by advisory status.
import statistics
monthly = collections.Counter(v["published"][:7] for v in V if v["published"] >= "2025-01")
print("\n== MONTHLY unique vulns since 2025:", dict(sorted(monthly.items())))
print("  packages with advisories: 2025 =", len({p for v in V if v["published"][:4] == "2025" for p in v["pkgs"]}),
      "| 2026 =", len({p for v in V if v["published"][:4] == "2026" for p in v["pkgs"]}))
DOS = {"CWE-400", "CWE-770", "CWE-1333", "CWE-407", "CWE-409", "CWE-835", "CWE-674", "CWE-1050", "CWE-834", "CWE-789", "CWE-776"}
for label, pop in [("dependencies (reach>=10)", deps), ("hidden layer", hid), ("all PyPI", None)]:
    vs = [v for v in V if v["published"] >= "2023" and v["cwes"] and (pop is None or pop & set(v["pkgs"]))]
    dos = sum(1 for v in vs if DOS & set(v["cwes"]))
    print(f"  {label}: {len(vs)} vulns with CWE since 2023, DoS-class {dos} ({100 * dos / len(vs):.0f}%)")
sc = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{d}/scorecard/*.json")}
sc = {p: s for p, s in sc.items() if p in rows and s.get("score") is not None}
with_v = [s["score"] for p, s in sc.items() if rows[p]["vulns"]]
without = [s["score"] for p, s in sc.items() if not rows[p]["vulns"]]
print(f"\n== SCORECARD mean: with advisories {statistics.mean(with_v):.1f} (n={len(with_v)}), without {statistics.mean(without):.1f} (n={len(without)})")
