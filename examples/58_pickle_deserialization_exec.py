"""pickle.loads executes arbitrary callables encoded in the payload during deserialization."""

import hashlib
import hmac
import json
import pickle

side_effects = []


def record_call(arg):
    side_effects.append(arg)
    return {"loaded": arg}


class BenignPayload:
    def __reduce__(self):
        # Instructs the pickle VM to call record_call("ran-during-load") while loading.
        return (record_call, ("ran-during-load",))


# The trap: loading bytes runs code before the caller ever inspects the result.
raw = pickle.dumps(BenignPayload())
result = pickle.loads(raw)
print(side_effects)  # ['ran-during-load']
assert side_effects == ["ran-during-load"]

# The fix: use a data-only format such as JSON for untrusted input.
safe_bytes = json.dumps({"loaded": "data-only"}).encode()
assert json.loads(safe_bytes) == {"loaded": "data-only"}


# If you must load pickles you produced yourself, verify an HMAC before touching pickle.loads.
def signed_dumps(obj, secret):
    body = pickle.dumps(obj)
    sig = hmac.new(secret, body, hashlib.sha256).digest()
    return sig + body


def signed_loads(blob, secret):
    sig, body = blob[:32], blob[32:]
    expected = hmac.new(secret, body, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("untrusted pickle rejected before deserialization")
    return pickle.loads(body)


secret = b"server-only-secret-key"
valid = signed_dumps({"ok": True}, secret)
assert signed_loads(valid, secret) == {"ok": True}

tampered = b"\x00" * 32 + raw
side_effects.clear()
try:
    signed_loads(tampered, secret)
except ValueError:
    pass
else:
    raise AssertionError("expected ValueError on untrusted payload")
assert side_effects == []
