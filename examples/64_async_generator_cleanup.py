"""Breaking out of `async for` leaves an async generator's `finally` suspended."""

import asyncio
from contextlib import aclosing


def sync_records(state):
    state["open"] = True
    try:
        yield 1
        yield 2
    finally:
        state["open"] = False


async def async_records(state):
    state["open"] = True
    try:
        yield 1
        yield 2
    finally:
        await asyncio.sleep(0)
        state["open"] = False


async def main():
    # In CPython, breaking out of a sync generator closes it immediately when refcount hits 0.
    sync_state = {"open": False}
    for _ in sync_records(sync_state):
        break
    assert sync_state["open"] is False

    # The trap: breaking out of `async for` cannot `await` cleanup synchronously,
    # so resources stay open until GC or loop shutdown.
    async_state = {"open": False}
    agen = async_records(async_state)
    async for _ in agen:
        break
    print(f"still open after break: {async_state['open']}")  # True
    assert async_state["open"] is True
    await agen.aclose()  # Clean up explicitly for this demo.

    # The fix: wrap the async generator in contextlib.aclosing().
    fixed_state = {"open": False}
    async with aclosing(async_records(fixed_state)) as agen:
        async for _ in agen:
            break
    assert fixed_state["open"] is False


asyncio.run(main())
