import asyncio
from contextlib import suppress


class GracefulExit(Exception):
    pass

class NonGracefulExit(Exception):
    pass


def raise_graceful(*args):
    # raises exception for graceful exiting
    raise GracefulExit()


def graceful_exit(loop, pending):
    # cancelling all tasks and waiting until they are done

    for task in pending:

        if not task.cancelled():
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
