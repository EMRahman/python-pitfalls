"""A script that imports itself runs twice, as __main__ and as a module."""

import pathlib
import subprocess
import sys
import tempfile
import textwrap

app = textwrap.dedent("""
    print("module body ran as", __name__)

    class Config:
        pass

    if __name__ == "__main__":
        import app  # Or any module that imports app.
        print(isinstance(Config(), app.Config))
""")

with tempfile.TemporaryDirectory() as d:
    path = pathlib.Path(d, "app.py")
    path.write_text(app)
    out = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, cwd=d)

lines = out.stdout.splitlines()
print(lines)
# ['module body ran as __main__', 'module body ran as app', 'False']
assert lines == ["module body ran as __main__", "module body ran as app", "False"]

# The fix: keep the entry point thin. Put code in modules and have a small
# main.py (or `python -m package`) call into them.
