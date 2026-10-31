"""`from __future__ import annotations` turns __annotations__ values into strings at runtime."""

from __future__ import annotations

import typing


def parse_port(port: int) -> int:
    return port


# The trap: inspecting __annotations__ directly sees 'int' (a str), not the int class.
ann = parse_port.__annotations__["port"]
print(type(ann), repr(ann))  # <class 'str'> 'int'
assert isinstance(ann, str)

try:
    isinstance(8080, parse_port.__annotations__["port"])
except TypeError as e:
    print(e)  # isinstance() arg 2 must be a type, a tuple of types, or a union
else:
    raise AssertionError("expected TypeError when passing string annotation to isinstance")

# Local classes have a second trap: get_type_hints() looks up names in module globals
# unless given localns, so annotations referencing function-local types fail outside the scope.
def make_handler():
    class LocalRequest:
        pass

    def handle(req: LocalRequest) -> None:
        pass

    return handle, LocalRequest


handler, local_cls = make_handler()
try:
    typing.get_type_hints(handler)
except NameError:
    pass
else:
    raise AssertionError("expected NameError for unresolvable local class")

# The fix: use typing.get_type_hints() instead of raw __annotations__, and keep
# runtime-inspected types at module scope (or pass localns explicitly).
hints = typing.get_type_hints(parse_port)
assert hints["port"] is int
assert isinstance(8080, hints["port"])
assert typing.get_type_hints(handler, localns={"LocalRequest": local_cls})["req"] is local_cls
