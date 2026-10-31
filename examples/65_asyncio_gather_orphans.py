"""asyncio.gather() propagates the first error without cancelling sibling tasks."""

import asyncio
import sys


async def validate():
    await asyncio.sleep(0.01)
    raise ValueError("invalid order")


async def charge_card(ledger):
    await asyncio.sleep(0.03)
    ledger.append("charged")


async def main():
    # The trap: validate() fails, gather() raises, and charge_card() keeps running!
    ledger = []
    t1 = asyncio.create_task(validate())
    t2 = asyncio.create_task(charge_card(ledger))
    try:
        await asyncio.gather(t1, t2)
    except ValueError:
        pass

    assert ledger == []  # Nothing charged yet when the exception handler runs...
    await asyncio.sleep(0.04)
    print(ledger)  # ['charged'] (...the sibling finished in the background!)
    assert ledger == ["charged"]
    await t2

    # The fix (Python 3.11+): asyncio.TaskGroup cancels siblings before exiting `async with`.
    ledger_fixed = []
    if sys.version_info >= (3, 11):
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(validate())
                tg.create_task(charge_card(ledger_fixed))
        except Exception:  # Catches ExceptionGroup(ValueError) while staying 3.10-parseable.
            pass
    else:
        tasks = [asyncio.create_task(validate()), asyncio.create_task(charge_card(ledger_fixed))]
        try:
            await asyncio.gather(*tasks)
        except ValueError:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    await asyncio.sleep(0.04)
    assert ledger_fixed == []


asyncio.run(main())
