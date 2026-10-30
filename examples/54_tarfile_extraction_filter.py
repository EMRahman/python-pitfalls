"""tarfile.extractall trusted member paths until Python 3.14 (CVE-2007-4559)."""

import io
import os
import sys
import tarfile
import tempfile
import warnings

if not hasattr(tarfile, "data_filter"):
    print("this Python predates tarfile extraction filters (PEP 706); skipping")
    sys.exit(0)


def archive_with(name):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(name)
        info.size = 4
        tar.addfile(info, io.BytesIO(b"data"))
    buf.seek(0)
    return buf


with tempfile.TemporaryDirectory() as root:
    dest = os.path.join(root, "dest")
    os.mkdir(dest)
    escaped = os.path.join(root, "outside.txt")

    # The trap: a member named "../outside.txt" lands outside the destination
    # on Python < 3.14, where extractall() defaults to the "fully_trusted" filter.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            with tarfile.open(fileobj=archive_with("../outside.txt")) as tar:
                tar.extractall(dest)
        except tarfile.FilterError:
            pass

    if sys.version_info >= (3, 14):
        print("3.14+: refused by the default 'data' filter")
        assert not os.path.exists(escaped)
    else:
        print("before 3.14: written outside the destination directory")
        assert os.path.exists(escaped)
        os.remove(escaped)

    # The fix: always pass filter="data" (backported to 3.8.17+, 3.9.17+,
    # 3.10.12+, 3.11.4+), so behavior doesn't depend on the Python version.
    try:
        with tarfile.open(fileobj=archive_with("../outside.txt")) as tar:
            tar.extractall(dest, filter="data")
    except tarfile.OutsideDestinationError as e:
        print(f"refused: {type(e).__name__}")
    else:
        raise AssertionError("expected OutsideDestinationError")
    assert not os.path.exists(escaped)
