"""Catching BaseException (or a bare except) swallows CancelledError."""

import asyncio

stop = False


async def stubborn():
    while not stop:
        try:
            await asyncio.sleep(0.01)
        except BaseException:  # Same problem with a bare `except:`
            pass  # "Never crash" also means "never cancel".


async def cooperative():
    while True:
        try:
            await asyncio.sleep(0.01)
        except Exception:  # CancelledError is a BaseException, so it passes through.
            pass


async def main():
    global stop

    # The trap
    task = asyncio.create_task(stubborn())
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.sleep(0.05)
    print(f"cancelled task still running: {not task.done()}")  # True
    assert not task.done()
    stop = True
    await task

    # The fix: catch Exception, or re-raise CancelledError.
    task = asyncio.create_task(cooperative())
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert task.cancelled()


asyncio.run(main())
