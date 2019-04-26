import asyncio


async def sleep_for(tics):

    assert tics >= 0, AssertionError("Tics has to be positive")

    # if 0 then perform sleep once anyway
    if not tics:
        await asyncio.sleep(0)
        return

    for _ in range(tics):
        await asyncio.sleep(0)
