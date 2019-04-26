import asyncio

from frames.tools import get_frames
from curses_tools import draw_frame, get_frame_size


async def game_over(canvas, frame):

    assert bool(frame), AssertionError("Frame can not be empty")

    frame_height, frame_width = get_frame_size(frame)

    height, width = canvas.getmaxyx()
    row = height // 2 - frame_height // 2
    column = width // 2 - frame_width // 2

    draw_frame(canvas, row, column, frame)

    while True:
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, frame)


def get_game_over(canvas):

    frame = get_frames("frames/gameover/gameover.txt")

    return game_over(canvas, frame[0])
