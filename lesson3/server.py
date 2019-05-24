import argparse
import asyncio
import logging
import os.path
from enum import Enum
from functools import partial
from glob import iglob
from os import getenv
from shutil import which
from uuid import uuid4

import aiofiles
from aiohttp import web

from exceptions import CompressorIsNotAvailable


class Compressors(Enum):
    ZIP = ("zip -9 -r -q - ", "zip", bool(which("zip")))
    GZ = ("tar --absolute-names -czf - ", "tar.gz", bool(which("tar")))

    def __init__(self, command, extension, installed):
        self.command = command
        self.extension = extension
        self.installed = installed


def get_headers(filename, extension):

    assert filename.isprintable() and extension.isprintable(), AssertionError(
        "Filename and extension have to be printable string.")
    assert bool(filename), AssertionError("Filename can not be empty.")

    return {
        'Content-Type': 'application/octet-stream',
        'Content-Encoding': extension,
        'Content-Disposition': f'attachment; filename="{filename}.{extension}"'}


def is_valid_path(root, path):

    assert root.isprintable() and path.isprintable(), AssertionError(
        "Root path and path have to be printable string.")
    assert bool(path), AssertionError("Path can not be empty.")

    if path in (".", ".."):
        return False

    full_path = os.path.normpath(os.path.join(root, path))
    if full_path == root or os.path.dirname(full_path) != root:
        return False

    return True


def get_request_id_msg(request_id, message):
    return f"Request ID {request_id}: <{message}>"


async def archivate_files(loop, arch_cmd, chunk_size, headers, files_root, delay, request):

    assert chunk_size > 0, AssertionError("Chunk size has to be more than 0.")
    assert delay >= 0.0, AssertionError("Delay has to be positive.")
    assert bool(arch_cmd), AssertionError("Compress' command line has to be defined.")
    assert bool(files_root), AssertionError("File's root path has to be defined.")

    archive_hash = request.match_info['archive_hash']
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    log_message = partial(get_request_id_msg, request_id)

    logging.debug(log_message(f"Handling request for: {archive_hash}"))

    if not is_valid_path(files_root, archive_hash):
        logging.debug(log_message(f"Wrong request: {archive_hash}"))

        raise web.HTTPBadRequest(
            text=f"Archive <{archive_hash}> is not allowed.")

    path = os.path.join(files_root, archive_hash)
    if not os.path.exists(path):
        logging.debug(log_message(f"Non-existed request: {archive_hash}"))

        raise web.HTTPNotFound(
            text=f"Archive <{archive_hash}> does not exist or was deleted.")

    response = web.StreamResponse()
    response.headers.extend(headers)
    response.enable_chunked_encoding()
    response.headers["X-Request-ID"] = request_id
    logging.debug(log_message(f"Updating headers with: {headers} and set one chunked"))

    await response.prepare(request)

    files = ' '.join(iglob(os.path.join(path, "*")))
    cmd = arch_cmd + files
    logging.debug(log_message(f"Read data compressor: {arch_cmd} via {chunk_size} bytes chunks"))
    logging.debug(log_message(f"Files for compressing: {files}"))

    try:
        proc = await asyncio.create_subprocess_shell(cmd, loop=loop,
                                            stdout=asyncio.subprocess.PIPE,
                                            stdin=asyncio.subprocess.DEVNULL,
                                            stderr=asyncio.subprocess.DEVNULL)
        logging.debug(log_message(f"Compressor pid: {proc.pid}"))

    except asyncio.CancelledError:
        logging.debug(log_message("Stopping request handling, due cancellation"))
        raise

    except Exception as exc:
        logging.exception(exc)

        raise web.HTTPInternalServerError()

    logging.debug(log_message("Writing was started"))
    try:
        archive_chunk = await proc.stdout.read(chunk_size)
        logging.debug(log_message(f"Read {len(archive_chunk)} bytes to archive chunk"))

        while archive_chunk:

            logging.debug(log_message(f"Writing {len(archive_chunk)} bytes archive chunk"))
            await response.write(archive_chunk)
            logging.debug(log_message("Archive chunk was written"))

            if delay:
                logging.debug(log_message(f"Additional delay {delay} s"))
                await asyncio.sleep(delay)

            archive_chunk = await proc.stdout.read(chunk_size)
            logging.debug(log_message(f"Read {len(archive_chunk)} bytes to archive chunk"))

        logging.debug(log_message("Writing was completed"))

    except asyncio.CancelledError:
        response.force_close()
        logging.debug(log_message("Request handling was stopped, due cancellation"))
        raise

    finally:
        # waiting for last read attempt for gracefull cancel
        await proc.stdout.read(chunk_size)

        if proc.returncode is None:
            logging.debug(log_message(f"Compressor pid: {proc.pid} needs to be terminated"))
            proc.terminate()
            await proc.wait()

        if proc.returncode is None:
            logging.debug(log_message(f"Compressor pid: {proc.pid} was not terminated and needs to be killed"))
            proc.kill()
            await proc.wait()

            logging.debug(log_message(f"Compressor pid: {proc.pid} was killed. Return code {proc.returncode}"))
        else:
            logging.debug(log_message(f"Compressor pid: {proc.pid} was terminated. Return code {proc.returncode}"))


