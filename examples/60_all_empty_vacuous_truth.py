"""all([]) is True (vacuous truth), so empty inputs and exhausted iterators pass every check."""

# The trap: "every user is an admin" is True when there are zero users.
users = []
can_deploy = all(u["is_admin"] for u in users)
print(can_deploy)  # True
assert can_deploy is True

# Worse with iterators (#1): logging or counting first makes a failing check pass.
candidates = (u for u in [{"name": "guest", "is_admin": False}])
_ = list(candidates)  # Consumed earlier (e.g. for logging).
assert all(u["is_admin"] for u in candidates) is True


# The fix: materialize once and require at least one item when emptiness isn't valid.
def all_nonempty(items, predicate):
    items = list(items)
    return bool(items) and all(predicate(x) for x in items)


assert all_nonempty([], lambda u: u["is_admin"]) is False
assert all_nonempty([{"is_admin": False}], lambda u: u["is_admin"]) is False
assert all_nonempty([{"is_admin": True}], lambda u: u["is_admin"]) is True
