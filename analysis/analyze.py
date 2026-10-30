"""Join vulnerabilities, dependency reach, downloads and yanked releases."""
import collections, glob, json, os, re, sys

data = sys.argv[1]
norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
top = json.load(open(f"{data}/top/top30d.json"))["rows"]
downloads = {norm(r["project"]): r["download_count"] for r in top}
rank = {norm(r["project"]): i + 1 for i, r in enumerate(top)}
roots = [norm(r["project"]) for r in top[:1000]]

# Reach: how many top-1000 packages pull each package in, directly or only indirectly.
direct, indirect, nodes_per_root = collections.defaultdict(set), collections.defaultdict(set), []
for f in glob.glob(f"{data}/deps/*.json"):
    d = json.load(open(f))
    if "graph" not in d:
        continue
    root = norm(os.path.basename(f)[:-5])
    nodes = d["graph"]["nodes"]
    nodes_per_root.append(len(nodes) - 1)
    for node in nodes:
        name = norm(node["versionKey"]["name"])
        if node["relation"] == "DIRECT":
            direct[name].add(root)
        elif node["relation"] == "INDIRECT":
            indirect[name].add(root)
reach = {p: direct[p] | indirect[p] for p in set(direct) | set(indirect)}
only_indirect = {p: reach[p] - direct[p] for p in reach}

v = json.load(open(f"{data}/vulns.json"))
vulns, malicious = v["vulns"], v["malicious"]
by_pkg = collections.defaultdict(list)
for x in vulns:
    for p in x["pkgs"]:
        by_pkg[p].append(x)

yanked = {}
for f in glob.glob(f"{data}/simple/*.json"):
    d = json.load(open(f))
    if "error" not in d:
        yanked[norm(os.path.basename(f)[:-5])] = d

def row(p):
    vs = by_pkg.get(p, [])
    recent = [x for x in vs if x["published"] >= "2023-01-01"]
    y = yanked.get(p, {})
    return dict(
        pkg=p, rank=rank.get(p), downloads=downloads.get(p, 0),
        reach=len(reach.get(p, ())), direct=len(direct.get(p, ())), only_indirect=len(only_indirect.get(p, ())),
        vulns=len(vs), vulns_2023=len(recent),
        high_crit=sum(1 for x in vs if x["sev"] >= 3),
        cwes=collections.Counter(c for x in vs for c in x["cwes"]).most_common(3),
        yanked=len(y.get("yanked", [])), versions=y.get("n_versions"),
    )

rows = [row(p) for p in reach]
json.dump({"rows": rows, "roots_with_graph": len(nodes_per_root),
           "median_deps": sorted(nodes_per_root)[len(nodes_per_root) // 2],
           "mean_deps": sum(nodes_per_root) / len(nodes_per_root)}, open(f"{data}/joined.json", "w"))

print(f"roots with graphs: {len(nodes_per_root)}, median transitive deps {sorted(nodes_per_root)[len(nodes_per_root)//2]}, mean {sum(nodes_per_root)/len(nodes_per_root):.1f}")
fmt = "{pkg:22} rank={rank!s:>5} reach={reach:>4} direct={direct:>4} only_ind={only_indirect:>4} vulns={vulns:>3} since23={vulns_2023:>3} hi/crit={high_crit:>3} yanked={yanked:>3}/{versions!s:<4} {cwes}"
print("\n== Dependencies with reach >= 10, by all-time vulns")
for r in sorted((r for r in rows if r["reach"] >= 10 and r["vulns"]), key=lambda r: -r["vulns"])[:30]:
    print(fmt.format(**r))
print("\n== Exposure (vulns since 2023 x reach), reach >= 10")
for r in sorted((r for r in rows if r["reach"] >= 10 and r["vulns_2023"]), key=lambda r: -r["vulns_2023"] * r["reach"])[:20]:
    print(fmt.format(**r), "score=", r["vulns_2023"] * r["reach"])
