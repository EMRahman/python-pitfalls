"""Calling a coroutine function without `await` does nothing."""

import asyncio
import gc
import warnings

saved = []


async def save(order):
    saved.append(order)


async def main():
    # The trap
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        save("order-1")  # Creates a coroutine object and throws it away.
        gc.collect()

    print(saved)  # [] (the order was never saved)
    assert saved == []
    assert any("was never awaited" in str(w.message) for w in caught)

    # The fix
    await save("order-2")
    assert saved == ["order-2"]


asyncio.run(main())
