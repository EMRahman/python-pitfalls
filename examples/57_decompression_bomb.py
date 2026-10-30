"""A few kilobytes of compressed data can expand to gigabytes in memory."""

import zlib

# The trap: 48 KB on the wire, 50 MB after decompress().
bomb = zlib.compress(b"\0" * 50_000_000, 9)
print(f"compressed {len(bomb):,} bytes")  # ~48,610 bytes
assert len(bomb) < 100_000
assert len(zlib.decompress(bomb)) == 50_000_000  # Real payloads nest layers to reach GBs.

# The fix: decompress incrementally with a hard cap on output size.
LIMIT = 1_000_000


def bounded_decompress(data, limit=LIMIT):
    d = zlib.decompressobj()
    out = d.decompress(data, limit)
    if d.unconsumed_tail or not d.eof:
        raise ValueError(f"decompressed size exceeds {limit:,} bytes")
    return out


try:
    bounded_decompress(bomb)
except ValueError as e:
    print(e)  # decompressed size exceeds 1,000,000 bytes
else:
    raise AssertionError("expected ValueError")

assert bounded_decompress(zlib.compress(b"hello")) == b"hello"
