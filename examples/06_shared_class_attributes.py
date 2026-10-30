"""Mutable class attributes are shared by every instance."""

from dataclasses import dataclass, field


# The trap
class Cart:
    items = []

    def add(self, item):
        self.items.append(item)


alice, bob = Cart(), Cart()
alice.add("apple")
print(bob.items)  # ['apple'] (Bob never added anything!)
assert bob.items == ["apple"]


# The fix: create per-instance state in __init__ ...
class CartFixed:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)


alice, bob = CartFixed(), CartFixed()
alice.add("apple")
assert bob.items == []


# ... or let a dataclass do it with default_factory.
@dataclass
class CartData:
    items: list = field(default_factory=list)


assert CartData().items is not CartData().items
