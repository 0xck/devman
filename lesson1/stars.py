import asyncio
import curses
from itertools import cycle, islice
from operator import ge
from random import choice, randint, sample


async def blink(canvas, row, column, behaviors, init_delay, symbol):

    assert all(ge(i, 0) for i in (row, column, init_delay)), AssertionError(
        "row, column and delay have to be non-negative")
    assert symbol.isprintable(), AssertionError("Star symbol has to be printable")

    # init star
    _, *star_attr = next(behaviors)
    canvas.addstr(row, column, symbol, *star_attr)

    # delay for randomizing time of start star's blinking
    for _ in range(init_delay):
        await asyncio.sleep(0)

    for timeout, *star_attr in behaviors:

        canvas.addstr(row, column, symbol, *star_attr)

        for _ in range(timeout):
            await asyncio.sleep(0)


def behavior(init_actions):

    actions = cycle(init_actions)

    while True:
        yield next(actions)


def get_stars(canvas, num_starts):

    assert num_starts > 0, AssertionError("Number of stars has to be at least 1")

    height, width = canvas.getmaxyx()

    assert num_starts <= round(height * width * 0.33), AssertionError(
        "Number of stars is too large, it has to be less or equal {}, this covers 33%% of canvas".format(round(height * width * 0.33)))

    stars = '+*.:'

    height_border = height - 1
    width_border = width - 1
    height_points = height_border - 1
    width_points = width_border - 1
    randomized_rows = sample(range(1, height_border), height_points)
    randomized_cols = sample(range(1, width_border), width_points)
    rows = cycle(randomized_rows)
    cols = cycle(randomized_cols)

    actions = (
        (20, curses.A_DIM),
        (3, ),
        (5, curses.A_BOLD),
        (3, ))

    actions_border = len(actions) - 1

    return (
        blink(
            canvas,
            next(rows),
            next(cols),
            # randomizing star state
            islice(behavior(actions), randint(0, actions_border), None),
            # randomizing star blinking
            randint(2, 26),
            choice(stars)
        ) for _ in range(num_starts))
