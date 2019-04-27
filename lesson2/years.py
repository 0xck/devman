from async_tools import sleep_for
from curses_tools import draw_frame
from game_scenario import PHRASES


async def show_years(canvas, years):

    assert bool(years), AssertionError("Years has to be initiated with int value.")
    assert years[0] >= 1957, AssertionError("Years has to be at least 1957 and more.")

    height, width = canvas.getmaxyx()
    row = height // 2
    column = width // 2

    while True:

        year_frame = str(years[0]) + " " + PHRASES.get(years[0], "")

        frame_column = column - len(year_frame) // 2

        draw_frame(canvas, row, frame_column, year_frame)

        await sleep_for(15)

        draw_frame(canvas, row, frame_column, year_frame, negative=True)

        years[0] += 1
