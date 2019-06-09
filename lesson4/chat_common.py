import argparse
import asyncio
import json
import logging
import signal
from datetime import datetime
from itertools import repeat
from os import getenv
from sys import exit

from exit_handler import GracefulExit, graceful_exit, raise_graceful


engine_log = logging.getLogger("Chat engine")


def decode_utf8(data):
    return data.decode("utf-8", "ignore")


def encode_utf8(data):
    return data.encode("utf-8", "ignore")


def get_logged_message(msg):

    time = datetime.now().strftime("%d.%m.%y %H:%M")

    return f'[{time}] {msg}'


async def chat_connector(address, port, delay, retry, chat_handler, writer):

    assert bool(address) and address.isprintable(), AssertionError("Address has to be non-empty printable.")
    assert 0 < int(port) < 65536, AssertionError("Port has to be in range 1-65535.")
    assert delay >= 0, AssertionError("Delay has to be positive.")
    assert retry is None or (isinstance(retry, int) and retry >= 0), AssertionError("Retries has to be None or positive int.")

    service_messages = {
        "established": f"Connection with {address}:{port} was established.",
        "terminated": f"Got termination, closing {address}:{port} connection.",
        "completed": f"Working with {address}:{port} was competed."}

    retries = repeat(None) if retry is None else range(-1, retry)

    wait_timeout = 0

    for attempt in retries:

        connect_writer = None

        try:
            connect_reader, connect_writer = await asyncio.open_connection(address, int(port))

            engine_log.info(service_messages["established"])
            await writer(get_logged_message(f"{service_messages['established']}\n"))

            result = await chat_handler(connect_reader, connect_writer, writer)
            engine_log.info(service_messages["completed"])
            await writer(get_logged_message(f"{service_messages['completed']}\n"))
            return result

        except (ConnectionRefusedError, ConnectionResetError):

            current_attempt = '' if retry is None else attempt + 1
            engine_log.warning(
                f"Connection error, trying to reconnect. Next attempt{current_attempt} in {wait_timeout} seconds.")

            await writer(get_logged_message("Connection error, trying to reconnect.\n"))

            await asyncio.sleep(wait_timeout)
            wait_timeout = wait_timeout or delay

        except asyncio.CancelledError:
            engine_log.info(service_messages["terminated"])
            await writer(get_logged_message(f"{service_messages['terminated']}\n"))

            raise

        finally:
            if connect_writer is not None:
                connect_writer.close()

    else:
        engine_log.warning("Retrying limit was reached, exiting...")
        await writer(get_logged_message("Retrying limit was reached, exit.\n"))


def setup_general_log(file, level):

    logging.basicConfig(filename=file,
                        format="[%(asctime)s] %(levelname)s / %(funcName)s / %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    engine_log.setLevel(level)


def _non_empty_printable(string):

    if not string or not string.isprintable():
        raise argparse.ArgumentError(
            "Argument has to be printable non-empty string.")

    return string


def _port(port):

    exception = argparse.ArgumentError

    try:
        port = int(port)
    except ValueError:
        raise exception

    if not 0 < port < 65536:
        raise exception

    return port


def _positive_number(number):

    exception = argparse.ArgumentError

    try:
        number = float(number)
    except ValueError:
        raise exception

    if number < 0.0:
        raise exception

    return number


def _retries(retries):

    if retries.lower() == "forever":
        return None

    if retries.isdigit():
        return int(retries)

    raise argparse.ArgumentError("Retries has to be positive number or word `forever`.")


def get_argparser():

    parser = argparse.ArgumentParser(description="Secret chat client.")

    parser.add_argument("-l", "--log", action="store",
                        help="log file path, default is console output",
                        default=getenv("CHAT_LOG", None))

    parser.add_argument("-f", "--loglevel", action="store", type=int, choices=range(1, 6), metavar="{1-5}",
                        help="log facility level, default is 2: ERROR",
                        default=int(getenv("CHAT_LOGLEVEL", 2)))

    parser.add_argument("-s", "--host", action="store", type=_non_empty_printable,
                        help="server hostname, default is 127.0.0.1",
                        default=getenv("CHAT_HOST", "127.0.0.1"))

    parser.add_argument("-d", "--delay", action="store", type=_positive_number,
                        help="delay of reconnection attempt in seconds, default is 1. Fractions, e.g. 0.1, may be used for ms.",
                        default=float(getenv("CHAT_DELAY", 1)))

    parser.add_argument("-r", "--retries", action="store", type=_retries, metavar="{positive number | word `forever`}",
                        help="number of retries, default is 3",
                        default=getenv("CHAT_RETRIES", 3))

    return parser


def run_client(client):

    loop = asyncio.get_event_loop()

    # handling SIGTERM
    signal.signal(signal.SIGTERM, raise_graceful)

    try:
        loop.run_until_complete(client())

    except (KeyboardInterrupt, GracefulExit):
        engine_log.info("Termination detected, exiting...")
        pending = asyncio.Task.all_tasks()
        graceful_exit(loop, pending)

    except json.JSONDecodeError:
        engine_log.error(f"An error occurred, see logs above, aborting...")
        exit(2)

    except Exception as exc:
        engine_log.exception(f"Unknown exception was handled, aborting... {exc}")
        exit(1)

    finally:
        loop.close()
