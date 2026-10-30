"""str.strip/lstrip/rstrip remove a *set of characters*, not a substring."""

# The trap
filename = "report.txt"
print(filename.rstrip(".txt"))  # 'repor' (the final 't' of 'report' went too)
assert filename.rstrip(".txt") == "repor"
assert "https://python.org".lstrip("https://") == "ython.org"

# The fix: removeprefix/removesuffix (Python 3.9+) remove an exact substring.
assert filename.removesuffix(".txt") == "report"
assert "https://python.org".removeprefix("https://") == "python.org"
