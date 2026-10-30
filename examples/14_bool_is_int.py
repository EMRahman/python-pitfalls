"""True == 1 and hash(True) == hash(1), so they collide as dict keys."""

from collections import Counter

# The trap
d = {1: "one", True: "yes", 1.0: "float one"}
print(d)  # {1: 'float one'} (three keys collapsed into one)
assert d == {1: "float one"}

assert Counter([1, True, 1.0]) == Counter({1: 3})
assert {0, False} == {0}
assert True + True == 2
assert isinstance(True, int)

# The fix: if the type matters, make it part of the key.
d = {(type(k), k): v for k, v in [(1, "one"), (True, "yes"), (1.0, "float one")]}
assert len(d) == 3
