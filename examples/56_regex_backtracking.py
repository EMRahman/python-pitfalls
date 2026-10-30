"""Nested quantifiers make regex matching time grow exponentially (ReDoS)."""

import re
import sys
import time


def seconds(pattern, text):
    start = time.perf_counter()
    re.match(pattern, text)
    return time.perf_counter() - start


# The trap: (a+)+ can split a run of "a"s in exponentially many ways, and tries
# every one of them before concluding the trailing "!" doesn't match.
nested = r"(a+)+$"
re.match(nested, "")  # Compile and cache first, so only matching is timed.
short = seconds(nested, "a" * 14 + "!")
longer = seconds(nested, "a" * 20 + "!")
print(f"14 chars: {short:.4f}s, 20 chars: {longer:.4f}s ({longer / short:.0f}x slower)")
assert longer > short * 8  # Theory says 64x; each extra character doubles the work.

# The fix: remove the nesting. Same language, linear time.
flat = r"a+$"
assert seconds(flat, "a" * 100_000 + "!") < 0.5
assert re.match(nested, "aaaa") and re.match(flat, "aaaa")

# Python 3.11+ also has possessive quantifiers and atomic groups, which never backtrack.
if sys.version_info >= (3, 11):
    assert seconds(r"(?>a+)+$", "a" * 100_000 + "!") < 0.5

# And bound input length before matching anything user-supplied.
