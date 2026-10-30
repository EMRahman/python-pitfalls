"""threading.Lock deadlocks if the same thread acquires it twice."""

import threading

# The trap
lock = threading.Lock()


def update_balance():
    with lock:
        return audit()  # Calls a helper that also takes the lock.


def audit():
    # With `with lock:` this would hang forever; a timeout lets us observe it.
    acquired = lock.acquire(timeout=0.1)
    if acquired:
        lock.release()
    return acquired


print(update_balance())  # False (deadlocked on itself)
assert update_balance() is False

# The fix: RLock can be re-acquired by the thread that holds it.
lock = threading.RLock()
assert update_balance() is True
