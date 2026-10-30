"""Arithmetic on aware datetimes is wall-clock arithmetic, which breaks across DST."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

rome = ZoneInfo("Europe/Rome")

# The trap (Home Assistant core PR #188537): during the repeated hour after
# clocks go back, now() + 3 minutes lands *before* now.
now_utc = datetime(2026, 10, 25, 1, 4, 22, tzinfo=UTC)
now_local = now_utc.astimezone(rome)  # 02:04:22+01:00 (second pass through 02:00)
next_alert = now_local + timedelta(minutes=3)
print(now_local, "->", next_alert)  # 02:04:22+01:00 -> 02:07:22+02:00
assert next_alert < now_utc  # Scheduled in the past, so it fires again at once.

# Subtraction is wall-clock too when both sides share a tzinfo.
ny = ZoneInfo("America/New_York")
open_sat = datetime(2026, 3, 7, 12, 0, tzinfo=ny)
open_sun = open_sat + timedelta(days=1)  # Clocks spring forward overnight.
print(open_sun - open_sat)  # 1 day, 0:00:00 (but only 23 real hours passed)
assert open_sun - open_sat == timedelta(days=1)
assert open_sun.astimezone(UTC) - open_sat.astimezone(UTC) == timedelta(hours=23)

# The fix: do arithmetic in UTC, convert to local time only for display.
next_alert = now_utc + timedelta(minutes=3)
assert next_alert > now_utc
