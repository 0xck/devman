import asyncio
from random import choice, randint

from async_tools import sleep_for
from curses_tools import draw_frame, get_frame_size
from explosion import explode
from frames.tools import get_frames
from game_scenario import get_garbage_delay_tics
from obstacles import Obstacle


async def fly_garbage(canvas, obstacles, obstacles_collisions,
                      column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Column position will stay same, as specified on start.

    E.g.
        with open('garbage.txt', "r") as garbage_file:
            frame = garbage_file.read()

        coroutine = fly_garbage(canvas, 10, frame):
    """

    assert speed > 0, AssertionError("Speed has to be positive")
    assert len(garbage_frame) and all(garbage_frame), AssertionError(
        "Frame can not be empty or has 0 height or width")

    frame, frame_height, frame_width = garbage_frame

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)
    row = 0

    obstacle = Obstacle(row, column, frame_height, frame_width)
    obstacles.add(obstacle)

    while row < rows_number:

        if obstacle in obstacles_collisions:
            draw_frame(canvas, row, column, frame, negative=True)

            await explode(canvas, row, column)

            break

        draw_frame(canvas, row, column, frame)

        await asyncio.sleep(0)

        draw_frame(canvas, row, column, frame, negative=True)

        row += speed

        obstacle.row = row

    # delete obstacle
    obstacles.discard(obstacle)

    # restore borders
    border = ord('|')
    canvas.border(border, border)


async def fill_orbit_with_garbage(canvas, coroutines, obstacles,
                                  obstacles_collisions, years):

    assert bool(years), AssertionError("Years has to be initiated with int value.")
    assert years[0] >= 1957, AssertionError("Years has to be at least 1957 and more.")

    _, width = canvas.getmaxyx()
    width -= 1

    garbage_frames = [(i, *get_frame_size(i)) for i in get_frames("frames/garbage/*.txt")]

    # waiting for garbage epoch
    while get_garbage_delay_tics(years[0]) is None:
        await asyncio.sleep(0)

    while True:

        frame = choice(garbage_frames)
        _, _, frame_width = frame
        column = randint(1, width - frame_width)
        speed = randint(1, 4) / 10

        coroutines.append(fly_garbage(canvas, obstacles, obstacles_collisions,
                                      column, frame, speed))

        # waiting before adding new one
        await sleep_for(get_garbage_delay_tics(years[0]))
