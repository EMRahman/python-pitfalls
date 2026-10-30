"""Closures look up variables when called, not when defined."""

# The trap
funcs = [lambda: i for i in range(3)]
results = [f() for f in funcs]
print(results)  # [2, 2, 2]
assert results == [2, 2, 2]

# The fix: bind the current value as a default argument ...
funcs = [lambda i=i: i for i in range(3)]
assert [f() for f in funcs] == [0, 1, 2]

# ... or use functools.partial.
from functools import partial


def identity(x):
    return x


funcs = [partial(identity, i) for i in range(3)]
assert [f() for f in funcs] == [0, 1, 2]
