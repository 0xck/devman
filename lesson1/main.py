import curses
import time

from fire import fire
from rocket import get_rocket
from stars import get_stars


def play_the_game(canvas, tic):

    num_stars = 200

    border = ord('|')
    height, width = canvas.getmaxyx()

    # stars
    coroutines = list(get_stars(canvas, num_stars))
    # explosion
    coroutines.append(fire(canvas, height // 2, width // 2))
    # rocket
    coroutines.append(get_rocket(canvas, 1))

    # canvas stuff
    canvas.border(border, border)
    curses.curs_set(False)
    canvas.nodelay(True)

    # loop
    while coroutines:

        for i, coroutine in enumerate(coroutines):
            try:
                if coroutine is not None:
                    coroutine.send(None)

            except StopIteration:
                coroutines[i] = None

        canvas.refresh()
        time.sleep(tic)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(play_the_game, 0.1)
