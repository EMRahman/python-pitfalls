"""os.path.join and pathlib discard everything before an absolute component."""

import os
import tempfile
from pathlib import Path

# The trap: a "safe" upload directory plus a user-supplied filename.
upload_dir = "/srv/app/uploads"
assert os.path.join(upload_dir, "report.pdf") == "/srv/app/uploads/report.pdf"
print(os.path.join(upload_dir, "/etc/hosts"))  # /etc/hosts (the prefix is gone)
assert os.path.join(upload_dir, "/etc/hosts") == "/etc/hosts"
assert Path(upload_dir) / "/etc/hosts" == Path("/etc/hosts")

# Relative segments escape too, and join() never normalizes them.
assert os.path.join(upload_dir, "../config.py") == "/srv/app/uploads/../config.py"


# The fix: resolve the final path and check it is still inside the base directory.
def safe_join(base, name):
    base = Path(base).resolve()
    target = (base / name).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"{name!r} escapes {base}")
    return target


with tempfile.TemporaryDirectory() as d:
    assert safe_join(d, "report.pdf").name == "report.pdf"
    for bad in ["/etc/hosts", "../config.py", "a/../../config.py"]:
        try:
            safe_join(d, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad}")
