"""`python -O` deletes assert statements, along with any checks inside them."""

import subprocess
import sys

code = """
def withdraw(balance, amount):
    assert amount <= balance, "insufficient funds"
    return balance - amount

print(withdraw(100, 500))
"""

normal = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
optimized = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)

assert "AssertionError: insufficient funds" in normal.stderr
print(optimized.stdout.strip())  # -400 (the check silently disappeared)
assert optimized.stdout.strip() == "-400"

# The fix: validate with an explicit raise. Use assert only for internal invariants.
code_fixed = code.replace(
    'assert amount <= balance, "insufficient funds"',
    'if amount > balance:\n        raise ValueError("insufficient funds")',
)
optimized = subprocess.run([sys.executable, "-O", "-c", code_fixed], capture_output=True, text=True)
assert "ValueError: insufficient funds" in optimized.stderr
