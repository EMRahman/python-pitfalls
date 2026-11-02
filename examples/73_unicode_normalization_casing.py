"""Visually identical Unicode strings can differ in bytes, length, equality and hash."""

import unicodedata

# The trap: precomposed (NFC) vs decomposed (NFD, common in macOS filenames).
nfc = "caf\u00e9"       # 'café' as 4 code points
nfd = "cafe\u0301"      # 'café' as 5 code points ('e' + combining acute accent)

print(nfc, nfd, nfc == nfd, len(nfc), len(nfd))  # café café False 4 5
assert nfc != nfd
assert len(nfc) == 4 and len(nfd) == 5
assert len({nfc, nfd}) == 2  # Two separate keys for the "same" string!

# Case-insensitive Trap: .lower() doesn't handle multi-character mappings like German 'ß'.
assert "ß".lower() == "ß"
assert "ß".upper() == "SS"
assert "straße".lower() != "STRASSE".lower()

# The fix: normalize external strings (typically NFC) and use .casefold() for caseless matching.
assert unicodedata.normalize("NFC", nfc) == unicodedata.normalize("NFC", nfd)


def canonical_key(text):
    return unicodedata.normalize("NFC", text).casefold()


assert canonical_key(nfc) == canonical_key(nfd)
assert canonical_key("straße") == canonical_key("STRASSE")
