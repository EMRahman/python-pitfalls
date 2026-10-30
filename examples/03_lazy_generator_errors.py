"""Generators don't run any code until they are iterated."""


# The trap
def chunks(data, size):
    if size <= 0:
        raise ValueError("size must be positive")
    for i in range(0, len(data), size):
        yield data[i : i + size]


batches = chunks([1, 2, 3], 0)  # No error here...

try:
    list(batches)  # ...it only surfaces here, far from the bug.
except ValueError as e:
    print(f"Raised late: {e}")
else:
    raise AssertionError("expected ValueError")


# The fix: validate eagerly in a normal function, then hand off to a generator.
def chunks_fixed(data, size):
    if size <= 0:
        raise ValueError("size must be positive")
    return _chunks(data, size)


def _chunks(data, size):
    for i in range(0, len(data), size):
        yield data[i : i + size]


try:
    chunks_fixed([1, 2, 3], 0)  # Fails immediately, at the call site.
except ValueError:
    pass
else:
    raise AssertionError("expected ValueError")

assert list(chunks_fixed([1, 2, 3], 2)) == [[1, 2], [3]]
