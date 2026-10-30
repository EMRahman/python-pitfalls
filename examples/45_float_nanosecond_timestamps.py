"""A float can't hold a nanosecond Unix timestamp exactly."""

import time

ts_ns = 1_700_000_000_123_456_789  # 2023-11-14, nanosecond precision

# The trap: a float64 has 53 bits of precision; this needs about 61.
seconds = ts_ns / 1e9
round_trip = int(seconds * 1e9)
print(round_trip - ts_ns)  # -21 (nanoseconds gained or lost)
assert round_trip != ts_ns

# Near today's epoch, floats are ~238 ns apart, so distinct events collide.
assert (ts_ns + 100) / 1e9 == ts_ns / 1e9

# The fix: keep integer nanoseconds end to end.
now_ns = time.time_ns()  # not time.time()
assert isinstance(now_ns, int)
whole, frac = divmod(ts_ns, 1_000_000_000)
assert (whole, frac) == (1_700_000_000, 123_456_789)
