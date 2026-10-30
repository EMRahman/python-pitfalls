"""Mutable default arguments are created once, at definition time."""


# The trap
def add_item(item, target=[]):
    target.append(item)
    return target


print(add_item("Apple"))   # ['Apple']
print(add_item("Banana"))  # ['Apple', 'Banana'] (Apple leaked!)
assert add_item("Cherry") == ["Apple", "Banana", "Cherry"]

# The shared default is visible on the function object itself.
assert add_item.__defaults__ == (["Apple", "Banana", "Cherry"],)


# The fix: use None as a sentinel and build a fresh object per call.
def add_item_fixed(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target


assert add_item_fixed("Apple") == ["Apple"]
assert add_item_fixed("Banana") == ["Banana"]
