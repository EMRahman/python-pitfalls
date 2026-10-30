"""Iterator exhaustion: looking at an iterator consumes it."""

# The trap
my_string = "hello"
reversed_iter = reversed(my_string)

first = list(reversed_iter)
second = list(reversed_iter)
print(first)   # ['o', 'l', 'l', 'e', 'h']
print(second)  # [] (silently empty!)
assert first == ["o", "l", "l", "e", "h"]
assert second == []

# `in` consumes too: it advances the iterator until it finds a match.
squares = (n * n for n in range(6))
assert 9 in squares
assert list(squares) == [16, 25]  # 0, 1, 4 and 9 are gone

# An exhausted (or empty) iterator is still truthy.
empty = (n for n in [])
assert bool(empty) is True

# The fix: materialize once, then reuse the list as often as you like.
reversed_list = list(reversed(my_string))
assert reversed_list == ["o", "l", "l", "e", "h"]
assert reversed_list == ["o", "l", "l", "e", "h"]
