"""Render the dependency-risk charts as light and dark SVGs.

Usage: python -I charts.py DATA_DIR OUT_DIR   (needs matplotlib)

Reads vulns.json and joined.json produced by osv_agg.py and analyze.py.
Colors are the validated reference palette (blue/orange pass all-pairs CVD
checks in both modes); text uses ink tokens, never series colors.
"""

import collections
import json
import sys

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.path import Path  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.transforms import IdentityTransform  # noqa: E402

data, out = sys.argv[1], sys.argv[2]

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  grid="#e1e0d9", axis="#c3c2b7", s1="#2a78d6", s2="#eb6834"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781",
                 grid="#2c2c2a", axis="#383835", s1="#3987e5", s2="#d95926"),
}
plt.rcParams.update({
    "svg.fonttype": "none",
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
})

DOS = {"CWE-400", "CWE-770", "CWE-1333", "CWE-407", "CWE-409", "CWE-835", "CWE-674",
       "CWE-1050", "CWE-834", "CWE-789", "CWE-776"}
CLASSES = [
    ("Resource exhaustion (DoS)", DOS),
    ("Information exposure", {"CWE-200", "CWE-201", "CWE-209", "CWE-532", "CWE-522", "CWE-669", "CWE-359"}),
    ("Auth & signature checks", {"CWE-287", "CWE-285", "CWE-862", "CWE-863", "CWE-347", "CWE-345",
                                 "CWE-295", "CWE-306", "CWE-639", "CWE-1390"}),
    ("Path traversal", {"CWE-22", "CWE-23", "CWE-24", "CWE-29", "CWE-36", "CWE-73"}),
    ("Code & command injection", {"CWE-94", "CWE-95", "CWE-77", "CWE-78", "CWE-89", "CWE-1336", "CWE-74", "CWE-917"}),
    ("Cross-site scripting", {"CWE-79", "CWE-80"}),
    ("Server-side request forgery", {"CWE-918"}),
    ("Unsafe deserialization", {"CWE-502"}),
    ("HTTP request smuggling", {"CWE-444"}),
]

vulns = json.load(open(f"{data}/vulns.json"))["vulns"]
rows = {r["pkg"]: r for r in json.load(open(f"{data}/joined.json"))["rows"]}
deps = {p for p, r in rows.items() if r["reach"] >= 10}


def style_axes(ax, t):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["axis"])
    ax.tick_params(colors=t["muted"], length=0, labelsize=9)


def rounded_hbar(ax, y, x0, x1, height, color, radius=3.0):
    """Horizontal bar, square at the baseline, rounded at the data end (display units)."""
    (ax0, ay0), (ax1, ay1) = ax.transData.transform([(x0, y - height / 2), (x1, y + height / 2)])
    # Sort, since an inverted axis flips display order (and would give a negative radius).
    px0, px1, py0, py1 = min(ax0, ax1), max(ax0, ax1), min(ay0, ay1), max(ay0, ay1)
    r = min(radius, (px1 - px0) / 2, (py1 - py0) / 2)
    k = 0.5523 * r  # Bezier circle approximation.
    verts = [(px0, py0), (px1 - r, py0), (px1 - r + k, py0), (px1, py0 + r - k), (px1, py0 + r),
             (px1, py1 - r), (px1, py1 - r + k), (px1 - r + k, py1), (px1 - r, py1), (px0, py1), (px0, py0)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="none", transform=IdentityTransform()))


def rounded_vbar(ax, x, y0, y1, width, color, radius=3.0):
    """Vertical bar, square at the baseline, rounded at the top."""
    (ax0, ay0), (ax1, ay1) = ax.transData.transform([(x - width / 2, y0), (x + width / 2, y1)])
    px0, px1, py0, py1 = min(ax0, ax1), max(ax0, ax1), min(ay0, ay1), max(ay0, ay1)
    r = min(radius, (px1 - px0) / 2, (py1 - py0) / 2)
    k = 0.5523 * r
    verts = [(px0, py0), (px0, py1 - r), (px0, py1 - r + k), (px0 + r - k, py1), (px0 + r, py1),
             (px1 - r, py1), (px1 - r + k, py1), (px1, py1 - r + k), (px1, py1 - r), (px1, py0), (px0, py0)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="none", transform=IdentityTransform()))


