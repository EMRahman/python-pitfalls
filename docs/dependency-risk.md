# Dependency Risk: Which Python Packages Cause the Most Vulnerabilities and Bugs?

[← Back to all pitfalls](../README.md)

The pitfalls elsewhere in this repo are bugs you write yourself. This page is about the ones you *install*: the packages your dependencies depend on, which you never chose, rarely read and often don't know you have.

It's a data analysis rather than a list of opinions. It joins every Python vulnerability in the [OSV database](https://osv.dev) with the resolved dependency graphs of the 1,000 most-downloaded PyPI packages, PyPI's record of yanked releases, and OpenSSF Scorecard maintenance scores. The scripts and a CSV snapshot are in [`analysis/`](../analysis/), so every number can be regenerated.

*Snapshot: 30 October 2026. PyPI download rankings from 1 October 2026 (30-day window).*

## Key findings

1. **A small hidden layer carries most of the dependency risk.** `urllib3`, `certifi`, `idna`, `cryptography`, `anyio` and `pyasn1` are each pulled in by 43–177 of the top 1,000 packages, and for 70–95% of those packages the dependency is *indirect*. Weighting vulnerabilities since 2023 by how many top packages pull a library in, **`urllib3` and `cryptography` are the highest-exposure dependencies on PyPI**, ahead of `pillow` and `aiohttp`, which have far more advisories but far less reach.
2. **Dependencies fail differently from applications.** 34% of vulnerabilities in widely used dependencies are denial of service through resource exhaustion (unbounded allocation, ReDoS, decompression bombs, infinite loops, deep recursion), against 13% across PyPI. Applications fail through path traversal, XSS, SSRF and code injection instead.
3. **2026 broke every record.** PyPI saw 2,637 unique vulnerabilities by the end of October, more than three times any previous full year, spread across 725 packages (310 in 2025). Disclosures arrive in bursts: 90% of `filelock`'s recent advisories landed in one week, as did 62% of Pillow's and 61% of PyJWT's.
4. **Advisory counts measure scrutiny as much as quality.** The best-maintained hidden dependencies have the *most* advisories. The packages with none include some of the weakest maintenance signals in the graph: `six`, `python-dateutil`, `h11`, `httpcore` and `mdurl` all score 3.4–4.7 out of 10 on OpenSSF Scorecard, despite being pulled in by up to 83 top packages each.
5. **A third of top packages have shipped a release bad enough to yank.** 331 of the top 1,000 packages have yanked at least one release, 940 in total. Among dependencies, `grpcio` (segfaults and deadlocks), `multidict` (memory leaks), `yarl`, `setuptools` and `urllib3` (truncated response bodies) stand out.
6. **The biggest supply-chain threat is a name, not a bug.** OSV lists 11,942 malicious PyPI packages. 739 of them are one keystroke away from a top-1,000 package name; `requests` alone has 49 lookalikes.

---

## 1. The hidden layer

The table lists every package that at least 20 of the top 1,000 packages depend on, where more than half of those packages depend on it only indirectly (through another dependency), and that has at least one advisory. *Reach* is the number of top-1,000 packages whose resolved dependency tree includes it.

