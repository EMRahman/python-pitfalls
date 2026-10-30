"""id() values are reused once an object is freed, so they aren't unique over time."""

# The trap
print(id([]) == id([]))  # True (the second list reuses the first one's memory)
assert id([]) == id([])
assert [] is not []

# A cache keyed on id() hands back stale results for new objects.
cache = {}


def describe(obj):
    key = id(obj)
    if key not in cache:
        cache[key] = repr(obj)
    return cache[key]


describe([1, 2, 3])  # The temporary list is freed right after this call.
print(describe([4, 5, 6]))  # '[1, 2, 3]'
assert describe([4, 5, 6]) == "[1, 2, 3]"

# The fix: key on the value itself, or keep the object alive (e.g. WeakKeyDictionary).
cache = {}


def describe_fixed(obj):
    key = tuple(obj)
    if key not in cache:
        cache[key] = repr(obj)
    return cache[key]


describe_fixed([1, 2, 3])
assert describe_fixed([4, 5, 6]) == "[4, 5, 6]"
