"""Binary floats can't represent most decimal prices exactly."""

from decimal import Decimal

# The trap
print(int(1.15 * 100))  # 114 (1.15 * 100 is 114.99999999999999)
assert int(1.15 * 100) == 114
assert 0.1 + 0.2 != 0.3

# Converting a price to ticks can land on the wrong tick.
price, tick = 1.15, 0.01
assert int(price / tick) == 114

# The fix: fixed-point integers (e.g. price * 10**9 as an int, as Databento's DBN
# format does), or Decimal built from strings.
PRICE_SCALE = 1_000_000_000
price_fixed = 1_150_000_000  # 1.15
tick_fixed = 10_000_000  # 0.01
assert price_fixed // tick_fixed == 115
assert price_fixed / PRICE_SCALE == 1.15  # Convert to float only for display.

assert Decimal("1.15") * 100 == 115
assert Decimal(1.15) != Decimal("1.15")  # A Decimal from a float keeps its error.
