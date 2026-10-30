"""Adjacent string literals are joined, so a missing comma merges items."""

# The trap
fruits = [
    "apple",
    "banana"  # <- missing comma
    "cherry",
]
print(fruits)  # ['apple', 'bananacherry']
assert fruits == ["apple", "bananacherry"]
assert len(fruits) == 2

# The fix: trailing commas on every line, plus a linter that flags this.
fruits = [
    "apple",
    "banana",
    "cherry",
]
assert len(fruits) == 3
