"""Python chains every comparison operator, including `in` and `is`, not just `<` and `>`."""

# The trap: `"a" in d == True` expands to `("a" in d) and (d == True)`.
d = {"a": 1}
result = "a" in d == True  # noqa: E712
print(result)  # False
assert result is False

# Conversely, `False == False in [False]` expands to `(False == False) and (False in [False])`.
weird = False == False in [False]  # noqa: E712
print(weird)  # True (even though `(False == False) in [False]` is False)
assert weird is True
assert ((False == False) in [False]) is False

# Even `<` chains into `==`: `1 < 2 == True` is `(1 < 2) and (2 == True)`.
assert (1 < 2 == True) is False  # noqa: E712

# The fix: don't compare booleans to True/False; or add explicit parentheses when needed.
assert ("a" in d) is True
assert "a" in d
