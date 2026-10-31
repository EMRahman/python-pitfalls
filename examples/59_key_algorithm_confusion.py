"""Letting an untrusted token header choose the algorithm turns a public key into an HMAC secret."""

import base64
import hashlib
import hmac
import json

# Public verification material that anyone (including an attacker) can read.
SERVER_PUBLIC_KEY = b"-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A\n-----END PUBLIC KEY-----"


def b64e(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64d(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# The trap: one `key` parameter whose meaning is chosen by the token's own `alg` header.
def decode_insecure(token, key):
    header_b64, payload_b64, sig_b64 = token.split(".")
    header = json.loads(b64d(header_b64))
    signing_input = f"{header_b64}.{payload_b64}".encode()

    if header["alg"] == "HS256":
        expected = hmac.new(key, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(b64d(sig_b64), expected):
            raise ValueError("bad signature")
    elif header["alg"] == "RS256":
        raise NotImplementedError("asymmetric check omitted in demo")
    else:
        raise ValueError("unknown alg")
    return json.loads(b64d(payload_b64))


# An attacker labels the token HS256 and signs it using the server's public key bytes.
header = b64e(json.dumps({"alg": "HS256"}).encode())
payload = b64e(json.dumps({"sub": "admin"}).encode())
forged_sig = b64e(hmac.new(SERVER_PUBLIC_KEY, f"{header}.{payload}".encode(), hashlib.sha256).digest())
forged_token = f"{header}.{payload}.{forged_sig}"

claims = decode_insecure(forged_token, SERVER_PUBLIC_KEY)
print(claims)  # {'sub': 'admin'} (accepted!)
assert claims == {"sub": "admin"}


# The fix: the server pins allowed algorithms explicitly and never trusts the header alone.
def decode_fixed(token, key, *, algorithms):
    header_b64, _, _ = token.split(".")
    header = json.loads(b64d(header_b64))
    if header.get("alg") not in algorithms:
        raise ValueError(f"disallowed algorithm: {header.get('alg')!r}")
    return decode_insecure(token, key)


try:
    decode_fixed(forged_token, SERVER_PUBLIC_KEY, algorithms=["RS256"])
except ValueError as e:
    print(e)  # disallowed algorithm: 'HS256'
else:
    raise AssertionError("expected forged HS256 token to be rejected")