| Package | Download rank | Reach | Indirect | Vulns (all time) | Vulns in 2026 | High/critical | Scorecard |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cryptography` | 9 | 82 | 70% | 24 | 7 | 12 | 8.3 |
| `urllib3` | 5 | 145 | 86% | 22 | 6 | 12 | 8.6 |
| `pygments` | 12 | 56 | 82% | 5 | 1 | 3 | 6.2 |
| `pyasn1` | 65 | 43 | 88% | 5 | 5 | 5 | 6.6 |
| `httpx2` | 129 | 36 | 75% | 5 | 5 | 2 | – |
| `certifi` | 6 | 144 | 87% | 4 | 1 | 2 | 6.3 |
| `anyio` | 22 | 72 | 75% | 3 | 3 | 2 | 5.6 |
| `idna` | 4 | 177 | 95% | 2 | 1 | 0 | 8.5 |
| `websockets` | 68 | 24 | 75% | 2 | 0 | 2 | 5.5 |
| `markdown-it-py` | 54 | 27 | 89% | 2 | 0 | 2 | 5.3 |
| `httpcore2` | 130 | 37 | 97% | 1 | 1 | 1 | – |
| `multidict` | 47 | 23 | 83% | 1 | 1 | 0 | 7.3 |
| `h11` | 27 | 69 | 94% | 1 | 0 | 1 | 4.4 |

Notes on the leaders:

- **`cryptography`** has a recurring weakness, CWE-1395, *dependency on a vulnerable third-party component*: its wheels bundle OpenSSL, so OpenSSL advisories become `cryptography` advisories. Upgrading `cryptography` is how Python users patch OpenSSL.
- **`urllib3`** advisories cover the details of HTTP that a higher-level library such as `requests` hides from you: `Cookie`, `Authorization` and `Proxy-Authorization` headers forwarded across redirects (CWE-200), certificate and proxy TLS validation (CWE-295), and redirects that ignore configuration (CWE-601). Since late 2025 the theme has shifted to decompression bombs and unbounded buffering in the streaming API (CWE-409, CWE-770).
- **`certifi`**'s advisories are about *trust*, not code: the bundled root-certificate list included certificate authorities that were later distrusted (TrustCor, e-Tugra, GLOBALTRUST), and in 2026 roots whose intermediate keys were compromised (emSign). The fix each time was removing them.
- **`pyasn1`**, which arrives almost entirely through `pyasn1-modules` (39 of its 43 dependents), had five advisories in 2026, all high or critical and all denial of service in its BER/DER decoder: unbounded recursion, quadratic OID parsing and oversized tags.

## 2. Exposure: advisories weighted by reach

Advisory counts alone favor big, heavily audited projects. Multiplying vulnerabilities since 2023 by reach gives a rough measure of how much of the ecosystem each package's bugs touch.

| Package | Reach | Indirect | Vulns since 2023 | Of which 2026 | Exposure | Top weaknesses |
|---|---:|---:|---:|---:|---:|---|
| `urllib3` | 145 | 86% | 14 | 6 | 2,030 | Information exposure, certificate validation |
| `cryptography` | 82 | 70% | 19 | 7 | 1,558 | NULL dereference, vulnerable bundled component |
| `pillow` | 17 | 18% | 66 | 60 | 1,122 | Out-of-bounds read, resource exhaustion |
| `aiohttp` | 15 | 27% | 54 | 40 | 810 | Unbounded allocation, request smuggling |
| `requests` | 121 | 49% | 4 | 1 | 484 | Information exposure, credential leaks |
| `pyjwt` | 19 | 47% | 23 | 21 | 437 | Improper signature verification |
| `certifi` | 144 | 87% | 3 | 1 | 432 | Insufficient authenticity verification |
| `filelock` | 18 | 56% | 20 | 19 | 360 | TOCTOU races, symlink following |
| `idna` | 177 | 95% | 2 | 1 | 354 | ReDoS, resource exhaustion |
| `tornado` | 13 | 54% | 24 | 15 | 312 | Resource exhaustion, unbounded allocation |
| `anyio` | 72 | 75% | 3 | 3 | 216 | Unbounded allocation, certificate validation |
| `pyasn1` | 43 | 88% | 5 | 5 | 215 | Resource exhaustion, algorithmic complexity |

**`pillow`** is the most vulnerable *library* on PyPI: 119 advisories, 88 of them high or critical, led by memory-safety bugs in its C image decoders (out-of-bounds reads and writes) and resource exhaustion. Any service that opens user-uploaded images is parsing untrusted binary data in C.

**`pyjwt`** and **`filelock`** show how surprising the leaders can be. PyJWT's 23 recent advisories are almost all variations on one theme, a token accepted when it shouldn't be (algorithm confusion, keys accepted as HMAC secrets, empty keys). `filelock` had 18 advisories in one week of October 2026, about symlink and race-condition attacks on lock files in shared directories.

For comparison, the packages with the most advisories overall are applications and frameworks you install deliberately: TensorFlow (435), Django (162), Open WebUI (161), Apache Airflow (158), vLLM (111) and MLflow (87).

## 3. How dependencies fail: resource exhaustion

Since 2023, 312 vulnerabilities in dependencies with reach of at least 10 carry CWE weakness data. Their profile is very different from PyPI as a whole.

| Weakness | Dependencies (reach ≥ 10) | All PyPI |
|---|---:|---:|
| Denial of service by resource exhaustion (CWE-400, 770, 1333, 407, 409, 835, 674) | **34%** | 13% |
| …in the hidden layer alone | **37%** | |
| HTTP request smuggling (CWE-444) | 18 vulns | |
| Most common in all PyPI | | Path traversal (CWE-22), XSS (79), SSRF (918), deserialization (502), code injection (94) |

Libraries sit at the boundary where untrusted bytes become Python objects: URLs, HTTP headers, JSON, ASN.1, Markdown, images, compressed streams. Their characteristic bug is letting an attacker make that conversion arbitrarily expensive. A regex that backtracks for minutes, a 1 KB payload that decompresses to 10 GB, or a deeply nested structure that blows the stack. Several entries in this repo are the same failure in miniature: the 4,300-digit `int` limit ([#42](interpreter.md#42-strint-fails-above-4300-digits)) exists because converting huge integers is quadratic.

**What this means for your code:** treat input *size* as part of validation. Set maximum request body sizes, header counts and decompression ratios at your outermost layer, because the library several levels down is the most likely place for resource exhaustion to land.

## 4. The 2026 surge, and why counts mislead

Unique Python vulnerabilities by year of publication:

| 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to Oct 30) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 123 | 161 | 251 | 521 | 807 | 537 | 725 | 815 | **2,637** |

Monthly volume climbed from about 60 in mid-2025 to between 210 and 390 every month since April 2026, and the number of distinct packages receiving advisories more than doubled (310 to 725). This dataset can't say why. Faster, more automated vulnerability discovery would produce this pattern, but so would changes in disclosure practice; treat any explanation as a hypothesis.

What the data does show is **burstiness**. Packages receive advisories in batches, consistent with a single audit or researcher working through a codebase:

| Package | Advisories since 2023 | Busiest 7 days | Share |
|---|---:|---:|---:|
| `filelock` | 20 | 18 | 90% |
| `pillow` | 66 | 41 | 62% |
| `pyjwt` | 23 | 14 | 61% |
| `sqlparse` | 8 | 4 | 50% |
| `starlette` | 10 | 4 | 40% |
| `aiohttp` | 54 | 10 | 19% |
| `cryptography` | 19 | 3 | 16% |

So a package's advisory count says as much about *who has looked* as about how buggy it is. That's the background for the next finding.

## 5. The quiet ones: no advisories, weak maintenance

Of the 42 hidden-layer packages with reach of at least 20, most have **no advisories at all**. OpenSSF Scorecard (0–10, covering maintenance activity, code review, fuzzing, branch protection and similar practices) suggests that some are quiet because nobody is looking rather than because they're solid.

| Package | Reach | Indirect | Scorecard | Maintained | Code review | Stars |
|---|---:|---:|---:|---:|---:|---:|
| `mdurl` | 28 | 96% | 3.4 | 0 | 0 | 15 |
| `six` | 83 | 89% | 3.7 | 0 | 2 | 1,033 |
| `wrapt` | 36 | 53% | 3.8 | 10 | 0 | 2,313 |
| `sniffio` | 28 | 68% | 4.0 | 0 | 8 | 155 |
| `annotated-types` | 61 | 98% | 4.2 | 2 | 8 | 616 |
| `h11` | 69 | 94% | 4.4 | 0 | 5 | 571 |
| `python-dateutil` | 71 | 62% | 4.4 | 1 | 1 | 2,641 |
| `httpcore` | 33 | 100% | 4.7 | 0 | 7 | 551 |

Across the 34 hidden-layer packages that have a Scorecard, those **with** advisories average 6.6 and those **without** average 5.8. The projects that publish advisories tend to be the ones with security processes. Two caveats: a "Maintained" score of 0 only means little recent activity, which is legitimate for finished software such as `six`; and the sample is small.

`h11`, the HTTP/1.1 parser under `httpx`, `httpcore` and `uvicorn`, is the clearest case to watch: reach 69, 94% indirect, a Scorecard of 4.4, and a 2025 request-smuggling advisory in the most security-sensitive job a library can have.

## 6. Bugs: yanked releases

PyPI lets maintainers *yank* a release: it stays downloadable for exact pins but is skipped by resolvers. Maintainers yank a release when it's broken badly enough to warn everyone off, which makes yanks a measurable trace of bugs that reached users.

- **331 of the top 1,000 packages (33%) have yanked at least one release**, 940 releases in total.
- The heaviest yankers are fast-moving tools and frameworks, led by `polars` (67 yanked), `claude-agent-sdk` (25, mostly scheduled removals of old builds), `omegaconf` (19), `setuptools-scm` (18), `setuptools` (12) and `grpcio` (11).

Among widely used dependencies (reach ≥ 10), the stated reasons are revealing:

| Package | Yanked | Reach | Example reasons |
|---|---:|---:|---|
| `setuptools` | 12 of 627 | 16 | Build regressions (pypa/setuptools#2500, #2885, #3002) |
| `grpcio` | 11 of 284 | 29 | "Segfaults", "Deadlock observed in Apache Beam" |
| `multidict` | 8 of 156 | 23 | Memory leaks (aio-libs/multidict#1117, #1131) |
| `yarl` | 7 of 137 | 21 | "Cython generated files are broken", performance regression |
| `aiohttp` | 7 of 314 | 15 | Regressions, an over-tight `multidict` pin that broke resolution |
| `protobuf` | 5 of 223 | 63 | Wrong Python-version metadata, superseded release candidates |
| `tzdata` | 4 of 39 | 44 | (no reason given) |
| `urllib3` | 4 of 105 | 145 | "Truncated response bodies when streaming a large compressed body" |

Two patterns stand out. **Compiled extensions** (`grpcio`, `multidict`, `yarl`) fail in ways pure Python can't, through segfaults, leaks and broken generated code. And **packaging metadata** is a bug surface of its own: several yanks fixed version pins or Python-version claims rather than code.

## 7. Malicious packages and typosquatting

OSV's `MAL-` records track packages uploaded to PyPI with malicious intent. They aren't vulnerabilities in real libraries, so they're excluded from everything above, but they're the largest category in the database.

| 2022 | 2023 | 2024 | 2025 | 2026 (to Oct 30) |
|---:|---:|---:|---:|---:|
| 20 | 6,468 | 2,646 | 1,245 | 1,588 |

739 of the 11,942 malicious names are a single edit (one insertion, deletion, substitution or swap of adjacent letters) away from a top-1,000 package. The most impersonated: `requests` (49 lookalikes), `requests-toolbelt` (43), `colorama` (42), `websocket-client` (40), `pycodestyle` and `prompt-toolkit` (32 each), `progressbar2` (31) and `scikit-learn` (30). One mistyped `pip install` is enough.

## What to do

1. **Know your hidden layer.** Run `uv tree` or `pipdeptree` and look at what you didn't choose. The packages in sections 1 and 2 are probably in your environment.
2. **Scan continuously, including transitive dependencies.** `pip-audit` or `osv-scanner` in CI checks the whole resolved environment against the same OSV data used here. Given the 2026 volume, a weekly scan is already stale.
3. **Lock with hashes.** `uv lock`, or `pip-compile --generate-hashes` with `pip install --require-hashes`, pins every transitive dependency to an exact, verified artifact. That protects against typosquats and compromised releases, and keeps a bad release (see section 6) from arriving silently.
4. **Bound untrusted input at the edge.** Resource exhaustion is the leading dependency failure, so cap body sizes, header counts, nesting depth and decompression ratios before data reaches the parsers.
5. **Isolate the riskiest parsers.** If you process untrusted images, PDFs or archives, consider doing it in a separate worker process with memory and CPU limits.
6. **Don't read "no advisories" as "safe".** For quiet, critical dependencies, check maintenance signals (OpenSSF Scorecard, recent releases, open security issues) as well as advisories.

## Method and limitations

**Sources**

- Vulnerabilities: the full [OSV PyPI export](https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip) (26,753 records). Records sharing an identifier or alias were merged, so PYSEC and GHSA copies of one CVE count once, giving 7,032 unique vulnerabilities. Withdrawn records are excluded, and `MAL-` records are analyzed separately.
- Popularity: [hugovk/top-pypi-packages](https://hugovk.github.io/top-pypi-packages/), 30-day downloads for the top 15,000 projects.
- Dependency graphs: [deps.dev](https://deps.dev) resolved graphs for the default version of each of the top 1,000 packages. For 88 fast-releasing packages (such as `boto3` and `pydantic`), deps.dev hadn't yet resolved the newest release, so the most recent resolved release was used.
- Yanked releases: PyPI's JSON simple index ([PEP 691](https://peps.python.org/pep-0691/)).
- Maintenance: OpenSSF Scorecard via deps.dev.

**Limitations**

- *Reach* counts only packages within the top 1,000 and only default dependencies on deps.dev's resolution platform. Optional extras (`pip install pkg[extra]`), platform-specific dependencies and vendored copies (`pip` bundles its own `urllib3` and `requests`) are not counted.
- Severity comes from GitHub advisories (available for 6,534 of 7,032 vulnerabilities) and CWE data from 6,320. PYSEC-only records have neither.
- Publication dates are when an advisory was published, which can trail the fix by months or years, and GitHub sometimes imports older CVEs with new dates.
- Advisory counts reflect scrutiny and disclosure practice as well as code quality (section 4). Treat them as a measure of *known* risk.
- Yanking is a maintainer's choice, so packages that never yank aren't necessarily bug-free.
- "One edit away" typosquat matching only checks top-1,000 names and misses other tricks, such as added suffixes (`requests-secure`) or swapped separators.

To reproduce, see [`analysis/README.md`](../analysis/README.md).
