import asyncio
from random import randint, choice

from async_tools import sleep_for
from curses_tools import draw_frame, get_frame_size
from frames.tools import get_frames


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Column position will stay same, as specified on start.

    E.g.
        with open('garbage.txt', "r") as garbage_file:
            frame = garbage_file.read()

        coroutine = fly_garbage(canvas, 10, frame):
    """

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:

        draw_frame(canvas, row, column, garbage_frame)

        await asyncio.sleep(0)

        draw_frame(canvas, row, column, garbage_frame, negative=True)

        row += speed

    # restore borders
    border = ord('|')
    canvas.border(border, border)


async def fill_orbit_with_garbage(canvas, coroutines, freq_min, freq_max):

    assert freq_min > 0 and freq_max > 0 and freq_min <= freq_max, AssertionError(
        "Frequencies has to be more that 0 and min <= max")

    _, width = canvas.getmaxyx()
    width -= 1

    garbage_frames = [(i, get_frame_size(i)[1]) for i in get_frames("frames/garbage/*.txt")]

    while True:

        frame, frame_width = choice(garbage_frames)
        column = randint(1, width - frame_width)

        coroutines.append(fly_garbage(canvas, column, frame, randint(2, 4) / 10))

        # random waiting before adding new one
        await sleep_for(randint(freq_min, freq_max))
