"""Bare names inside `match`/`case` are capture variables, not constant lookups."""

from enum import IntEnum

# The trap: HTTP_OK looks like a constant comparison, but a bare name matches
# anything and rebinds the local variable HTTP_OK to the subject's value.
HTTP_OK = 200


def classify_broken(response):
    HTTP_OK = 200
    match response:
        case (HTTP_OK, body):  # Captures status into HTTP_OK!
            return f"ok ({HTTP_OK}): {body}"
        case _:
            return "error"


out = classify_broken((500, "database down"))
print(out)  # ok (500): database down
assert out == "ok (500): database down"


# The fix: dotted names (such as Enum members) are value patterns, not captures.
class Status(IntEnum):
    OK = 200
    SERVER_ERROR = 500


def classify_fixed(response):
    match response:
        case (Status.OK, body):
            return f"ok: {body}"
        case _:
            return "error"


assert classify_fixed((500, "database down")) == "error"
assert classify_fixed((200, "healthy")) == "ok: healthy"
