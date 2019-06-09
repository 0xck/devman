import asyncio
import logging
from functools import partial
from os import getenv

from aiofile import AIOFile, Writer

from chat_common import get_logged_message, chat_connector, get_argparser, _non_empty_printable, run_client, _port, setup_general_log


reader_log = logging.getLogger("Chat reader")


async def read_chat(filename, chat_connector):

    assert bool(filename) and filename.isprintable(), AssertionError("Filename has to be non-empty printable.")

    async with AIOFile(filename, mode="a", encoding="utf-8") as file:
        writer = Writer(file)

        try:
            await chat_connector(writer)

            await file.fsync()

        except asyncio.CancelledError:
            await file.fsync()
            raise


async def read_write_lines(reader, _, writer):

    data = await reader.readline()

    while data:
        await writer(get_logged_message(data.decode("utf-8", "ignore")))
        data = await reader.readline()


def get_args():

    parser = get_argparser()

    parser.add_argument("-p", "--port", action="store", type=_port,
                        help="chat port, default is 5000",
                        default=int(getenv("CHAT_PORT", 5000)))

    parser.add_argument("-H", "--history", action="store", type=_non_empty_printable,
                        help="messages history, default is ./messages.history",
                        default=getenv("CHAT_HISTORY", "./messages.history"))

    return parser.parse_args()


if __name__ == '__main__':
    options = get_args()

    # logger settings
    log_level = options.loglevel * 10
    setup_general_log(options.log, log_level)
    reader_log.setLevel(log_level)

    connector = partial(chat_connector, options.host, options.port, options.delay, options.retries, read_write_lines)
    chat_handler = partial(read_chat, options.history, connector)

    reader_log.info(f"Chat reader is starting with options: {options}")
    run_client(chat_handler)
