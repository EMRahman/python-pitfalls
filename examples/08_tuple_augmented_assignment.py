"""t[i] += x on a tuple raises TypeError *after* mutating the list inside it."""

# The trap
t = (1, 2, [3, 4])

try:
    t[2] += [5, 6]
except TypeError as e:
    print(f"Error caught: {e}")
else:
    raise AssertionError("expected TypeError")

print(t)  # (1, 2, [3, 4, 5, 6]) (the list mutated anyway!)
assert t == (1, 2, [3, 4, 5, 6])

# The fix: mutate the inner list directly; no reassignment, no error.
t = (1, 2, [3, 4])
t[2].extend([5, 6])
assert t == (1, 2, [3, 4, 5, 6])
