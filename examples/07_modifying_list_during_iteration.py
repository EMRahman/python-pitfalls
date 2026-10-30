"""Removing items from a list while looping over it skips elements."""

# The trap
numbers = [2, 4, 6, 8]
for n in numbers:
    if n % 2 == 0:
        numbers.remove(n)

print(numbers)  # [4, 8] ("remove every even number" left half of them behind)
assert numbers == [4, 8]

# Dicts and sets at least fail loudly.
d = {"a": 1, "b": 2}
try:
    for key in d:
        del d[key]
except RuntimeError as e:
    print(e)  # dictionary changed size during iteration
else:
    raise AssertionError("expected RuntimeError")

# The fix: build a new list (or iterate over a copy).
numbers = [2, 4, 6, 8]
numbers = [n for n in numbers if n % 2 != 0]
assert numbers == []

numbers = [2, 4, 6, 8]
for n in numbers[:]:
    if n % 2 == 0:
        numbers.remove(n)
assert numbers == []
