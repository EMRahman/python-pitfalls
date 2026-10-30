"""round() rounds halves to the nearest even number."""

from decimal import ROUND_HALF_UP, Decimal

# The trap
print(round(0.5), round(1.5), round(2.5))  # 0 2 2
assert [round(0.5), round(1.5), round(2.5)] == [0, 2, 2]

# Floats add a second surprise: 2.675 is really 2.67499999...
assert round(2.675, 2) == 2.67

# The fix: use Decimal with an explicit rounding mode.
assert Decimal("2.5").quantize(Decimal("1"), rounding=ROUND_HALF_UP) == 3
assert Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("2.68")
