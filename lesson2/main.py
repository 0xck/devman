import curses
import time

from fire import fire
from rocket import get_rocket
from stars import get_stars
from space_garbage import fill_orbit_with_garbage


def play_the_game(canvas, tic):

    assert tic > 0, AssertionError("Tic interval has to be more that 0")

    border = ord('|')

    height, width = canvas.getmaxyx()

    # number of starts covers 4% of canvas square
    num_stars = round(height * width * 0.04)

    # stars
    coroutines = list(get_stars(canvas, num_stars))
    # explosion
    coroutines.append(fire(canvas, height // 2, width // 2))
    # rocket
    coroutines.append(get_rocket(canvas, 1))
    # garbage
    coroutines.append(fill_orbit_with_garbage(canvas, coroutines, 10, 20))

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

    except Exception as exc:
        exit_msg = "Something went wrong, see details below:\n<{}>".format(
            exc)

    finally:

        if exit_msg:
            print(exit_msg)
