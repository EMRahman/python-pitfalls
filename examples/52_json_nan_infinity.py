"""json.dumps emits NaN and Infinity, which aren't valid JSON."""

import json

# The trap
payload = json.dumps({"bid": float("nan"), "ask": float("inf")})
print(payload)  # {"bid": NaN, "ask": Infinity}
assert payload == '{"bid": NaN, "ask": Infinity}'
assert json.loads(payload)  # Python accepts it; JavaScript's JSON.parse throws.

# The fix: refuse non-finite floats and send null (or a sentinel) explicitly.
try:
    json.dumps({"bid": float("nan")}, allow_nan=False)
except ValueError as e:
    print(e)  # Out of range float values are not JSON compliant
else:
    raise AssertionError("expected ValueError")

assert json.dumps({"bid": None}) == '{"bid": null}'
