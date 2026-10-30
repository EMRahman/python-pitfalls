"""The event loop only keeps a weak reference to tasks, so an unreferenced task can vanish."""

import asyncio
import gc
import weakref


async def worker():
    # Waits on a future that nothing outside this task refers to.
    await asyncio.get_running_loop().create_future()


async def main():
    # The trap: fire-and-forget without keeping the task.
    task_ref = weakref.ref(asyncio.create_task(worker()))
    await asyncio.sleep(0)  # Let it start and suspend.
    gc.collect()
    print(task_ref())  # None (the pending task was destroyed)
    assert task_ref() is None

    # The fix: hold a strong reference until the task finishes.
    background_tasks = set()
    task = asyncio.create_task(worker())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    task_ref = weakref.ref(task)
    del task
    await asyncio.sleep(0)
    gc.collect()
    assert task_ref() is not None

    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)


asyncio.run(main())
