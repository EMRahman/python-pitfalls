"""Comprehensions in a class body can't see class variables, and may find globals instead."""

rate = 0.0  # An unrelated module-level name.


# The trap
class Fees:
    rate = 0.01
    tiers = [rate * n for n in (1, 2, 3)]


print(Fees.tiers)  # [0.0, 0.0, 0.0] (used the global, not Fees.rate)
assert Fees.tiers == [0.0, 0.0, 0.0]

# Without the global it's a NameError instead.
del rate
try:

    class Fees2:
        rate = 0.01
        tiers = [rate * n for n in (1, 2, 3)]

except NameError as e:
    print(e)  # name 'rate' is not defined
else:
    raise AssertionError("expected NameError")


# The fix: a plain loop runs in the class scope.
class FeesFixed:
    rate = 0.01
    tiers = []
    for n in (1, 2, 3):
        tiers.append(rate * n)
    del n


assert FeesFixed.tiers == [0.01, 0.02, 0.03]
