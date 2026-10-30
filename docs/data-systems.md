# Data Systems Pitfalls: Time, Numbers and Bytes

[← Back to all pitfalls](../README.md)

These are the pitfalls that matter when Python moves real data: market feeds, sensor readings, binary protocols and distributed workers. Each one silently corrupts values rather than crashing, so it surfaces as a reconciliation break, a dropped event or a job that fires at the wrong hour.

## Contents

| # | Pitfall | What you see | The fix |
|---|---------|--------------|---------|
| | **Hashing & numbers** | | |
| 43 | [`hash()` changes between processes](#43-hash-changes-between-processes) | Workers disagree on sharding | `zlib.crc32` / `hashlib` |
| 44 | [NaN breaks `in`, `max()` and `sorted()`](#44-nan-breaks-in-max-and-sorted) | Unsorted "sorted" output | Filter NaNs first |
| 45 | [Floats can't hold nanosecond timestamps](#45-floats-cant-hold-nanosecond-timestamps) | Timestamps off by ~100 ns | Integer nanoseconds |
| 46 | [`datetime` truncates to microseconds](#46-datetime-truncates-to-microseconds) | Distinct events compare equal | Integer nanoseconds |
| 47 | [Float prices](#47-float-prices-land-on-the-wrong-tick) | `int(1.15 * 100) == 114` | Fixed-point integers |
| | **Time zones** | | |
| 48 | [Aware datetime arithmetic is wall-clock](#48-aware-datetime-arithmetic-is-wall-clock-arithmetic) | Jobs fire an hour off, or in a loop | Do arithmetic in UTC |
| 49 | [A UTC offset is not a time zone](#49-a-utc-offset-is-not-a-time-zone) | Schedule drifts after DST | Convert to a `ZoneInfo` |
| 50 | [`datetime.utcnow()`](#50-datetimeutcnow-is-off-by-your-utc-offset) | Timestamps off by hours | `datetime.now(timezone.utc)` |
| | **Wire formats** | | |
| 51 | [`struct` pads and byte-swaps](#51-struct-pads-and-byte-swaps-by-default) | Garbage fields, wrong sizes | Always use `<`, `>` or `!` |
| 52 | [`json.dumps` emits invalid JSON](#52-jsondumps-emits-invalid-json) | Other languages reject the payload | `allow_nan=False` |

---

## Hashing & numbers

### 43. `hash()` Changes Between Processes

The built-in `hash()` of `str` and `bytes` is salted with a random seed chosen at interpreter startup (to stop attackers from crafting hash collisions). The same symbol hashes differently in every process, so `hash(key) % n_workers` sends the same key to different shards depending on which process computes it.

```python
# The Trap: run in two processes
shard = hash("AAPL") % 4
# Worker A: [1, 0, 2, 2, 3, 2, 0, 1]   (shards for 8 symbols)
# Worker B: [1, 2, 3, 1, 3, 0, 2, 0]
```

It also makes `set` iteration order of strings differ between runs, which makes tests flaky when they depend on it. (Integers hash to themselves and are not randomized, so the bug hides in tests that use numeric IDs.)

**The fix:** Use a stable hash for anything that crosses a process boundary or gets persisted: `zlib.crc32(key.encode())`, or `hashlib.blake2b(key.encode(), digest_size=8)` for a better distribution. `PYTHONHASHSEED=0` disables randomization, but it's a workaround, not a design.

**In the wild:** Randomization exists because of CVE-2012-1150. Attackers could send request parameters chosen to collide in a dict, turning each insert into a linear scan and letting a single HTTP request occupy a server's CPU. Python added randomization in 2.6.8, 2.7.3 and 3.2.3 behind `-R`, and turned it on by default in 3.3.

[Example](../examples/43_hash_randomization_sharding.py)

### 44. NaN Breaks `in`, `max()` and `sorted()`

`float("nan")` isn't equal to anything, including itself. Every algorithm that relies on comparisons gives inconsistent results when a NaN is present, and none of them raise an error.

```python
# The Trap
nan = float("nan")
nan in [nan]                # True (`in` checks identity before ==)
float("nan") in [nan]       # False (a different NaN object)
max([nan, 1, 2])            # nan
max([1, nan, 2])            # 2   (depends on position!)
sorted([3, nan, 1, 2])      # [3, nan, 1, 2]   (not sorted)
```

**Why:** Sorting and `max()` assume that if `a < b` is false then `a >= b`. Every comparison with NaN is false, so that assumption breaks and the result depends on the order in which elements were compared.

**The fix:** Remove or replace NaNs before aggregating: `[x for x in xs if not math.isnan(x)]`. Market data formats often use a sentinel for a missing price; Databento's [DBN](https://docs.rs/dbn) uses `i64::MAX` (`UNDEF_PRICE`), which its float conversion helpers turn into NaN. Handle that case at the boundary, before it reaches your analytics.

[Example](../examples/44_nan_breaks_containers.py)

### 45. Floats Can't Hold Nanosecond Timestamps

A Unix timestamp in nanoseconds is about 1.7 × 10¹⁸, which needs 61 bits. A float has 53 bits of precision, so near today's date adjacent float values are about 238 ns apart. Converting nanoseconds to float seconds, whether with `ts / 1e9`, `time.time()` or a float column in a DataFrame, quietly rounds the timestamp.

```python
# The Trap
ts_ns = 1_700_000_000_123_456_789
int(ts_ns / 1e9 * 1e9) - ts_ns          # -21 (nanoseconds lost)
(ts_ns + 100) / 1e9 == ts_ns / 1e9      # True (two events, one timestamp)
```

**The fix:** Keep integer nanoseconds end to end. Use `time.time_ns()` (and `time.monotonic_ns()` or `time.perf_counter_ns()` for latency) rather than `time.time()`, and use `divmod(ts_ns, 1_000_000_000)` to split seconds from nanoseconds. Python ints are exact at any size.

[Example](../examples/45_float_nanosecond_timestamps.py)

### 46. `datetime` Truncates to Microseconds

`datetime` and `timedelta` have microsecond resolution. Exchange and network timestamps are nanoseconds, so converting to `datetime` drops the last three digits, and events that were distinct become equal. Sorting loses their true order, and de-duplicating by timestamp drops real records.

```python
# The Trap
trade_a = 1_700_000_000_123_456_100
trade_b = trade_a + 500   # 500 ns later
dt_a = datetime.fromtimestamp(trade_a / 1e9, timezone.utc)
dt_b = datetime.fromtimestamp(trade_b / 1e9, timezone.utc)
dt_a == dt_b              # True
len({dt_a, dt_b})         # 1 (one trade de-duplicated away)
```

**The fix:** Treat integer nanoseconds as the source of truth and convert to `datetime` only for display. When you need datetime-like operations at nanosecond resolution, use `numpy.datetime64[ns]` or `pandas.Timestamp`.

[Example](../examples/46_datetime_microsecond_truncation.py)

### 47. Float Prices Land on the Wrong Tick

Most decimal fractions, including `0.1` and `1.15`, have no exact binary representation. The error is invisible in `repr()` but appears as soon as you convert to an integer number of cents or ticks.

```python
# The Trap
int(1.15 * 100)      # 114 (1.15 * 100 is 114.99999999999999)
int(1.15 / 0.01)     # 114 ticks, not 115
0.1 + 0.2 == 0.3     # False
```

**The fix:** Store prices as fixed-point integers. Databento's [DBN format](https://docs.rs/dbn), for example, encodes every price as a signed 64-bit integer in units of 10⁻⁹, so `1.15` is `1_150_000_000` and tick arithmetic is exact. Convert to float only at the edge, for display. For human-entered amounts, `Decimal("1.15")` from a *string* is exact too. Note that `Decimal(1.15)` from a float keeps the float's error.

[Example](../examples/47_float_prices.py)

---

## Time zones

### 48. Aware `datetime` Arithmetic Is Wall-Clock Arithmetic

Adding a `timedelta` to an aware `datetime` adds to the *wall-clock* time and then looks up the offset again. Across a DST transition, "now + 3 minutes" can land before now or an hour later. Subtracting two datetimes that share a `tzinfo` is wall-clock too, so it ignores the transition.

```python
# The Trap: clocks in Rome go back from 03:00 CEST to 02:00 CET
now = datetime(2026, 10, 25, 1, 4, 22, tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Rome"))
# 02:04:22+01:00, the second pass through 02:00
now + timedelta(minutes=3)
# 02:07:22+02:00, i.e. 00:07 UTC: an hour in the PAST

ny = ZoneInfo("America/New_York")
sat = datetime(2026, 3, 7, 12, tzinfo=ny)
sun = sat + timedelta(days=1)   # Clocks spring forward overnight.
sun - sat                       # 1 day, 0:00:00, but only 23 hours passed
```

**Why:** Wall-clock arithmetic is what you want for calendar logic ("same time tomorrow") but not for durations ("in 3 minutes"). Python can't tell which one you mean. Arithmetic also resets `fold`, the attribute that says which pass through a repeated hour a time belongs to.

**The fix:** Do duration arithmetic in UTC and convert to local time for display: `datetime.now(timezone.utc) + delay`. Use local-time arithmetic only for calendar rules, and test both DST transitions.

**In the wild:** Home Assistant's `alert` integration scheduled repeat notifications with `now() + delay` in local time. During the repeated hour, the next notification landed in the past, fired at once and rescheduled itself the same way, so [notifiers were called in a tight loop](https://github.com/home-assistant/core/pull/188537) until the alert cleared. The fix was a one-word change from `now()` to `utcnow()`.

[Example](../examples/48_aware_datetime_wall_clock_arithmetic.py)

### 49. A UTC Offset Is Not a Time Zone

`datetime.fromisoformat("2024-10-26T03:45:00+02:00")` returns a datetime with a *fixed* `+02:00` offset, not `Europe/Amsterdam`. Calendar arithmetic on it keeps `+02:00` forever, so after DST ends, "03:45 tomorrow" is really 02:45 local time.

```python
# The Trap
last = datetime.fromisoformat("2024-10-26T03:45:00+02:00")   # Parsed from storage.
nxt = last + timedelta(days=1)
nxt.astimezone(ZoneInfo("Europe/Amsterdam"))   # 02:45+01:00 (an hour early)
```

**Why:** ISO 8601 strings store an offset, not the rules that produced it. Once serialized, a datetime has forgotten which time zone it came from.

**The fix:** Convert to the real zone before doing calendar arithmetic: `last.astimezone(ZoneInfo("Europe/Amsterdam")) + timedelta(days=1)`. If the zone matters, store its name (`"Europe/Amsterdam"`) alongside the timestamp.

**In the wild:** Home Assistant's [automatic backups ran an hour off schedule after every DST change](https://github.com/home-assistant/core/pull/188836), until Core restarted. The schedule iterator was seeded with the last backup time loaded from storage, whose tzinfo was the fixed offset in effect at the time. The fix converts the seed with `dt_util.as_local()` first.

[Example](../examples/49_fixed_offset_not_timezone.py)

### 50. `datetime.utcnow()` Is Off by Your UTC Offset

`datetime.utcnow()` returns the current UTC time as a *naive* datetime, with no tzinfo. Every API that receives a naive datetime assumes it's in local time, so `.timestamp()` on it is wrong by your machine's UTC offset. On a UTC server it's correct by coincidence, which is why the bug ships.

```python
# The Trap (on a machine in New York)
datetime.utcnow().timestamp() - time.time()   # +14,400 or +18,000 s (4 or 5 hours off)
```

**The fix:** Use aware datetimes everywhere: `datetime.now(timezone.utc)` (or `datetime.now(UTC)` on Python 3.11+). `utcnow()` and `utcfromtimestamp()` are deprecated as of Python 3.12 for exactly this reason. Ruff's `DTZ003` flags them.

[Example](../examples/50_utcnow_naive_timestamp.py)

---

## Wire formats

### 51. `struct` Pads and Byte-Swaps by Default

A `struct` format without a prefix uses *native* mode: the host CPU's byte order and C alignment rules. `"BI"` (a byte then a 4-byte int) is 8 bytes, not 5, because native mode pads the int to a 4-byte boundary. Network protocols and most file formats are packed and have a fixed byte order.

```python
# The Trap
struct.calcsize("BI")                         # 8 (3 padding bytes)
struct.unpack("BI", five_byte_record)         # struct.error: unpack requires a buffer of 8 bytes
struct.unpack("=I", b"\x00\x00\x01\x2c")      # (738263040,) on x86/ARM, not 300
```

**The fix:** Always start format strings with an explicit byte order: `<` (little-endian), `>` or `!` (big-endian/network). These also disable padding, so `struct.calcsize("<BI")` is 5. `ctypes.Structure` has the same problem: it follows C alignment unless you set `_pack_`. NumPy structured dtypes are packed by default and pad only with `align=True`.

[Example](../examples/51_struct_native_alignment.py)

### 52. `json.dumps` Emits Invalid JSON

By default `json.dumps` writes `NaN`, `Infinity` and `-Infinity` for non-finite floats. These are JavaScript literals, not JSON, so strict parsers (JavaScript's `JSON.parse`, Go's `encoding/json`, many databases) reject the whole payload. Python's own `json.loads` accepts them, so round-trip tests pass.

```python
# The Trap
json.dumps({"bid": float("nan"), "ask": float("inf")})
# '{"bid": NaN, "ask": Infinity}'
```

A related trap: Python serializes huge integers exactly, but JavaScript reads JSON numbers as doubles, so IDs or nanosecond timestamps above 2⁵³ arrive rounded.

**The fix:** Pass `allow_nan=False` to fail fast, and convert missing values to `None` (`null`) yourself. Send large integers such as nanosecond timestamps as strings when the consumer might be JavaScript.

[Example](../examples/52_json_nan_infinity.py)
