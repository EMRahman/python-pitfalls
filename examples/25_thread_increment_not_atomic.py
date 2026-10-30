"""`counter += 1` is several bytecode steps; threads can interleave between them."""

import dis
import threading
import time

# Why: one line of Python, separate load and store instructions.
ops = [i.opname for i in dis.get_instructions("counter += 1")]
print(ops)  # [..., 'LOAD_NAME', ..., 'BINARY_OP', 'STORE_NAME', ...]
assert any(op.startswith("LOAD_NAME") for op in ops)
assert any(op.startswith("STORE_NAME") for op in ops)

# The trap: read-modify-write from two threads.
counter = 0


def work():
    global counter
    for _ in range(1000):
        current = counter
        time.sleep(0)  # Stands in for any thread switch between load and store.
        counter = current + 1


threads = [threading.Thread(target=work) for _ in range(2)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(counter)  # Far less than 2000
assert counter < 2000

# The fix: guard the read-modify-write with a lock.
counter = 0
lock = threading.Lock()


def work_fixed():
    global counter
    for _ in range(1000):
        with lock:
            current = counter
            time.sleep(0)
            counter = current + 1


threads = [threading.Thread(target=work_fixed) for _ in range(2)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert counter == 2000
