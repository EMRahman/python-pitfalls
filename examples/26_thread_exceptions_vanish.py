"""Exceptions in threads don't reach the caller; in executors they vanish entirely."""

import threading
from concurrent.futures import ThreadPoolExecutor


def job():
    raise ValueError("boom")


# The trap (1): Thread prints a traceback to stderr, then join() returns normally.
seen = []
original_hook = threading.excepthook
threading.excepthook = lambda args: seen.append(args.exc_type)
t = threading.Thread(target=job)
t.start()
t.join()  # No exception here.
threading.excepthook = original_hook
print("main thread carried on")
assert seen == [ValueError]

# The trap (2): an executor stores the exception and prints nothing at all.
with ThreadPoolExecutor() as pool:
    future = pool.submit(job)
assert isinstance(future.exception(), ValueError)

# The fix: always collect results. future.result() re-raises in the caller.
with ThreadPoolExecutor() as pool:
    future = pool.submit(job)
try:
    future.result()
except ValueError as e:
    print(f"surfaced: {e}")
else:
    raise AssertionError("expected ValueError")
