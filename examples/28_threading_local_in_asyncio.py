"""threading.local is shared by every asyncio task on the same thread."""

import asyncio
import contextvars
import threading

# The trap
request = threading.local()


async def handle(user):
    request.user = user
    await asyncio.sleep(0)  # Another task runs and overwrites request.user.
    return request.user


async def main():
    return await asyncio.gather(handle("alice"), handle("bob"))


results = asyncio.run(main())
print(results)  # ['bob', 'bob'] (alice's request now belongs to bob)
assert results == ["bob", "bob"]

# The fix: contextvars gives each task its own copy.
current_user = contextvars.ContextVar("current_user")


async def handle_fixed(user):
    current_user.set(user)
    await asyncio.sleep(0)
    return current_user.get()


async def main_fixed():
    return await asyncio.gather(handle_fixed("alice"), handle_fixed("bob"))


assert asyncio.run(main_fixed()) == ["alice", "bob"]
