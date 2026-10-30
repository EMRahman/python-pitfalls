"""`is` on integers depends on caching and compilation, not on value."""

# The trap: CPython keeps one shared object for each int from -5 to 256.
a = int("256")
b = int("256")
print(a is b)  # True

c = int("257")
d = int("257")
print(c is d)  # False (same value, different objects)
assert a is b
assert c is not d

# Literals are even less predictable: identical constants compiled together
# are merged, so `x = 257; y = 257; x is y` is True in a script but False when
# typed line by line into the REPL.
x = 257
y = 257
assert x is y

# The fix: compare values with ==. Reserve `is` for None and other singletons.
assert c == d
