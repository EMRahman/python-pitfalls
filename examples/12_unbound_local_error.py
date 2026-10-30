"""Assigning to a name anywhere in a function makes it local everywhere in it."""

# The trap
total = 10


def report():
    print(total)  # UnboundLocalError is raised HERE...
    if False:
        total = 0  # ...because of this line, which never even runs.


try:
    report()
except UnboundLocalError as e:
    print(e)
else:
    raise AssertionError("expected UnboundLocalError")


# The fix: pass values in and return results (or declare `global`/`nonlocal`).
def report_fixed(total):
    print(total)
    return total


assert report_fixed(total) == 10
