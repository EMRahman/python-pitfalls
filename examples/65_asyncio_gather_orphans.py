"""asyncio.gather() propagates the first error without cancelling sibling tasks."""

import asyncio
import sys


async def validate(charging_started):
    await charging_started.wait()
    raise ValueError("invalid order")


async def charge_card(ledger, charging_started, release_charge):
    charging_started.set()
    # Hold the side effect until the caller has observed the validation failure.
    # Events make the ordering independent of event-loop speed or timer delays.
    await release_charge.wait()
    ledger.append("charged")


async def main():
    # The trap: validate() fails, gather() raises, and charge_card() keeps running!
    ledger = []
    charging_started = asyncio.Event()
    release_charge = asyncio.Event()
    t1 = asyncio.create_task(validate(charging_started))
    t2 = asyncio.create_task(charge_card(ledger, charging_started, release_charge))
    try:
        await asyncio.gather(t1, t2)
    except ValueError:
        pass
    else:
        raise AssertionError("expected validation failure")

    assert ledger == []
    assert not t2.done()  # gather() left its sibling alive after propagating the error.
    release_charge.set()
    await t2
    print(ledger)  # ['charged'] (the sibling finished after the error was handled!)
    assert ledger == ["charged"]

    # The fix (Python 3.11+): asyncio.TaskGroup cancels siblings before exiting `async with`.
    ledger_fixed = []
    charging_started = asyncio.Event()
    release_charge = asyncio.Event()
    if sys.version_info >= (3, 11):
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(validate(charging_started))
                charge = tg.create_task(charge_card(ledger_fixed, charging_started, release_charge))
        except Exception as exc:  # ExceptionGroup, with syntax that also parses on 3.10.
            assert len(exc.exceptions) == 1
            assert isinstance(exc.exceptions[0], ValueError)
        else:
            raise AssertionError("expected validation failure")
    else:
        tasks = [
            asyncio.create_task(validate(charging_started)),
            asyncio.create_task(charge_card(ledger_fixed, charging_started, release_charge)),
        ]
        charge = tasks[1]
        try:
            await asyncio.gather(*tasks)
        except ValueError:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            raise AssertionError("expected validation failure")

    assert charging_started.is_set()
    assert charge.cancelled()  # Cleanup finished before control returned to the caller.
    release_charge.set()
    assert ledger_fixed == []


asyncio.run(main())
