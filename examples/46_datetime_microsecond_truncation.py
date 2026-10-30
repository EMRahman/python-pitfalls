"""datetime only stores microseconds, so nanosecond events collapse together."""

from datetime import datetime, timezone

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

# The trap: two trades 500 ns apart.
trade_a = 1_700_000_000_123_456_100
trade_b = trade_a + 500

dt_a = datetime.fromtimestamp(trade_a / 1e9, UTC)
dt_b = datetime.fromtimestamp(trade_b / 1e9, UTC)
print(dt_a, dt_b)  # identical
assert dt_a == dt_b
assert len({dt_a, dt_b}) == 1  # De-duplicating by timestamp drops a trade.

# The fix: keep integer nanoseconds as the source of truth and convert only for
# display (or use a nanosecond type such as numpy.datetime64[ns] / pandas.Timestamp).
assert trade_a != trade_b
assert len({trade_a, trade_b}) == 2
