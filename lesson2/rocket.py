import asyncio
from itertools import cycle

from async_tools import sleep_for
from curses_tools import draw_frame, get_frame_size, read_controls
from explosion import explode
from fire import fire
from frames.tools import get_frames
from gameover import get_game_over
from physics import update_speed


async def animate_spaceship(init_frames, spaceship_frame, timeout):

    assert bool(len(init_frames)), AssertionError("Frames can not be empty")
    assert timeout >= 0, AssertionError("Timeout have to be non-negative")

    frames = ((frame, *get_frame_size(frame)) for frame in init_frames)

    for frame in cycle(frames):

        if None in spaceship_frame:
            return

        spaceship_frame[:] = frame[:]

        await sleep_for(timeout)


def calc_location(diff, border):

    if diff < 1:
        return 1

    if diff > border:
        return border

    return diff


async def run_spaceship(canvas, spaceship_frame, coroutines, obstacles,
                        obstacles_collisions, years, timeout, row, column):

    assert all(i >= 0 for i in (row, column, timeout)), AssertionError(
        "row, column and timeout have to be non-negative")
    assert bool(years), AssertionError("Years has to be initiated with int value.")

    height, width = canvas.getmaxyx()

    row_speed = 0
    column_speed = 0

    # "spinlock" waiting for updating spaceship_frame
    while not spaceship_frame:
        await asyncio.sleep(0)

    frame, rocket_height, rocket_width = spaceship_frame
    draw_frame(canvas, row, column, frame)

    while True:

        collisions = set(filter(lambda o: o.has_collision(row, column), obstacles))

        if collisions:
            obstacles_collisions.update(collisions)

            draw_frame(canvas, row, column, frame, negative=True)

            await explode(canvas, row, column)

            coroutines.append(get_game_over(canvas))

            spaceship_frame[0] = None

            return

        # handle a user control
        row_shift, col_shift, space = read_controls(canvas)

        draw_frame(canvas, row, column, frame, negative=True)

        row_speed, column_speed = update_speed(row_speed, column_speed, row_shift, col_shift)

        # keep rocket in borders
        row = calc_location(row + row_speed, height - rocket_height - 1)
        column = calc_location(column + column_speed, width - rocket_width - 1)

        # shoot
        if space and years[0] >= 2020:
            coroutines.append(fire(canvas, obstacles, obstacles_collisions, row - 1, column + 2, -2))

        frame, rocket_height, rocket_width = spaceship_frame
        draw_frame(canvas, row, column, frame)

        await asyncio.sleep(0)


def get_rocket_handlers(canvas, coroutines, obstacles,
                        obstacles_collisions, years, timeout):

    assert timeout >= 0, AssertionError("Timeout has to be non-negative")
    assert bool(years), AssertionError("Years has to be initiated with int value.")

    height, width = canvas.getmaxyx()

    rocket_frames = get_frames("frames/rocket/rocket_frame_[0-9].txt")

    spaceship_frame = []

    animate = animate_spaceship(rocket_frames, spaceship_frame, timeout)

    run = run_spaceship(
        canvas,
        spaceship_frame,
        coroutines,
        obstacles,
        obstacles_collisions,
        years,
        timeout,
        height - (2 + max(get_frame_size(i)[0] for i in rocket_frames)),
        width // 2)

    return [animate, run]
