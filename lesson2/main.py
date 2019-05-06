import curses
import sys
import time

from fire import fire
from obstacles import show_obstacles
from rocket import get_rocket_handlers
from space_garbage import fill_orbit_with_garbage
from stars import get_stars
from years import show_years, years_increment


def play_the_game(canvas_init, tic, print_obstacles=False):

    assert tic > 0, AssertionError("Tic interval has to be more that 0")

    border = ord('|')

    # set main canvas
    height_init, width_init = canvas_init.getmaxyx()
    canvas = canvas_init.derwin(height_init - 2, width_init, 0, 0)
    height, width = canvas.getmaxyx()

    # set years canvas
    canvas_year = canvas_init.derwin(height_init - 1, 0)

    # number of starts covers 4% of canvas square
    num_stars = round(height * width * 0.04)

    coroutines = []
    # obstacles
    obstacles = set()
    obstacles_collisions = set()
    years = [1957]

    # fill coroutines
    # years
    coroutines.append(years_increment(years))
    coroutines.append(show_years(canvas_year, years))
    # stars
    coroutines.extend(list(get_stars(canvas, num_stars)))
    # rocket
    coroutines.extend(get_rocket_handlers(canvas, coroutines, obstacles, obstacles_collisions, years, 1))
    # garbage handler
    coroutines.append(fill_orbit_with_garbage(canvas, coroutines, obstacles, obstacles_collisions, years))
    # print garbage borders
    if print_obstacles:
        coroutines.append(show_obstacles(canvas, obstacles))
    # explosion
    coroutines.append(fire(canvas, obstacles, obstacles_collisions, height // 2, width // 2))

    # canvas stuff
    canvas.keypad(True)
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
        canvas_year.refresh()

        time.sleep(tic)


if __name__ == '__main__':

    exit_msg = ""
    exit_code = 0

    try:
        curses.update_lines_cols()
        curses.wrapper(play_the_game, 0.1)

    except KeyboardInterrupt:
        exit_msg = "CTRL+C pressed, exiting..."

    except Exception as exc:
        exit_msg = "Something went wrong, see details below:\n<{}>".format(
            exc)
        exit_code = 1

    finally:

        if exit_msg:

            output = sys.stderr if exit_code else sys.stdout
            print(exit_msg, file=output)

            sys.exit(exit_code)
