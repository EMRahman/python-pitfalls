"""hash() of str and bytes changes between processes, so it can't route data."""

import subprocess
import sys

symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOG", "META", "NFLX"]


def shards_in_new_process(expr, seed):
    code = f"symbols = {symbols!r}\nimport zlib\nprint([{expr} for s in symbols])"
    env = {"PYTHONHASHSEED": seed}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    return out.stdout.strip()


# The trap: two workers (two processes) disagree about where a symbol lives.
worker_a = shards_in_new_process("hash(s) % 4", "1")
worker_b = shards_in_new_process("hash(s) % 4", "2")
print(worker_a)
print(worker_b)
assert worker_a != worker_b

# The fix: use a stable hash such as zlib.crc32 or hashlib.
worker_a = shards_in_new_process("zlib.crc32(s.encode()) % 4", "1")
worker_b = shards_in_new_process("zlib.crc32(s.encode()) % 4", "2")
assert worker_a == worker_b
