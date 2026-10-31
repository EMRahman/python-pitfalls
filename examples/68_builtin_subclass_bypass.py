"""Subclassing built-in dict/list skips overridden dunder methods in C fast-paths."""

from collections import UserDict


# The trap: CPython's dict.__init__, dict.update, dict.get, dict.setdefault and {**d} call
# internal C functions directly instead of dispatching through Python's dunder methods.
class LowerKeyDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

    def __contains__(self, key):
        return super().__contains__(key.lower())


d = LowerKeyDict(Accept="text/html")     # __init__ skips __setitem__
d["X-Token"] = "secret"                  # [] calls __setitem__
d.update({"Cache-Control": "no-store"})  # .update() skips __setitem__
d.setdefault("Host", "example.com")      # .setdefault() skips __setitem__

print(list(d.keys()))  # ['Accept', 'x-token', 'Cache-Control', 'Host']
assert "Accept" not in d  # __contains__ lowercases, so 'Accept' isn't even found in its own dict!
assert d["X-TOKEN"] == "secret"  # [] calls __getitem__
assert d.get("X-TOKEN") is None  # .get() skips both __contains__ and __getitem__!


# The fix: subclass collections.UserDict (or collections.abc.MutableMapping).
class FixedLowerKeyDict(UserDict):
    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

    def __delitem__(self, key):
        super().__delitem__(key.lower())

    def __contains__(self, key):
        return super().__contains__(key.lower())


fixed = FixedLowerKeyDict(Accept="text/html")
fixed["X-Token"] = "secret"
fixed.update({"Cache-Control": "no-store"})
fixed.setdefault("Host", "example.com")
assert list(fixed.keys()) == ["accept", "x-token", "cache-control", "host"]
assert fixed.get("X-TOKEN") == "secret"
assert "ACCEPT" in fixed
