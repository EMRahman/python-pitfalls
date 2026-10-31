"""itertools.groupby only groups consecutive runs, and advancing it drains prior groups."""

from collections import defaultdict
from itertools import groupby

# Trap 1: unsorted data produces duplicate group keys, unlike SQL GROUP BY.
events = [("alice", 10), ("bob", 20), ("alice", 5)]
keys = [user for user, _ in groupby(events, key=lambda r: r[0])]
print(keys)  # ['alice', 'bob', 'alice']
assert keys == ["alice", "bob", "alice"]

# Trap 2: storing (key, group_iter) pairs leaves earlier group iterators empty.
sorted_events = sorted(events, key=lambda r: r[0])
saved = list(groupby(sorted_events, key=lambda r: r[0]))
first_key, first_group = saved[0]
print(first_key, list(first_group))  # alice [] (drained when groupby moved to 'bob')
assert first_key == "alice"
assert list(first_group) == []

# The fix: sort by the same key first and materialize each group immediately...
grouped = [(k, list(g)) for k, g in groupby(sorted(events, key=lambda r: r[0]), key=lambda r: r[0])]
assert grouped == [("alice", [("alice", 10), ("alice", 5)]), ("bob", [("bob", 20)])]

# ...or group in O(n) without sorting using defaultdict(list).
by_user = defaultdict(list)
for user, amount in events:
    by_user[user].append(amount)
assert dict(by_user) == {"alice": [10, 5], "bob": [20]}
