"""Defining __len__ without __bool__ makes valid zero-length objects falsy."""

import warnings
import xml.etree.ElementTree as ET


# The trap: `if node:` calls __bool__, which falls back to `len(node) != 0`.
class Node:
    def __init__(self, name, children=()):
        self.name = name
        self.children = list(children)

    def __len__(self):
        return len(self.children)


leaf = Node("root")  # A valid node that happens to have 0 children.
found = leaf if leaf else None
print(found)  # None (treated as missing!)
assert bool(leaf) is False
assert found is None

# Standard library example: an XML Element with no child elements is falsy too.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    elem = ET.fromstring("<status>ok</status>")
    assert bool(elem) is False


# The fix: test `is not None` for optional objects, and define `__bool__` when
# an empty container-like object is still a valid, present entity.
class SafeNode(Node):
    def __bool__(self):
        return True


safe_leaf = SafeNode("root")
assert bool(safe_leaf) is True
assert len(safe_leaf) == 0
assert (leaf if leaf is not None else None) is leaf
