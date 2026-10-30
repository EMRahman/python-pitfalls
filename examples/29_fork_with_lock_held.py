"""fork() copies a lock held by another thread, but not the thread that would release it."""

import os
import sys
import threading
import time
import warnings

if not hasattr(os, "fork"):
    print("os.fork is not available on this platform; skipping")
    sys.exit(0)

# Python 3.12+ warns about forking a multi-threaded process.
warnings.simplefilter("ignore", DeprecationWarning)

# The trap: a background thread holds a lock (think logging, or a connection pool).
lock = threading.Lock()
held = threading.Event()


def background():
    with lock:
        held.set()
        time.sleep(1)


threading.Thread(target=background).start()
held.wait()

pid = os.fork()
if pid == 0:
    # Child: the lock is copied in its locked state, and nobody will ever release it.
    os._exit(0 if lock.acquire(timeout=0.5) else 1)

_, status = os.waitpid(pid, 0)
child_got_lock = os.waitstatus_to_exitcode(status) == 0
print(f"child acquired the lock: {child_got_lock}")  # False (deadlock)
assert not child_got_lock

# The fix: use the "spawn" or "forkserver" start method (the default on every
# platform since Python 3.14), or fork before starting any threads.
