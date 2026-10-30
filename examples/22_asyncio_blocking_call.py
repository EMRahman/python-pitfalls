"""A blocking call inside a coroutine freezes every other task on the loop."""

import asyncio
import time


async def main():
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.01)

    hb = asyncio.create_task(heartbeat())
    await asyncio.sleep(0)

    # The trap: time.sleep (or requests.get, or heavy CPU work) blocks the loop.
    before = ticks
    time.sleep(0.2)
    print(f"ticks during blocking sleep: {ticks - before}")  # 0
    assert ticks == before

    # The fix: await an async API, or push blocking work to a thread.
    before = ticks
    await asyncio.to_thread(time.sleep, 0.2)
    print(f"ticks during to_thread sleep: {ticks - before}")  # ~20
    assert ticks > before

    hb.cancel()


asyncio.run(main())
