import asyncio
from itertools import cycle

from curses_tools import draw_frame, get_frame_size, read_controls


async def handle_rocket(canvas, init_frames, timeout, row, column):

    assert bool(len(init_frames)), AssertionError("Frames can not be empty")
    assert all(ge(i, 0) for i in (row, column, timeout)), AssertionError(
        "row, column and timeout have to be non-negative")

    height, width = canvas.getmaxyx()

    frames = cycle(map(lambda frame: (frame, *get_frame_size(frame)), init_frames))

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
        if row_shift and (0 < (row + row_shift) < (height - rocket_height)):
            row += row_shift

        if col_shift and (1 < (column + col_shift) < (width - rocket_width)):
            column += col_shift

        frame, rocket_height, rocket_width = next(frames)
        draw_frame(canvas, row, column, frame)


def get_rocket_frames():

    raw_frames = ("rocket_frame_1.txt", "rocket_frame_2.txt")

    frames = [""] * len(raw_frames)

    for i, f in enumerate(raw_frames):
        with open(f, "r") as fd:
            frames[i] = (fd.read())

    if not all(frames):
        raise ValueError("Empty frame")

    return frames


def get_rocket(canvas, timeout):

    assert timeout >= 0, AssertionError("Timeout has to be non-negative")

    height, width = canvas.getmaxyx()

    rocket_frames = get_rocket_frames()

    return handle_rocket(
        canvas,
        rocket_frames,
        timeout,
        height - (2 + max(get_frame_size(i)[0] for i in rocket_frames)),
        width // 2)
