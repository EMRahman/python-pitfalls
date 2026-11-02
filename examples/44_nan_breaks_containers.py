"""NaN is not equal to itself, which breaks membership, max() and sorting."""

import math

nan = float("nan")

# The trap
assert nan != nan
assert nan in [nan]  # `in` checks identity before equality...
assert float("nan") not in [nan]  # ...so a different NaN object isn't found.

# max() and min() depend on where the NaN sits.
print(max([nan, 1, 2]), max([1, nan, 2]))  # nan 2
assert math.isnan(max([nan, 1, 2]))
assert max([1, nan, 2]) == 2

# sorted() silently returns an unsorted list.
result = sorted([3, nan, 1, 2])
print(result)  # [3, nan, 1, 2]
assert [x for x in result if not math.isnan(x)] != [1, 2, 3]

# Sets and dicts accept every distinct NaN object as a separate, un-findable key.
nan_set = {float("nan") for _ in range(5)}
print(len(nan_set), float("nan") in nan_set)  # 5 False
assert len(nan_set) == 5
assert float("nan") not in nan_set

# The fix: remove or replace NaNs before aggregating, sorting or keying containers.
clean = [x for x in [3, nan, 1, 2] if not math.isnan(x)]
assert sorted(clean) == [1, 2, 3]
assert max(clean) == 3
