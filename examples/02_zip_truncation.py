"""zip() silently truncates, and can swallow an element from an iterator."""

# The trap: unequal lengths drop data without a warning.
names = ["Ada", "Grace", "Linus"]
scores = [95, 88]
assert list(zip(names, scores)) == [("Ada", 95), ("Grace", 88)]  # Linus vanished

# Worse: zip pulls from the first iterator before noticing the second is empty.
numbers = iter([1, 2, 3, 4])
pairs = list(zip(numbers, ["a", "b"]))
leftover = list(numbers)
print(pairs)     # [(1, 'a'), (2, 'b')]
print(leftover)  # [4] (3 was pulled out and thrown away)
assert pairs == [(1, "a"), (2, "b")]
assert leftover == [4]

# The fix: strict=True (Python 3.10+) turns silent truncation into an error.
try:
    list(zip(names, scores, strict=True))
except ValueError as e:
    print(e)  # zip() argument 2 is shorter than argument 1
else:
    raise AssertionError("expected ValueError")
