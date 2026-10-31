"""Popen.wait() with stdout=PIPE deadlocks once the child fills the OS pipe buffer."""

import subprocess
import sys

# A child that writes 1 MB to stdout (~16x a typical 64 KB OS pipe buffer).
cmd = [sys.executable, "-c", "import sys; sys.stdout.write('x' * 1_000_000)"]

# The trap: wait() waits for exit without reading stdout, while the child blocks on write().
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
try:
    proc.wait(timeout=0.3)
except subprocess.TimeoutExpired:
    deadlocked = True
    proc.kill()
    proc.communicate()  # Drain and close pipe cleanly.
else:
    deadlocked = False
    proc.stdout.close()

print(f"wait() deadlocked: {deadlocked}")  # True
assert deadlocked is True

# The fix: subprocess.run() (or proc.communicate()) drains pipes while waiting.
completed = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
assert len(completed.stdout) == 1_000_000
