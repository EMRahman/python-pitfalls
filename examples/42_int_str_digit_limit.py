"""Converting between int and str fails above 4300 digits (CVE-2020-10735)."""

import json
import sys

# The trap: arithmetic is unlimited, but decimal conversion is capped.
big = 10**5000
try:
    str(big)
except ValueError as e:
    print(e)  # Exceeds the limit (4300 digits) for integer string conversion...
else:
    raise AssertionError("expected ValueError")

# It also applies to parsing, including json.loads.
try:
    json.loads("9" * 5000)
except ValueError:
    pass
else:
    raise AssertionError("expected ValueError")

# Power-of-two bases are linear time, so they are not limited.
assert hex(big).startswith("0x")

# The fix: raise the limit deliberately where you trust the input.
old_limit = sys.get_int_max_str_digits()
sys.set_int_max_str_digits(0)  # 0 means unlimited
try:
    assert len(str(big)) == 5001
finally:
    sys.set_int_max_str_digits(old_limit)
