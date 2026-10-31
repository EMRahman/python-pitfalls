# Concurrency Pitfalls: asyncio and Threading

[← Back to all pitfalls](../README.md)

Concurrency bugs are the purest form of *unknown unknowns*. The code reads top to bottom, but it runs in an order decided by the event loop, the OS scheduler and the GIL. Most of these pass every test and fail under production load.

## Contents

| # | Pitfall | What you see | The fix |
|---|---------|--------------|---------|
| | **asyncio** | | |
| 20 | [Fire-and-forget tasks get garbage-collected](#20-fire-and-forget-tasks-get-garbage-collected) | Work silently never finishes | Keep a reference in a set |
| 21 | [Forgetting `await`](#21-forgetting-await-silently-does-nothing) | Function "ran" but did nothing | `await` it; enable a type checker |
| 22 | [Blocking calls freeze the loop](#22-blocking-calls-freeze-the-event-loop) | Every task stalls at once | `asyncio.to_thread()` |
| 23 | [Catching `BaseException`](#23-catching-baseexception-breaks-cancellation) | `cancel()` and timeouts do nothing | Catch `Exception` |
| 24 | [Loop methods aren't thread-safe](#24-loop-methods-arent-thread-safe) | Callbacks run late, or never | `call_soon_threadsafe()` |
| 64 | [Breaking out of `async for`](#64-breaking-out-of-async-for-delays-cleanup) | Connections stay open after `break` | `contextlib.aclosing()` |
| 65 | [`asyncio.gather()` orphans siblings](#65-asynciogather-leaves-sibling-tasks-running-on-error) | Failed call still mutates state | `asyncio.TaskGroup` |
| | **Threading & Subprocesses** | | |
| 25 | [`+=` is not atomic](#25--is-not-atomic) | Lost updates | `threading.Lock` |
| 26 | [Exceptions in threads vanish](#26-exceptions-in-threads-vanish) | Failures with no traceback | Call `future.result()` |
| 27 | [`Lock` is not reentrant](#27-lock-is-not-reentrant) | Thread deadlocks on itself | `threading.RLock` |
| 28 | [`threading.local` in asyncio](#28-threadinglocal-leaks-between-asyncio-tasks) | One request sees another's data | `contextvars` |
| 29 | [`fork()` with threads running](#29-fork-copies-locked-locks) | Child process hangs forever | `spawn` / `forkserver` |
| 30 | [Daemon threads skip cleanup](#30-daemon-threads-skip-cleanup) | Unflushed data at exit | Stop event + `join()` |
| 66 | [`Popen.wait()` with `PIPE`](#66-subprocesspopenwait-deadlocks-when-a-pipe-fills) | Process hangs past ~64 KB output | `subprocess.run()` / `communicate()` |
| 67 | ["The GIL makes `dict` safe"](#67-the-gil-makes-dict-safe-fails-on-compound-operations) | Duplicate work, `RuntimeError` | Lock compound access |

---

## asyncio

### 20. Fire-and-Forget Tasks Get Garbage-Collected

`asyncio.create_task(job())` looks like "start this in the background". But the event loop keeps only a *weak* reference to tasks. If your code doesn't hold the returned task, the garbage collector can destroy it while it's still pending, and the work never completes. All you get is a `Task was destroyed but it is pending!` log line, if you're lucky.

```python
# The Trap
async def main():
    asyncio.create_task(send_heartbeats())  # Nothing keeps this task alive.
    ...
```

**Why:** A task parked on an `Event`, `Queue`, `Lock` or `Future` is only reachable through a reference cycle (task → coroutine → future → callback → task). A cycle with no outside reference is garbage. Tasks waiting on sockets or timers are usually held by the loop, which is why this is so intermittent.

**The fix:** Keep a strong reference until the task finishes, or use `asyncio.TaskGroup` (Python 3.11+), which owns its tasks.

```python
background_tasks = set()

task = asyncio.create_task(send_heartbeats())
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)
```

**In the wild:** This is the pattern the [asyncio docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task) recommend, and the one [Home Assistant's core](https://github.com/home-assistant/core/blob/dev/homeassistant/core.py) uses: `hass.async_create_task()` adds every task to `self._tasks` and removes it with `add_done_callback`, so integration authors never hold the reference themselves. Ruff's `RUF006` flags unstored `create_task` results.

[Example](../examples/20_asyncio_task_garbage_collected.py)

### 21. Forgetting `await` Silently Does Nothing

Calling an `async def` function doesn't run it. It returns a coroutine object, and if you don't `await` it, the body never executes. The line looks exactly like a normal function call.

```python
# The Trap
async def save(order):
    await db.insert(order)

async def checkout(order):
    save(order)  # Creates a coroutine and throws it away. Nothing is saved.
```

At best, Python prints `RuntimeWarning: coroutine 'save' was never awaited` when the coroutine is garbage-collected, which is easy to miss in production logs.

**The fix:** `await save(order)`. Type checkers catch this reliably (pyright's `reportUnusedCoroutine`, mypy's `unused-coroutine`).

Don't rely on `-W error::RuntimeWarning` alone. The warning is raised while the coroutine is being garbage-collected, where an exception can't propagate. Python prints it as `Exception ignored in: <coroutine ...>` and carries on with exit status 0. Under pytest, the warning only fails the test with both filters together, `-W error::RuntimeWarning -W error::pytest.PytestUnraisableExceptionWarning`, or with `filterwarnings = ["error"]` in your pytest config.

[Example](../examples/21_asyncio_forgotten_await.py)

### 22. Blocking Calls Freeze the Event Loop

asyncio is cooperative: a task gives up control only at an `await`. Any synchronous call that blocks, such as `time.sleep()`, `requests.get()`, file I/O, or a heavy computation, stops *every* task on the loop until it returns.

```python
# The Trap
async def handler():
    time.sleep(0.2)  # Every other task is frozen for 200 ms.
```

**The fix:** Use the async equivalent (`await asyncio.sleep()`, `aiohttp`, `httpx.AsyncClient`), or run blocking work in a thread with `await asyncio.to_thread(func, ...)`. Run with `PYTHONASYNCIODEBUG=1` during development: asyncio then logs any step that holds the loop for more than 100 ms.

**In the wild:** Home Assistant patches `time.sleep`, `open`, `os.listdir`, `importlib.import_module`, SSL certificate loading and more at startup ([`block_async_io.py`](https://github.com/home-assistant/core/blob/dev/homeassistant/block_async_io.py)), so any integration that calls them from the event loop is reported immediately. The `time.sleep` check was [added in 2022](https://github.com/home-assistant/core/pull/63766).

[Example](../examples/22_asyncio_blocking_call.py)

### 23. Catching `BaseException` Breaks Cancellation

`asyncio` cancels a task by raising `CancelledError` inside it. Since Python 3.8 that's a subclass of `BaseException`, not `Exception`. A bare `except:` or `except BaseException:` written to "never crash" also means "never cancel", and timeouts (`asyncio.timeout()`, `wait_for()`) are built on cancellation.

```python
# The Trap
async def poll_forever():
    while True:
        try:
            await fetch_quotes()
        except BaseException:  # Also catches CancelledError.
            log.exception("poll failed")

task.cancel()  # Logged, ignored. The loop keeps polling.
```

**The fix:** Catch `Exception`. If you really must catch `BaseException`, re-raise `CancelledError`:

```python
except asyncio.CancelledError:
    raise
except Exception:
    log.exception("poll failed")
```

[Example](../examples/23_asyncio_swallowed_cancellation.py)

### 24. Loop Methods Aren't Thread-Safe

Many libraries deliver callbacks on their own threads. Calling `loop.call_soon()`, `loop.create_task()` or any async API from such a thread is undefined behavior. The most visible symptom is that `call_soon()` queues the callback without waking the loop, so it sits there until something unrelated wakes the loop up, which could be seconds later or never.

```python
# The Trap
def on_message(msg):  # Called on the library's network thread.
    loop.call_soon(handle, msg)  # Queued, but the sleeping loop isn't woken.
```

In the example, the callback is delayed from 100 ms to 500 ms. With `loop.set_debug(True)`, asyncio raises `RuntimeError: Non-thread-safe operation invoked on an event loop other than the current one` instead.

**The fix:** Use `loop.call_soon_threadsafe(handle, msg)` for callbacks, or `asyncio.run_coroutine_threadsafe(coro, loop)` for coroutines. Both wake the loop immediately.

**In the wild:** Home Assistant's [Hikvision integration](https://github.com/home-assistant/core/pull/160027) updated entity state directly from its library's event-stream thread. The fix switched to a method that hops to the loop with `call_soon_threadsafe`. HA now raises on this mistake: core APIs call [`verify_event_loop_thread()`](https://github.com/home-assistant/core/blob/dev/homeassistant/core.py), which compares `threading.get_ident()` with the loop's thread.

[Example](../examples/24_asyncio_cross_thread_calls.py)

### 64. Breaking Out of `async for` Delays Cleanup

In CPython, breaking out of a synchronous generator loop drops its reference count to zero and runs its `finally` block right away. An async generator's `finally` may `await`, which synchronous `break` and garbage collection cannot do immediately. Breaking early out of `async for` leaves connections, locks or transactions inside the generator open until the loop shuts down (or a later GC pass schedules cleanup).

```python
# The Trap
async def stream_rows(db):
    conn = await db.acquire()
    try:
        async for row in conn.cursor():
            yield row
    finally:
        await conn.release()   # Not run when the caller breaks!

async for row in stream_rows(db):
    if row.id == target:
        break                  # conn stays checked out of the pool.
```

**The fix:** Wrap any async generator you might exit early in `contextlib.aclosing()` (Python 3.10+), which awaits `agen.aclose()` on block exit:

```python
async with contextlib.aclosing(stream_rows(db)) as rows:
    async for row in rows:
        if row.id == target:
            break
```

[Example](../examples/64_async_generator_cleanup.py)

### 65. `asyncio.gather()` Leaves Sibling Tasks Running on Error

`await asyncio.gather(validate(), charge_card())` looks like a single unit of work. Yet when `validate()` raises, `gather()` immediately propagates the exception to the caller *without cancelling* `charge_card()`. The sibling task keeps running in the background and can commit writes after your error handler has already returned a failure response.

```python
# The Trap
try:
    await asyncio.gather(validate(), charge_card())
except ValueError:
    return "order rejected"   # charge_card() is still running in the background!
```

**Why:** `gather()` waits on futures rather than owning task lifetimes, so raising early merely detaches the caller from the remaining tasks.

**The fix:** Use `asyncio.TaskGroup` (Python 3.11+), which cancels every remaining task and awaits their termination before exiting the `async with` block.

[Example](../examples/65_asyncio_gather_orphans.py)

---

## Threading & Subprocesses

### 25. `+=` Is Not Atomic

The GIL guarantees that only one thread runs Python bytecode at a time, not that a line of Python runs uninterrupted. `counter += 1` compiles to separate load, add and store instructions, and a thread switch between the load and the store loses the other thread's update.

```python
# The Trap
import dis
dis.dis("counter += 1")
#  LOAD_NAME   counter
#  LOAD_CONST  1
#  BINARY_OP   += (INPLACE_ADD before 3.11)
#  STORE_NAME  counter   <- another thread may have stored in between
```

The example widens the window with `time.sleep(0)` so the race shows every time. Two threads doing 1,000 increments each end up near 1,000 instead of 2,000. The free-threaded build (Python 3.13t and later) has no GIL at all, so races that were rare become common.

**The fix:** Guard shared read-modify-write with a `threading.Lock`, use `queue.Queue` to hand work between threads, or give each thread its own data and combine the results at the end.

[Example](../examples/25_thread_increment_not_atomic.py)

### 26. Exceptions in Threads Vanish

An exception in a `threading.Thread` prints a traceback to stderr and kills that thread, but `join()` returns normally and the main thread carries on. With `concurrent.futures`, it's quieter still: the exception is stored on the `Future` and nothing is printed at all.

```python
# The Trap
with ThreadPoolExecutor() as pool:
    pool.submit(process_batch, batch)  # If this raises, you'll never know.
```

**The fix:** Always collect results. `future.result()` re-raises the worker's exception in the caller. With many futures, iterate over `concurrent.futures.as_completed()` and call `.result()` on each. For raw threads, set `threading.excepthook` to route errors into your logging or alerting.

[Example](../examples/26_thread_exceptions_vanish.py)

### 27. `Lock` Is Not Reentrant

A `threading.Lock` doesn't know which thread holds it. If a function holding the lock calls a helper that also acquires it, the thread waits forever for itself.

```python
# The Trap
lock = threading.Lock()

def update_balance():
    with lock:
        audit()   # Deadlock.

def audit():
    with lock:
        ...
```

**The fix:** Use `threading.RLock`, which the owning thread can acquire repeatedly. Better still, structure code so locks are taken in one place: public methods lock, private helpers assume the lock is held.

[Example](../examples/27_lock_not_reentrant.py)

### 28. `threading.local` Leaks Between asyncio Tasks

`threading.local()` gives each *thread* its own storage, which is how many frameworks store "the current request". But every asyncio task runs on the same thread, so they all share one `threading.local`, and each task overwrites the others' values at every `await`.

```python
# The Trap
request = threading.local()

async def handle(user):
    request.user = user
    await asyncio.sleep(0)   # Another task runs and sets request.user.
    return request.user

await asyncio.gather(handle("alice"), handle("bob"))  # ['bob', 'bob']
```

**The fix:** Use `contextvars.ContextVar`. Each asyncio task runs in its own copy of the context, so values don't bleed between tasks. Context variables also work correctly with threads.

[Example](../examples/28_threading_local_in_asyncio.py)

### 29. `fork()` Copies Locked Locks

`os.fork()` copies the whole process memory, including every lock, but only the thread that called `fork()`. If another thread was holding a lock at that moment (inside `logging`, a connection pool, or `malloc` in a C extension), the child gets the lock in its locked state, and the thread that would release it doesn't exist in the child. The first time the child touches that lock, it hangs forever.

```python
# The Trap
threading.Thread(target=log_metrics_forever).start()   # Holds logging's lock now and then.
pool = multiprocessing.Pool()                          # fork() on Linux before 3.14.
# Child processes occasionally hang on their first log call.
```

**The fix:** Use the `spawn` or `forkserver` start method (`multiprocessing.get_context("forkserver")`), or create processes before starting any threads. Python 3.12 emits a `DeprecationWarning` when you fork a multi-threaded process, and since [Python 3.14](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods) no platform defaults to `fork`.

[Example](../examples/29_fork_with_lock_held.py) (POSIX only)

### 30. Daemon Threads Skip Cleanup

When the main thread exits, Python kills daemon threads abruptly. Their `finally` blocks and `with` exits never run, so buffers aren't flushed, files aren't closed and transactions aren't committed.

```python
# The Trap
def writer():
    try:
        while True:
            buffer.append(next_record())
    finally:
        flush(buffer)   # Never runs at interpreter exit.

threading.Thread(target=writer, daemon=True).start()
```

**The fix:** Use a normal thread with a stop signal, and join it on shutdown:

```python
stop = threading.Event()
t = threading.Thread(target=writer, args=(stop,))
t.start()
...
stop.set()
t.join()
```

[Example](../examples/30_daemon_threads_skip_cleanup.py)

### 66. `subprocess.Popen.wait()` Deadlocks When a Pipe Fills

`Popen(..., stdout=subprocess.PIPE)` redirects the child's output into an OS kernel buffer (typically 64 KB on Linux and macOS). Calling `proc.wait()` waits for the child to exit *without draining that pipe*. Small outputs fit in the buffer so every unit test passes; in production, a verbose response fills the pipe, the child blocks on `write()`, and the parent blocks on `wait()` forever.

```python
# The Trap
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
proc.wait()               # Hangs once stdout exceeds ~64 KB.
out = proc.stdout.read()
```

**The fix:** Use `subprocess.run(cmd, capture_output=True)` (or `out, err = proc.communicate()`), which drains `stdout` and `stderr` concurrently while waiting for exit. If you don't need the output, redirect to `subprocess.DEVNULL` instead of `PIPE`.

[Example](../examples/66_subprocess_pipe_deadlock.py)

### 67. "The GIL Makes `dict` Safe" Fails on Compound Operations

Because individual C-level `dict` lookups and stores happen while holding the GIL, Python lore often treats `dict` as "thread-safe without a lock". That abstraction leaks in three ways: check-then-set (`if k not in cache: cache[k] = ...`) races between the check and the store; mutating a `dict` while another thread iterates it raises `RuntimeError: dictionary changed size during iteration` even with the GIL on; and under free-threaded builds (`python3.13t` / `python3.14t`), the GIL is gone altogether.

```python
# The Trap
def get_user(uid):
    if uid not in cache:          # Thread B checks before Thread A stores...
        cache[uid] = fetch(uid)   # ...both run fetch(uid).
    return cache[uid]
```

**The fix:** Protect compound read-modify-write sequences and iteration snapshots (`list(shared.items())`) with a `threading.Lock`, regardless of whether the GIL is enabled.

[Example](../examples/67_freethreaded_gil_assumptions.py)
