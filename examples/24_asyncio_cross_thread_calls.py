"""Event loop methods are not thread-safe; call_soon from another thread can stall."""

import asyncio
import threading
import time


async def main():
    loop = asyncio.get_running_loop()

    # The trap: a library thread schedules a callback with call_soon.
    done = asyncio.Event()

    def library_callback():
        time.sleep(0.1)  # Make sure the loop is idle and waiting.
        loop.call_soon(done.set)  # Queued, but the sleeping loop is never woken.

    loop.call_later(0.5, lambda: None)  # Some unrelated timer wakes the loop later.
    threading.Thread(target=library_callback).start()
    start = time.monotonic()
    await done.wait()
    stalled = time.monotonic() - start
    print(f"call_soon from a thread took {stalled:.2f}s")  # ~0.50s, not ~0.10s
    assert stalled >= 0.4

    # In debug mode asyncio refuses outright.
    loop.set_debug(True)
    errors = []

    def debug_callback():
        try:
            loop.call_soon(done.set)
        except RuntimeError as e:
            errors.append(e)

    t = threading.Thread(target=debug_callback)
    t.start()
    t.join()
    loop.set_debug(False)
    assert errors, "expected RuntimeError in debug mode"

    # The fix: call_soon_threadsafe wakes the loop immediately.
    done = asyncio.Event()

    def library_callback_fixed():
        time.sleep(0.1)
        loop.call_soon_threadsafe(done.set)

    threading.Thread(target=library_callback_fixed).start()
    start = time.monotonic()
    await done.wait()
    assert time.monotonic() - start < 0.4


asyncio.run(main())
