import asyncio
import curses
from itertools import chain, cycle
from random import choice, randint, sample


def rotator(seq, num):
    return chain(seq[num:len(seq)], seq[0:num])


async def blink(canvas, row, column, init_behavior, init_delay, symbol):

    behaviors = cycle(init_behavior)

    _, *star_attr = next(behaviors)

    canvas.addstr(row, column, symbol, *star_attr)

    # delay for randomizing time of start star's blinking
    for _ in range(init_delay):
        await asyncio.sleep(0)

    while True:

        timeout, *star_attr = next(behaviors)

        canvas.addstr(row, column, symbol, *star_attr)

        for _ in range(timeout):
            await asyncio.sleep(0)


def get_stars(canvas, num_starts):

    stars = '+*.:'

    height, width = canvas.getmaxyx()

    rows = cycle(sample(range(1, height - 1), height - 2))
    cols = cycle(sample(range(1, width - 1), width - 2))

    behavior = (
        (20, curses.A_DIM),
        (3, ),
        (5, curses.A_BOLD),
        (3, ))

    behaviors = (tuple(rotator(behavior, randint(-3, 3))) for _ in range(num_starts))

    return (
        blink(
            canvas,
            next(rows),
            next(cols),
            next(behaviors),
            randint(2, 26),
            choice(stars)
        ) for _ in range(num_starts))
