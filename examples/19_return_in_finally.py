"""return/break/continue inside `finally` silently discards exceptions."""

# Python 3.14+ emits a SyntaxWarning for the code below (PEP 765).


# The trap
def save():
    try:
        raise OSError("disk full")
    finally:
        return "saved"  # The OSError vanishes.


print(save())  # 'saved'
assert save() == "saved"


# The fix: keep finally for cleanup only, and return outside it.
def save_fixed():
    try:
        raise OSError("disk full")
    finally:
        pass  # cleanup goes here
    return "saved"


try:
    save_fixed()
except OSError:
    pass
else:
    raise AssertionError("expected OSError")
