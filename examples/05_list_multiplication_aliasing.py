"""Multiplying a list of lists copies references, not the inner lists."""

# The trap
grid = [[0] * 3] * 3
grid[0][0] = 1
print(grid)  # [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
assert grid == [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
assert grid[0] is grid[1] is grid[2]

# Same trap, different spelling: dict.fromkeys shares one value object.
groups = dict.fromkeys(["a", "b"], [])
groups["a"].append(1)
assert groups == {"a": [1], "b": [1]}

# The fix: a comprehension builds a new inner object on each pass.
grid = [[0] * 3 for _ in range(3)]
grid[0][0] = 1
assert grid == [[1, 0, 0], [0, 0, 0], [0, 0, 0]]

groups = {key: [] for key in ["a", "b"]}
groups["a"].append(1)
assert groups == {"a": [1], "b": []}