async def handle_index_page(request):

    logging.debug(f"Handling root access")

    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()

    return web.Response(text=index_contents, content_type='text/html')


def _non_empty_printable(string):

    if not string or not string.isprintable():
        raise argparse.ArgumentError(
            "Files root path has to be printable non-empty string.")

    return string


def _natural_number(number):

    exception = argparse.ArgumentError("Chunk size has to be more than 0.")

    try:
        number = int(number)
    except ValueError:
        raise exception

    if number < 1:
        raise exception

    return number


def _positive_number(number):

    exception = argparse.ArgumentError("Delay has to be positive.")

    try:
        number = float(number)
    except ValueError:
        raise exception

    if number < 0.0:
        raise exception

    return number


def grab_args():

    parser = argparse.ArgumentParser(description='Files downloader web app')
    parser.add_argument('-l', '--log', action='store',
                        help='log file path, default is console output',
                        default=getenv("FDWA_LOG", None))
    parser.add_argument('-f', '--loglevel', action='store', type=int, choices=range(1, 6), metavar="{1-5}",
                        help='log facility level, default is 2: ERROR',
                        default=int(getenv("FDWA_LOGLEVEL", 2)))
    parser.add_argument('-r', '--filesroot', action='store', type=_non_empty_printable,
                        help='files root directory, default is ./files',
                        default=getenv("FDWA_FILESROOT", "./files"))
    parser.add_argument('-d', '--delay', action='store', type=_positive_number,
                        help='delay during sending file in seconds, default is 0, no delay. Fractions, e.g. 0.1, may be used for ms.',
                        default=float(getenv("FDWA_DELAY", 0)))
    parser.add_argument('-s', '--chunksize', action='store', type=_natural_number,
                        help='chunk size, default is 32768',
                        default=int(getenv("FDWA_CHUNKSIZE", (32 * 1024))))
    parser.add_argument('-c', '--compressor', action='store', choices=["zip", "gz"], metavar="{zip, gz}",
                        help='compression type, default is zip',
                        default=getenv("FDWA_COMPRESSOR", "zip"))

    return parser.parse_args()


def setup_web_app(options):

    compressor = Compressors[options.compressor.upper()]
    if not compressor.installed:
        raise CompressorIsNotAvailable("Check if compressor's binaries are in the $PATH.")

    headers = get_headers("archive", compressor.extension)
    app = web.Application()
    archivate = partial(archivate_files, app.loop, compressor.command,
                        options.chunksize, headers, os.path.normpath(options.filesroot),
                        options.delay)

    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate)])

    return app


if __name__ == '__main__':

    options = grab_args()

    # logging settings
    logging.basicConfig(filename=options.log, level=(options.loglevel * 10),
                        format='[%(asctime)s] %(levelname)s / %(funcName)s / %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    logging.info(f"Files downloader web app is starting with options: {options}")

    app = setup_web_app(options)

    web.run_app(app)