def weakness_mix(mode):
    t = THEMES[mode]
    recent = [v for v in vulns if v["published"] >= "2023" and v["cwes"]]
    pops = {"dependencies": [v for v in recent if deps & set(v["pkgs"])], "all": recent}
    share = {k: [100 * sum(1 for v in vs if cls & set(v["cwes"])) / len(vs) for _, cls in CLASSES]
             for k, vs in pops.items()}
    order = sorted(range(len(CLASSES)), key=lambda i: -share["dependencies"][i])

    fig = plt.figure(figsize=(8, 4.6), facecolor=t["surface"])
    ax = fig.add_axes([0.30, 0.10, 0.66, 0.74])
    style_axes(ax, t)
    n = len(CLASSES)
    ax.set_xlim(0, 40)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_yticks(range(n), [CLASSES[i][0] for i in order], color=t["ink2"], fontsize=9.5)
    ax.set_xticks([0, 10, 20, 30, 40], ["0%", "10%", "20%", "30%", "40%"])
    ax.grid(axis="x", color=t["grid"], linewidth=0.75)
    ax.set_axisbelow(True)
    fig.canvas.draw()
    bar = 0.30  # Two bars per band with a gap between them; each well under 24px.
    for row, i in enumerate(order):
        rounded_hbar(ax, row - bar / 2 - 0.02, 0, share["dependencies"][i], bar, t["s1"])
        rounded_hbar(ax, row + bar / 2 + 0.02, 0, share["all"][i], bar, t["s2"])
    # Selective labels: only the headline pair.
    i = order[0]
    ax.text(share["dependencies"][i] + 0.6, 0 - bar / 2 - 0.02, f"{share['dependencies'][i]:.0f}%",
            va="center", fontsize=9, color=t["ink"], fontweight="bold")
    ax.text(share["all"][i] + 0.6, 0 + bar / 2 + 0.02, f"{share['all'][i]:.0f}%", va="center", fontsize=9, color=t["ink2"])

    fig.text(0.02, 0.95, "How Python vulnerabilities fail: dependencies vs all of PyPI",
             fontsize=12.5, fontweight="bold", color=t["ink"])
    fig.text(0.02, 0.905, f"Share of advisories published since 2023 with each weakness type (CWE); an advisory can have several. "
             f"Dependencies: {len(pops['dependencies'])}; all PyPI: {len(pops['all']):,}.",
             fontsize=8.5, color=t["muted"])
    legend(fig, t, [(t["s1"], "Dependencies pulled in by ≥10 of the top 1,000 packages"), (t["s2"], "All PyPI")], y=0.035)
    fig.savefig(f"{out}/weakness-mix-{mode}.svg", facecolor=t["surface"])
    plt.close(fig)
    return {CLASSES[i][0]: (round(share["dependencies"][i], 1), round(share["all"][i], 1)) for i in order}


def legend(fig, t, items, y):
    x = 0.02
    for color, label in items:
        fig.patches.append(matplotlib.patches.FancyBboxPatch((x, y), 0.014, 0.022, boxstyle="round,pad=0,rounding_size=0.004",
                                                             transform=fig.transFigure, facecolor=color, edgecolor="none"))
        txt = fig.text(x + 0.022, y + 0.011, label, fontsize=9, color=t["ink2"], va="center")
        fig.canvas.draw()
        x = fig.transFigure.inverted().transform(txt.get_window_extent().get_points())[1][0] + 0.03


