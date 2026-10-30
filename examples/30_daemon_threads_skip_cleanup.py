"""Daemon threads are killed at exit without running finally blocks."""

import subprocess
import sys
import textwrap

# The trap
child = textwrap.dedent("""
    import threading, time

    def flush_buffer():
        try:
            time.sleep(10)
        finally:
            print("flushed")  # Never runs.

    threading.Thread(target=flush_buffer, daemon=True).start()
    time.sleep(0.1)
    print("main done")
""")
out = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=30)
print(out.stdout.splitlines())  # ['main done']
assert out.stdout.splitlines() == ["main done"]

# The fix: a normal thread with a stop signal, joined on shutdown.
child_fixed = textwrap.dedent("""
    import threading

    stop = threading.Event()

    def flush_buffer():
        try:
            stop.wait(10)
        finally:
            print("flushed")

    t = threading.Thread(target=flush_buffer)
    t.start()
    print("main done")
    stop.set()
    t.join()
""")
out = subprocess.run([sys.executable, "-c", child_fixed], capture_output=True, text=True, timeout=30)
assert out.stdout.splitlines() == ["main done", "flushed"]
