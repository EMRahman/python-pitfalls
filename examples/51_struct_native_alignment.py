"""struct's default format uses native padding and byte order."""

import struct

# The trap: a 5-byte wire record (uint8 side, uint32 size).
assert struct.calcsize("BI") == 8  # Native alignment pads 3 bytes after the B.
assert struct.calcsize("<BI") == 5

record = struct.pack("<BI", 1, 300)
try:
    struct.unpack("BI", record)
except struct.error as e:
    print(e)  # unpack requires a buffer of 8 bytes
else:
    raise AssertionError("expected struct.error")

# Byte order: network data is big-endian, most CPUs are little-endian.
network_uint32 = b"\x00\x00\x01\x2c"  # 300, big-endian
print(struct.unpack("=I", network_uint32)[0])  # 738263040 on x86 and ARM
assert struct.unpack(">I", network_uint32)[0] == 300

# The fix: always state byte order and size with <, > or !.
assert struct.unpack("<BI", record) == (1, 300)
