"""urllib.parse.urljoin follows browser link rules, not path-append rules."""

from urllib.parse import urljoin, urlsplit

# Trap 1: without a trailing slash, the last segment of base is treated as a file and dropped.
base = "https://api.example.com/v1"
print(urljoin(base, "users"))  # https://api.example.com/users (/v1 vanished!)
assert urljoin(base, "users") == "https://api.example.com/users"

# Trap 2: a leading slash in the target discards the entire base path, even with a trailing slash.
assert urljoin("https://api.example.com/v1/", "/users") == "https://api.example.com/users"

# Trap 3: a scheme-relative target ("//...") replaces the host altogether.
escaped = urljoin("https://api.example.com/v1/", "//attacker.example/steal")
print(escaped)  # https://attacker.example/steal
assert escaped == "https://attacker.example/steal"


# The fix: reject targets that carry a scheme or host, normalize one slash, and check containment.
def safe_api_url(base_url, endpoint):
    target = urlsplit(endpoint)
    if target.scheme or target.netloc:
        raise ValueError(f"{endpoint!r} specifies its own origin")
    base_norm = base_url.rstrip("/") + "/"
    joined = urljoin(base_norm, endpoint.removeprefix("/"))
    b, j = urlsplit(base_norm), urlsplit(joined)
    if (b.scheme, b.netloc) != (j.scheme, j.netloc) or not j.path.startswith(b.path):
        raise ValueError(f"{endpoint!r} escapes {base_norm}")
    return joined


assert safe_api_url("https://api.example.com/v1", "users") == "https://api.example.com/v1/users"
assert safe_api_url("https://api.example.com/v1/", "/users") == "https://api.example.com/v1/users"
for bad in ["//attacker.example/steal", "https://attacker.example/x", "../admin"]:
    try:
        safe_api_url("https://api.example.com/v1", bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"expected ValueError for {bad!r}")
