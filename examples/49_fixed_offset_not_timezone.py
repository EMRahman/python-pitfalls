"""A parsed "+02:00" is a fixed offset, not a time zone, so it ignores DST."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

amsterdam = ZoneInfo("Europe/Amsterdam")

# The trap (Home Assistant core PR #188836): a stored timestamp is parsed back
# and used to schedule tomorrow's 03:45 backup.
last_backup = datetime.fromisoformat("2024-10-26T03:45:00+02:00")
assert last_backup.tzinfo == timezone(timedelta(hours=2))  # Not Europe/Amsterdam.

next_backup = last_backup + timedelta(days=1)
print(next_backup.astimezone(amsterdam))  # 2024-10-27 02:45:00+01:00 (an hour early)
assert next_backup.astimezone(amsterdam).hour == 2

# The fix: convert to the real zone before doing calendar arithmetic.
next_backup = last_backup.astimezone(amsterdam) + timedelta(days=1)
assert next_backup.hour == 3
assert next_backup.utcoffset() == timedelta(hours=1)
