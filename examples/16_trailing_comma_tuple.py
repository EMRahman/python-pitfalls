"""A trailing comma turns a value into a one-element tuple."""

# The trap
timeout = 30,
print(timeout)  # (30,)
assert timeout == (30,)

try:
    timeout + 5
except TypeError as e:
    print(e)  # can only concatenate tuple (not "int") to tuple
else:
    raise AssertionError("expected TypeError")

# Parentheses don't make a tuple; the comma does.
assert (30) == 30
assert type((30,)) is tuple

# The fix: delete the comma (and let a linter catch it next time).
timeout = 30
assert timeout + 5 == 35
