"""for-loop variables outlive the loop and overwrite outer names."""

# The trap
i = "Safe string"
for i in range(5):
    pass

print(i)  # 4 (the original string was silently overwritten)
assert i == 4

# A loop over an empty sequence never assigns, so the old value survives.
item = "stale"
for item in []:
    pass
assert item == "stale"

# Comprehensions have their own scope in Python 3 and do not leak.
x = "outer"
squares = [x * x for x in range(3)]
assert x == "outer"

# The fix: use distinct names, or move the loop into a function.
