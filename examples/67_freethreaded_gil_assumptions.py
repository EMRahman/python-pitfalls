""""The GIL makes dict thread-safe" fails on compound operations and dict iteration."""

import threading
import time

# The trap: individual C-level dict lookups are atomic under the GIL, so code often skips
# locks around shared dicts. Both check-then-set and concurrent iteration break anyway—and
# under free-threaded Python (3.13t/3.14t) there is no GIL to hide timing windows at all.
cache = {}
calls = 0


def expensive(key):
    global calls
    time.sleep(0.01)  # Simulates I/O or CPU work between check and store.
    calls += 1
    return f"value-{key}"


def get_unlocked(key):
    if key not in cache:
        cache[key] = expensive(key)
    return cache[key]


threads = [threading.Thread(target=get_unlocked, args=("user:1",)) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"expensive() calls for one key: {calls}")  # 5 (computed 5 times instead of 1)
assert calls > 1

# Concurrent mutation during iteration raises RuntimeError even with the GIL enabled.
shared = {i: i for i in range(200)}
iteration_error = None
ready = threading.Event()


def iterate_dict():
    global iteration_error
    try:
        for i, _ in enumerate(shared):
            if i == 10:
                ready.set()
            time.sleep(0.0005)
    except RuntimeError as e:
        iteration_error = e


t = threading.Thread(target=iterate_dict)
t.start()
ready.wait()
shared["new_key"] = 999
t.join()
assert isinstance(iteration_error, RuntimeError)

# The fix: guard check-then-act and snapshots with a Lock.
cache.clear()
calls = 0
lock = threading.Lock()


def get_locked(key):
    with lock:
        if key not in cache:
            cache[key] = expensive(key)
        return cache[key]


threads = [threading.Thread(target=get_locked, args=("user:1",)) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert calls == 1
