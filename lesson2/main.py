import curses
import time

from fire import fire
from obstacles import show_obstacles
from rocket import get_rocket_handlers
from stars import get_stars
from space_garbage import fill_orbit_with_garbage


def play_the_game(canvas, tic, print_obstacles=False):

    assert tic > 0, AssertionError("Tic interval has to be more that 0")

    border = ord('|')

    height, width = canvas.getmaxyx()

    # number of starts covers 4% of canvas square
    num_stars = round(height * width * 0.04)

    # fill coroutines
    coroutines = []
    # obstacles list
    obstacles = set()
    obstacles_collisions = set()
    # stars
    coroutines.extend(list(get_stars(canvas, num_stars)))
    # rocket
    coroutines.extend(get_rocket_handlers(canvas, coroutines, obstacles, obstacles_collisions, 1))
    # garbage handler
    coroutines.append(fill_orbit_with_garbage(canvas, coroutines, obstacles, obstacles_collisions, 10, 20))
    # print garbage borders
    if print_obstacles:
        coroutines.append(show_obstacles(canvas, obstacles))
    # explosion
    coroutines.append(fire(canvas, obstacles, obstacles_collisions, height // 2, width // 2))

    # canvas stuff
    canvas.border(border, border)
    curses.curs_set(False)
    canvas.nodelay(True)

    # loop
    while coroutines:

        for i, coroutine in enumerate(coroutines):

            try:
                coroutine.send(None)

            except StopIteration:
                coroutines.pop(i)

        canvas.refresh()
        time.sleep(tic)


if __name__ == '__main__':

    exit_msg = ""

    try:
        curses.update_lines_cols()
        curses.wrapper(play_the_game, 0.1)

    except KeyboardInterrupt:
        exit_msg = "CTRL+C pressed, exiting..."

    # except Exception as exc:
    #     exit_msg = "Something went wrong, see details below:\n<{}>".format(
    #         exc)

    finally:

        if exit_msg:
            print(exit_msg)
