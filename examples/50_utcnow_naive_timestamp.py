"""datetime.utcnow() returns a naive datetime that .timestamp() treats as local time."""

import os
import sys
import time
import warnings
from datetime import datetime, timezone

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

if not hasattr(time, "tzset"):
    print("time.tzset is not available on this platform; skipping")
    sys.exit(0)

os.environ["TZ"] = "America/New_York"
time.tzset()

# The trap
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)  # Deprecated in 3.12.
    naive = datetime.utcnow()

assert naive.tzinfo is None
error_hours = (naive.timestamp() - time.time()) / 3600
print(f"off by {error_hours:.0f} hours")  # off by 4 or 5 hours
assert abs(error_hours) > 3

# The fix: use aware datetimes.
aware = datetime.now(UTC)
assert abs(aware.timestamp() - time.time()) < 5
