import asyncio
import logging
import os.path
from enum import Enum
from functools import partial
from glob import iglob
from shutil import which

import aiofiles
from aiohttp import web


class Compressors(Enum):
    zip = ("zip -9 -r -q - ", "zip", bool(which("zip")))
    gz = ("tar --absolute-names -czf - ", "tar.gz", bool(which("tar")))

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
        'Content-Disposition': f'attachment; filename="{filename + "." + extension}"'}


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


async def archivate_photos(loop, arch_cmd, chunk_size, headers, files_root, delay, request):

    assert chunk_size > 0, AssertionError("Chunk size has to be more than 0.")
    assert delay >= 0.0, AssertionError("Delay has to be positive.")
    assert bool(arch_cmd), AssertionError("Compress' command line has to be defined.")
    assert bool(files_root), AssertionError("File's root path has to be defined.")

    archive_hash = request.match_info['archive_hash']

    logging.debug(f"Handling request for: {archive_hash}")

    if not is_valid_path(files_root, archive_hash):
        logging.debug(f"Wrong request: {archive_hash}")

        raise web.HTTPBadRequest(
            text=f"Archive <{archive_hash}> is not allowed.")

    path = os.path.join(files_root, archive_hash)

    if not os.path.exists(path):
        logging.debug(f"Non-existed request: {archive_hash}")

        raise web.HTTPNotFound(
            text=f"Archive <{archive_hash}> does not exist or was deleted.")

    logging.debug(f"Updating headers with: {headers} and set one chunked")

    response = web.StreamResponse()
    response.headers.extend(headers)
    response.enable_chunked_encoding()

    await response.prepare(request)

    files = ' '.join(iglob(os.path.join(path, "*.jpg")))

    cmd = arch_cmd + files

    logging.debug(f"Read data compressor: {arch_cmd} via {chunk_size} bytes chunked")
    logging.debug(f"Files for compressing: {files}")

    try:
        proc = await asyncio.create_subprocess_shell(cmd, loop=loop,
                                            stdout=asyncio.subprocess.PIPE,
                                            stdin=asyncio.subprocess.DEVNULL,
                                            stderr=asyncio.subprocess.DEVNULL)
    except asyncio.CancelledError:
        logging.debug("Stopping request handling")
        raise

    except Exception as exc:
        logging.exception(exc)

        raise web.HTTPInternalServerError()

    logging.debug(f"Compressor pid: {proc.pid}")

    try:
        logging.debug("Reading archive chunk")

        archive_chunk = await proc.stdout.read(chunk_size)

        logging.debug(f"Read {len(archive_chunk)} bytes to archive chunk")

        while archive_chunk:

            logging.debug(f"Writing {len(archive_chunk)} bytes archive chunk")

            await response.write(archive_chunk)

            logging.debug("Archive chunk was written")

            if delay:
                logging.debug("Additional delay")
                await asyncio.sleep(delay)

            logging.debug("Reading archive chunk")

            archive_chunk = await proc.stdout.read(chunk_size)

            logging.debug(f"Read {len(archive_chunk)} bytes to archive chunk")

        logging.debug("Writing was completed")

    except asyncio.CancelledError:
        logging.debug("Stopping request handling")

        response.force_close()

        logging.debug("Request handling was stopped")

        raise

    finally:
        # waiting for last read attempt for gracefull cancel
        logging.debug("Waiting cancellation archive chunk")

        await proc.stdout.read(chunk_size)

        logging.debug("Getting cancellation archive chunk was done")

        if proc.returncode is None:
            logging.debug(f"Compressor pid: {proc.pid} needs to be terminated")

            proc.terminate()
            await proc.wait()

        if proc.returncode is None:
            logging.debug(f"Compressor pid: {proc.pid} was not terminated and needs to be killed")

            proc.kill()
            await proc.wait()

            logging.debug(f"Compressor pid: {proc.pid} was killed. Return code {proc.returncode}")
        else:
            logging.debug(f"Compressor pid: {proc.pid} was terminated. Return code {proc.returncode}")


async def handle_index_page(request):

    logging.debug(f"Handling root access")

    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()

    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':

    import argparse
    from os import getenv
    from exceptions import CompressorIsNotAvailable

    def non_empty_printable(string):
        if not string or not string.isprintable():
            raise argparse.ArgumentError(
                "Photos root path has to be printable non-empty string.")
        return string

    def natural_number(number):
        number = int(number)
        if number < 1:
            raise argparse.ArgumentError("Chunk size has to be more than 0.")
        return number

    def positive_number(number):
        number = float(number)
        if number < 0.0:
            raise argparse.ArgumentError("Delay has to be positive.")
        return number

    parser = argparse.ArgumentParser(description='Photos downloader web app')
    parser.add_argument('-l', '--log', action='store', help='log file path',
                        default=getenv("PDWA_LOG", None))
    parser.add_argument('-f', '--loglevel', action='store', help='log facility level', type=int, choices=range(1, 6), metavar="{1-5}",
                        default=int(getenv("PDWA_LOGLEVEL", 2)))
    parser.add_argument('-r', '--photosroot', action='store', help='photos root directory', type=non_empty_printable,
                        default=getenv("PDWA_PHOTOSROOT", "./photos"))
    parser.add_argument('-d', '--delay', action='store', help='delay during sending file', type=positive_number,
                        default=float(getenv("PDWA_DELAY", 0)))
    parser.add_argument('-s', '--chunksize', action='store', help='chunk size', type=natural_number,
                        default=int(getenv("PDWA_CHUNKSIZE", (32 * 1024))))
    parser.add_argument('-c', '--compressor', action='store', help='compression type', choices=["zip", "gz"], metavar="{zip, gz}",
                        default=getenv("PDWA_COMPRESSOR", "zip"))

    opt = parser.parse_args()

    # logging settings
    logging.basicConfig(filename=opt.log, level=(opt.loglevel * 10),
                        format='[%(asctime)s] %(levelname)s / %(funcName)s / %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    compressor = Compressors[opt.compressor]
    if not compressor.installed:
        raise CompressorIsNotAvailable("Check if compressor's binaries are in the $PATH.")

    headers = get_headers("archive", compressor.extension)

    app = web.Application()

    archivate = partial(archivate_photos, app.loop, compressor.command,
                        opt.chunksize, headers, os.path.normpath(opt.photosroot),
                        opt.delay)

    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate)])

    logging.info(f"Photos downloader web app is starting with options: {opt}")

    web.run_app(app)
