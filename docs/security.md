# Security Pitfalls: Where Hidden Complexity Becomes a CVE

[← Back to all pitfalls](../README.md)

Every pitfall in this repo is a gap between what code *looks* like it does and what it actually does. On this page, that gap is exploitable. Each entry is one of the weakness types that dominates real Python vulnerability data (see [Dependency risk](dependency-risk.md)), shown through the standard-library behavior underneath it, with the real CVEs it produced.

Counts are unique PyPI advisories published since 2023, from the [OSV](https://osv.dev) database.

## Contents

| # | Pitfall | Weakness (CWE) | PyPI advisories since 2023 | The fix |
|---|---------|----------------|---------------------------:|---------|
| 53 | [`os.path.join` discards your prefix](#53-ospathjoin-discards-your-prefix) | Path traversal (22) | 444, the most common weakness on PyPI | Resolve, then check containment |
| 54 | [`tarfile` trusted member paths](#54-tarfile-trusted-member-paths-until-python-314) | Path traversal (22) | (CVE-2007-4559, in CPython) | `filter="data"` |
| 55 | [Redirects forward credentials](#55-redirects-forward-credentials-to-another-host) | Information exposure (200) | 60 redirect-related | Strip headers across origins |
| 56 | [Regex backtracking](#56-nested-quantifiers-backtrack-exponentially) | ReDoS (1333) | 80 | Remove nested quantifiers |
| 57 | [Decompression bombs](#57-decompression-bombs) | Compressed data (409) | 31 | Cap output size |
| 58 | [Loading data runs code](#58-loading-data-can-run-code) | Deserialization (502) | 210 | Use data-only formats |
| 59 | [One key parameter, two meanings](#59-one-key-parameter-two-meanings) | Signature verification (347) | 41 | Pin the algorithm |

Entries 53–57 have runnable examples. Entries 58 and 59 are documented without examples, because demonstrating them means writing a working attack.

---

### 53. `os.path.join` Discards Your Prefix

`os.path.join(base, name)` reads like "put `name` inside `base`". But if `name` is absolute, join throws `base` away entirely, and `pathlib`'s `/` operator does the same. Relative `..` segments pass through untouched, because join never normalizes.

```python
# The Trap
upload_dir = "/srv/app/uploads"
os.path.join(upload_dir, "report.pdf")    # '/srv/app/uploads/report.pdf'
os.path.join(upload_dir, "/etc/hosts")    # '/etc/hosts'
Path(upload_dir) / "/etc/hosts"           # PosixPath('/etc/hosts')
os.path.join(upload_dir, "../config.py")  # '/srv/app/uploads/../config.py'
```

**Why:** `join` is documented string surgery on path syntax, not a security boundary. On Windows, a drive letter (`C:`) resets it too.

**The fix:** Resolve the final path and check that it's still inside the base directory:

```python
def safe_join(base, name):
    base = Path(base).resolve()
    target = (base / name).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"{name!r} escapes {base}")
    return target
```

`.resolve()` also follows symlinks, so a link planted inside the directory can't point outside it. Better still, don't use client-supplied names as paths at all: generate the filename yourself and store the original as metadata.

**In the wild:** Path traversal (CWE-22 and its variants) is the most common weakness in PyPI advisories, with 507 since 2023. It shows up in file servers, archive extraction, model and plugin loaders, and anything that turns a request parameter into a path.

[Example](../examples/53_path_join_absolute.py)

### 54. `tarfile` Trusted Member Paths Until Python 3.14

A tar archive stores its own file names, and before Python 3.14 `tarfile.extractall()` wrote them where they said, including `../../etc/cron.d/job` or `/home/user/.ssh/authorized_keys`. Extracting an archive meant letting its author choose where files go.

```python
# The Trap (Python < 3.14)
with tarfile.open("upload.tar") as tar:
    tar.extractall("dest")   # A member named "../outside.txt" lands outside dest.
```

Confusingly, `zipfile.extractall()` has always sanitized names: the same `../outside.txt` member becomes `dest/outside.txt`. Two standard-library archive modules gave opposite answers to the same question.

**Why:** Tar preserves full Unix filesystem semantics (absolute paths, links, device files, permissions) because it was designed for backups, where that's exactly what you want.

**The fix:** Always pass `filter="data"`, which rejects absolute paths, `..` escapes, links pointing outside the destination, and device files. It was added by [PEP 706](https://peps.python.org/pep-0706/) in Python 3.12, backported to 3.8.17, 3.9.17, 3.10.12 and 3.11.4, and became the default in 3.14. Passing it explicitly makes your code safe on every supported version.

**In the wild:** CVE-2007-4559 was reported in 2007 and stayed open for over 15 years, partly because changing the default would break legitimate backup tools. It was finally addressed by PEP 706 in 2023, after renewed attention to how widely `extractall()` was used on untrusted archives.

[Example](../examples/54_tarfile_extraction_filter.py)

### 55. Redirects Forward Credentials to Another Host

HTTP libraries follow redirects for you, and that's exactly the problem: the request you configured for `api.example.com` gets replayed, headers and all, to wherever the `Location` header points. Python's own `urllib.request` forwards `Authorization` and `Cookie` headers to a different host, as verified on Python 3.13 and 3.14.

```python
# The Trap
req = urllib.request.Request("https://api.example.com/data",
                             headers={"Authorization": "Bearer api-token"})
urllib.request.urlopen(req)
# A 302 to https://attacker.example/ resends "Authorization: Bearer api-token".
```

**Why:** "Follow redirects" hides a policy decision, *which* parts of the request should be resent, behind a convenience. The safe answer depends on whether the scheme, host and port changed, and older code didn't ask.

**The fix:** Use a client that strips credentials on cross-origin redirects (current `requests`, `urllib3` and `httpx` do), disable redirects for authenticated calls, or install a redirect handler that removes `Authorization`, `Cookie` and `Proxy-Authorization` when the origin changes. The example has a 15-line handler.

**In the wild:** The leading Python HTTP libraries have all fixed variations on this, one header at a time:

- `requests`: CVE-2018-18074 (`Authorization` kept on an HTTPS-to-HTTP redirect), CVE-2023-32681 (`Proxy-Authorization` leak)
- `urllib3`: CVE-2018-20060 (`Authorization`), CVE-2023-43804 (`Cookie`), CVE-2024-37891 (`Proxy-Authorization`), CVE-2026-44431 (sensitive headers in proxied redirects)

[Example](../examples/55_redirect_forwards_credentials.py)

### 56. Nested Quantifiers Backtrack Exponentially

Python's `re` engine is a backtracking matcher. A pattern such as `(a+)+$` can split a run of `a`s in exponentially many ways, and on a near-miss input it tries every split before giving up. Each extra character roughly doubles the time: in the example, 20 characters take about 50 times longer than 14. A few dozen characters can pin a CPU core for minutes.

```python
# The Trap
re.match(r"(a+)+$", "a" * 14 + "!")   # ~0.0005 s
re.match(r"(a+)+$", "a" * 20 + "!")   # ~0.03 s
re.match(r"(a+)+$", "a" * 40 + "!")   # Hours.
```

Real patterns rarely look this obvious. The usual shape is two adjacent sub-patterns that can match the same characters, such as `(\w+\s?)+`, `(.*,)*` or `^(\d+)*$`, applied to a URL, email address or header.

**The fix:** Remove the ambiguity (`a+$` matches the same strings in linear time), cap input length before matching, and on Python 3.11+ use possessive quantifiers (`a++`) or atomic groups (`(?>...)`), which never backtrack. For untrusted input at scale, the third-party `re2` bindings guarantee linear-time matching.

**In the wild:** `urllib3` (CVE-2021-33503, URLs with many `@` characters) and `idna` (CVE-2024-3651, crafted domain names) both had catastrophic backtracking in parsers that sit under almost every Python HTTP request. There were 80 ReDoS advisories on PyPI since 2023.

[Example](../examples/56_regex_backtracking.py)

### 57. Decompression Bombs

`zlib.decompress()`, `gzip.decompress()` and friends return the *whole* output, however large. Compression ratios of 1,000:1 are trivial to produce, and nesting layers takes them far higher, so a request body of a few kilobytes can allocate gigabytes.

```python
# The Trap
bomb = zlib.compress(b"\0" * 50_000_000, 9)   # 48,610 bytes
zlib.decompress(bomb)                          # 50,000,000 bytes in memory
```

**Why:** Size limits on the wire say nothing about size after decoding. Every layer that transparently decompresses (HTTP `Content-Encoding`, gzip files, zip archives, image formats) is a place where a small input becomes a large one.

**The fix:** Decompress incrementally with an output cap, using `zlib.decompressobj().decompress(data, max_length)` and checking `unconsumed_tail`, and apply limits after decoding as well as before.

**In the wild:** `urllib3` fixed decompression bombs in its streaming API three times between December 2025 and May 2026 (CVE-2025-66471, then CVE-2026-21441 for a bypass via redirects, then a further bypass). There were 31 advisories for this weakness (CWE-409) on PyPI since 2023.

[Example](../examples/57_decompression_bomb.py)

### 58. Loading Data Can Run Code

`pickle.load()` doesn't just read data. The pickle format can instruct the loader to import any importable callable and call it with arguments, which is how it rebuilds arbitrary objects. Loading a pickle from an untrusted source is equivalent to running a program from that source. The same is true of `yaml.load()` with PyYAML's full loader, `shelve`, and every machine-learning checkpoint format built on pickle, including PyTorch's `.pt` and `.pth` files and many `joblib` files.

**Why:** The interface is named `load` and returns data, but the format is a small stack-based language. Nothing in the call site tells you that.

**The fix:**

- Use formats that can only describe data: JSON, MessagePack, Protocol Buffers, or `safetensors` for model weights. Use `yaml.safe_load()`.
- If you must pickle, only load files you produced yourself, and authenticate them (for example with an HMAC over the bytes) so a swapped file is rejected before it's loaded.
- Don't rely on scanners to make untrusted pickles safe (see below).

**In the wild:** Deserialization of untrusted data (CWE-502) accounts for 210 PyPI advisories since 2023, concentrated in machine-learning tools that load models from the internet. [PyTorch 2.6 changed `torch.load`](https://dev-discuss.pytorch.org/t/bc-breaking-change-torch-load-is-being-flipped-to-use-weights-only-true-by-default-in-the-nightlies-after-137602/2573) to `weights_only=True` by default, and CVE-2025-32434 then showed that even that restricted mode could be bypassed in earlier versions. `picklescan`, a tool built to detect malicious pickles, has had 58 advisories of its own, most of them ways to get a malicious file past it undetected.

*No runnable example: demonstrating this means writing a working payload.*

### 59. One Key Parameter, Two Meanings

Token libraries often take a single `key` argument whose meaning depends on the algorithm: for HMAC it's a shared *secret*, for RSA or ECDSA it's a *public* key. If the algorithm is read from the token itself, an attacker can choose it. A token labeled with an HMAC algorithm, verified against a server's *public* key, is checked using a value the attacker already knows.

```python
# The Trap: the token decides how it gets verified.
jwt.decode(token, public_key_pem)          # Older APIs inferred the algorithm.

# The fix: the server decides.
jwt.decode(token, public_key_pem, algorithms=["RS256"])
```

**Why:** One loosely typed parameter (`str | bytes`) carries two security-critical meanings, and the choice between them is made by untrusted input. The interface is shallow in exactly the sense this repo is about: simple to call, impossible to reason about without knowing the internals.

**The fix:** Always pass an explicit allow-list of algorithms, never one taken from the token. Use typed key objects rather than raw strings where the library supports them, and keep HMAC secrets and asymmetric keys in separate code paths.

**In the wild:** PyJWT has had 23 advisories since 2023, and 15 of them involve keys or algorithms: public keys in DER form, JWK containers or whitespace-mutated PEM accepted as HMAC secrets, and empty HMAC keys accepted. That's 41 signature-verification advisories (CWE-347) across PyPI.

*No runnable example: demonstrating this means forging a token.*
