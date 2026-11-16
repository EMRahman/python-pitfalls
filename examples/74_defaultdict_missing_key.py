""""defaultdict turns a missing-key read into an insertion, which can hide typos."""

from collections import defaultdict

# Intended aggregation: this is exactly what defaultdict(int) is good for.
events = [("api", "timeout"), ("orders", "bad_response"), ("api", "connection_reset")]
error_counts = defaultdict(int)
for service, _error in events:
    error_counts[service] += 1
assert dict(error_counts) == {"api": 2, "orders": 1}

# Trap: a read of an unknown key creates it with the factory's default.
known_counts = defaultdict(int, api=12)
service = "apii"  # A typo; no such registered service exists.
assert known_counts[service] == 0
print(dict(known_counts))  # {'api': 12, 'apii': 0}
assert dict(known_counts) == {"api": 12, "apii": 0}

# The safe inspection path: .get() does not mutate the mapping.
checked_counts = defaultdict(int, api=12)
assert checked_counts.get(service, 0) == 0
assert dict(checked_counts) == {"api": 12}

# When absence is a bug, validate explicitly (or use a plain dict).
if service not in checked_counts:
    print(f"Unknown service: {service}")
else:
    print(checked_counts[service])
