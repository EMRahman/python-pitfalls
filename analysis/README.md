# Dependency Risk Analysis

Scripts behind [docs/dependency-risk.md](../docs/dependency-risk.md). They download public data, join it, and print every number used in the report.

`dependency_risk.csv` is the joined snapshot from 30 October 2026: one row per package that at least 5 of the top 1,000 PyPI packages depend on, with reach, advisory counts, yanked releases and Scorecard.

## Reproduce

Downloaded data is untrusted, so keep it in its own directory and run the scripts from here with `python -I`. Network scripts need Python 3.11+ with working CA certificates. `fetch_yanked.py` also needs `packaging`, and `charts.py` needs `matplotlib`.

```sh
DATA=/tmp/pypi-risk-data
mkdir -p $DATA/osv $DATA/top $DATA/deps $DATA/simple $DATA/scorecard

curl -L -o $DATA/osv/all.zip https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip
unzip -q $DATA/osv/all.zip -d $DATA/osv/json
curl -L -o $DATA/top/top30d.json https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json

python -I osv_agg.py $DATA              # Merge advisories into unique vulnerabilities
python -I fetch_deps.py $DATA 1000      # Resolved dependency graphs from deps.dev
python -I fetch_yanked.py $DATA 1000    # Yanked releases from PyPI (needs packaging)
python -I analyze.py $DATA              # Reach x vulnerabilities x yanks
python -I fetch_scorecard.py $DATA      # OpenSSF Scorecard for the hidden layer
python -I report.py $DATA               # Every table in the report
python -I charts.py $DATA ../docs/img   # Light and dark SVG charts (needs matplotlib)
```

The fetch scripts cache one JSON file per package, so they can be rerun after a failure. Expect about five minutes in total. Results will drift as OSV, PyPI and deps.dev update.

| Script | Output |
|---|---|
| `osv_agg.py` | `vulns.json`: unique vulnerabilities (aliases merged) and malicious-package counts |
| `fetch_deps.py` | `deps/*.json`: resolved graph per top package, falling back to a recent release if deps.dev hasn't resolved the newest |
| `fetch_yanked.py` | `simple/*.json`: release count and yanked versions with reasons |
| `analyze.py` | `joined.json`: per-package reach, direct and indirect counts, advisories, yanks |
| `fetch_scorecard.py` | `scorecard/*.json`: Scorecard for packages with reach ≥ 20 and mostly indirect use |
| `report.py` | Prints the hidden-layer, burstiness, CWE, yanked, malicious-package, monthly and Scorecard tables |
| `charts.py` | `docs/img/*-{light,dark}.svg`: advisories per year, reach vs advisories, weakness mix. Colors are a palette validated for color-vision deficiency in both themes |