def reach_scatter(mode):
    t = THEMES[mode]
    pts = [r for r in rows.values() if r["reach"] >= 10]
    hidden = lambda r: r["only_indirect"] / r["reach"] >= 0.5

    fig = plt.figure(figsize=(8, 5.2), facecolor=t["surface"])
    ax = fig.add_axes([0.09, 0.15, 0.87, 0.68])
    style_axes(ax, t)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(t["axis"])
    ax.set_yscale("symlog", linthresh=1, linscale=0.6)
    ax.set_ylim(-0.25, 110)
    ax.set_xlim(0, 240)
    ax.set_yticks([0, 1, 10, 100], ["0", "1", "10", "100"])
    ax.grid(color=t["grid"], linewidth=0.75)
    ax.set_axisbelow(True)
    ax.set_xlabel("Reach: how many of the top 1,000 PyPI packages depend on it", color=t["ink2"], fontsize=9.5)
    ax.set_ylabel("Advisories since 2023", color=t["ink2"], fontsize=9.5)
    for group, color in ((False, t["s2"]), (True, t["s1"])):
        sel = [r for r in pts if hidden(r) == group]
        ax.scatter([r["reach"] for r in sel], [r["vulns_2023"] for r in sel], s=46, color=color,
                   edgecolors=t["surface"], linewidths=1.5, zorder=3)
    # Offsets in points; negative dx right-aligns the label to the left of its dot.
    labels = {"urllib3": (6, 4), "cryptography": (6, 4), "pillow": (6, 0), "aiohttp": (6, -4),
              "requests": (-7, 3), "pyjwt": (6, 1), "certifi": (6, -3), "idna": (6, 3), "filelock": (6, -9),
              "tornado": (-7, -2), "pyasn1": (6, 2), "anyio": (6, 2), "typing-extensions": (-6, 7),
              "charset-normalizer": (-6, 7)}
    for r in pts:
        if r["pkg"] in labels:
            dx, dy = labels[r["pkg"]]
            ax.annotate(r["pkg"], (r["reach"], r["vulns_2023"]), xytext=(dx, dy), textcoords="offset points",
                        fontsize=8.5, color=t["ink2"], ha="left" if dx > 0 else "right", va="bottom", zorder=4)
    fig.text(0.02, 0.95, "Reach vs advisories: the hidden layer sits far right", fontsize=12.5, fontweight="bold", color=t["ink"])
    fig.text(0.02, 0.905, f"{len(pts)} packages that at least 10 of the top 1,000 depend on. Vertical axis is logarithmic above 1.",
             fontsize=8.5, color=t["muted"])
    legend(fig, t, [(t["s1"], "Hidden layer: mostly pulled in indirectly"), (t["s2"], "Mostly a direct dependency")], y=0.035)
    fig.savefig(f"{out}/reach-vs-advisories-{mode}.svg", facecolor=t["surface"])
    plt.close(fig)


def per_year(mode):
    t = THEMES[mode]
    counts = collections.Counter(v["published"][:4] for v in vulns)
    years = [str(y) for y in range(2016, 2027)]
    fig = plt.figure(figsize=(8, 3.8), facecolor=t["surface"])
    ax = fig.add_axes([0.09, 0.12, 0.88, 0.68])
    style_axes(ax, t)
    ax.set_xlim(-0.6, len(years) - 0.4)
    ax.set_ylim(0, 3000)
    ax.set_xticks(range(len(years)), years)
    ax.set_yticks([0, 1000, 2000, 3000], ["0", "1,000", "2,000", "3,000"])
    ax.grid(axis="y", color=t["grid"], linewidth=0.75)
    ax.set_axisbelow(True)
    fig.canvas.draw()
    for i, y in enumerate(years):
        rounded_vbar(ax, i, 0, counts[y], 0.42, t["s1"])
    ax.text(len(years) - 1, counts["2026"] + 60, f"{counts['2026']:,}\nto 30 Oct", ha="center", va="bottom", fontsize=9, color=t["ink"], fontweight="bold")
    ax.text(len(years) - 2, counts["2025"] + 60, f"{counts['2025']:,}", ha="center", va="bottom", fontsize=9, color=t["ink2"])
    fig.text(0.02, 0.93, "Unique Python vulnerabilities published per year", fontsize=12.5, fontweight="bold", color=t["ink"])
    fig.text(0.02, 0.875, "PyPI advisories in OSV, duplicates across databases merged. 2026 is a partial year.", fontsize=8.5, color=t["muted"])
    fig.savefig(f"{out}/advisories-per-year-{mode}.svg", facecolor=t["surface"])
    plt.close(fig)
    return {y: counts[y] for y in years}


for mode in THEMES:
    mix = weakness_mix(mode)
    reach_scatter(mode)
    years = per_year(mode)
print(json.dumps({"weakness_mix": mix, "per_year": years}, indent=1))
