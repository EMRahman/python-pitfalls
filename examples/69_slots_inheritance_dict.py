"""Subclassing a __slots__ class without declaring __slots__ silently restores __dict__."""


class Point:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y


# The parent has no __dict__ and rejects unknown attributes.
p = Point(1, 2)
assert not hasattr(p, "__dict__")


# The trap: omitting __slots__ on a subclass recreates __dict__ and __weakref__ on instances.
class LabeledPoint(Point):
    pass


lp = LabeledPoint(1, 2)
lp.typo_attr = 99  # Silently stored in lp.__dict__!
print(hasattr(lp, "__dict__"), lp.__dict__)  # True {'typo_attr': 99}
assert hasattr(lp, "__dict__")
assert lp.__dict__ == {"typo_attr": 99}


# The fix: declare __slots__ on every subclass (use `()` if it adds no new attributes).
class SlottedLabeledPoint(Point):
    __slots__ = ("label",)

    def __init__(self, x, y, label):
        super().__init__(x, y)
        self.label = label


sp = SlottedLabeledPoint(1, 2, "origin")
assert not hasattr(sp, "__dict__")
try:
    sp.typo_attr = 99
except AttributeError:
    pass
else:
    raise AssertionError("expected AttributeError on slotted subclass")
