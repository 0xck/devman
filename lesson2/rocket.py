import asyncio
from itertools import cycle

from curses_tools import draw_frame, get_frame_size, read_controls
from frames.tools import get_frames


async def handle_rocket(canvas, init_frames, timeout, row, column):

    assert bool(len(init_frames)), AssertionError("Frames can not be empty")
    assert all(i >= 0 for i in (row, column, timeout)), AssertionError(
        "row, column and timeout have to be non-negative")

    height, width = canvas.getmaxyx()

    frames_list = ((frame, *get_frame_size(frame)) for frame in init_frames)

    frames = cycle(frames_list)

    frame, rocket_height, rocket_width = next(frames)

    draw_frame(canvas, row, column, frame)

    while True:

        for _ in range(timeout):
            await asyncio.sleep(0)
            # against stars that redraw canvas in other coroutines
            draw_frame(canvas, row, column, frame)

        # handle a user control
        row_shift, col_shift, _ = read_controls(canvas)

        draw_frame(canvas, row, column, frame, negative=True)

        # keep rocket in borders
        if row_shift and 0 < row + row_shift < height - rocket_height:
            row += row_shift

        if col_shift and 1 < column + col_shift < width - rocket_width:
            column += col_shift

        frame, rocket_height, rocket_width = next(frames)
        draw_frame(canvas, row, column, frame)


def get_rocket(canvas, timeout):

    assert timeout >= 0, AssertionError("Timeout has to be non-negative")

    height, width = canvas.getmaxyx()

    rocket_frames = get_frames("frames/rocket/rocket_frame_[0-9].txt")

    return handle_rocket(
        canvas,
        rocket_frames,
        timeout,
        height - (2 + max(get_frame_size(i)[0] for i in rocket_frames)),
        width // 2)
