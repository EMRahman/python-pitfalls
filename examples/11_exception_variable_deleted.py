"""The `as` name in an except block is deleted when the block ends."""

# The trap
e = "important data"
try:
    1 / 0
except ZeroDivisionError as e:
    pass

try:
    print(e)
except NameError as err:
    print(f"{type(err).__name__}: {err}")  # NameError: name 'e' is not defined
else:
    raise AssertionError("expected NameError")

# The fix: copy the exception to another name if you need it later.
error = None
try:
    1 / 0
except ZeroDivisionError as exc:
    error = exc

assert isinstance(error, ZeroDivisionError)
