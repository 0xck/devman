import asyncio
import json
import logging
from builtins import AssertionError
from functools import partial
from os import getenv
from os.path import exists

from aiofile import LineReader, AIOFile, Writer

from chat_common import chat_connector, get_argparser, _non_empty_printable, run_client, _port, encode_utf8, decode_utf8
from exit_handler import NonGracefulExit


async def does_nothing(*args, **kwargs):
    return


async def get_accounts(storage):

    assert bool(storage) and storage.isprintable(), AssertionError("Storage file name has to be non-empty printable.")

    if not exists(storage):
        logging.info(f"There is not {storage} file.")
        return {}

    storage_content = []

    async with AIOFile(storage, mode="r", encoding="utf-8") as file:

        async for line in LineReader(file):
            storage_content.append(line)

    try:
        return json.loads("".join(storage_content))

    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in {storage}")
        raise NonGracefulExit()


async def register(storage, nickname, reader, writer, _):

    assert bool(storage) and storage.isprintable(), AssertionError("Storage file name has to be non-empty printable.")
    assert bool(nickname) and nickname.isprintable(), AssertionError("Nickname has to be non-empty printable.")

    accounts = await get_accounts(storage)

    if nickname in accounts:
        logging.warning(f"Account {nickname} already exists.")
        return

    # registering new account
    try:
        # read init
        debug_line = await reader.readline()
        logging.debug(decode_utf8(debug_line))
        # skip token input
        writer.write(encode_utf8("\n"))
        await writer.drain()
        # read invite
        debug_line = await reader.readline()
        logging.debug(decode_utf8(debug_line))
        # create new
        writer.write(encode_utf8(f"{nickname}\n"))
        await writer.drain()
        # get info for new account
        registered = await reader.readline()
        accounts[nickname] = json.loads(decode_utf8(registered))

    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in account info")
        raise NonGracefulExit()

    except asyncio.CancelledError:
        logging.error(
            f"Account for {nickname} was created, but was not added to {storage}, its token is {accounts[nickname]['account_hash']}")
        raise

    async with AIOFile(storage, mode="w", encoding="utf-8") as file:

        try:
            await Writer(file)(json.dumps(accounts))
            await file.fsync()

            logging.info(f"Account {nickname} information was written into {storage}")

        except asyncio.CancelledError:
            await file.fsync()
            raise

    # print result to stdout for user handling
    print(f"Account for {nickname} was successfully created, its token is {accounts[nickname]['account_hash']}")


async def send_messages(messages, token, reader, writer, _):

    assert bool(messages) and all(bool(m) and m.isprintable() for m in messages), AssertionError(
        "Messages have to be present and must be non-empty printable.")
    assert bool(token), AssertionError("Token can not be empty.")

    try:
        # read init
        debug_line = await reader.readline()
        logging.debug(decode_utf8(debug_line))
        # send auth token
        writer.write(encode_utf8(f"{token}\n"))
        await writer.drain()
        # read auth answer
        debug_line = await reader.readline()
        answer = decode_utf8(debug_line)
        logging.debug(answer)

    except asyncio.CancelledError:
        logging.info("Got terminated, messages were not sent.")
        raise

    try:
        if json.loads(answer) is None:
            logging.error(f"Invalid token {token}")
            return

    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in auth answer: {answer}")
        raise NonGracefulExit()

    try:
        # sending messages
        for msg in messages:

            # send message
            prepared = msg.strip().replace("\n", "\t").replace("\\n", "\t")
            if not prepared:
                logging.warning(f"Empty message from original message {repr(msg)} was skipped")
                continue

            logging.debug(f"Writing prepared {prepared} from original message {msg}")
            writer.write(encode_utf8(f"{prepared}\n\n"))
            await writer.drain()

            # read answer
            debug_line = await reader.readline()
            logging.debug(decode_utf8(debug_line))

    except asyncio.CancelledError:
        logging.info("Got terminated, all or part of messages might not be sent.")
        raise


def get_action(action_send, action_register, action_check):
    # Perform given options to triple bytes result

    assert all(isinstance(i, bool) for i in (action_send, action_register, action_check)), AssertionError(
        "All parameters has to be bool.")

    return (action_send << 2) + (action_register << 1) + action_check


async def client_sender(options, chat_connector):

    # Action is defined as result of triple bytes table
    # from given actions: send (S), register (R) and checknick (C),
    # where 0 is False and 1 is True. Thus, table is
    # S R C | result
    # ------|-------
    # 0 0 0 | 0 or nothing is defined
    # 0 0 1 | 1 or check nickname token
    # 0 1 0 | 2 or register nickname
    # 1 0 0 | 4 or send messages
    # all rest combination does have sense, due actions can not be combined.
    action = get_action(options.send, options.register, options.checknick)
    logging.debug(f"Action {action} was given from {(options.send, options.register, options.checknick)}")

    if not action:
        logging.error("Action has to be set.")
        return

    if action not in (1, 2, 4):
        logging.error("Actions can not be combined.")
        return

    # sending message
    if action == 4:
        token = None

        if options.token is not None:
            token = options.token

        elif options.nickname is not None:
            accounts = await get_accounts(options.accounts)
            account = accounts.get(options.nickname)
            if account is not None:
                token = account["account_hash"]

        if token is None:
            logging.error("Token or known nickname has to be defined for sending message.")
            return

        sender = partial(send_messages, options.messages, token)
        await chat_connector(sender, does_nothing)
        return

    # for rest actions nickname has to be defined
    if options.nickname is None:
        logging.error("Nickname has to be defined.")
        return

    # register new account
    if action == 2:
        registrar = partial(register, options.accounts, options.nickname)
        await chat_connector(registrar, does_nothing)
        return

    # check what is nickname token
    accounts = await get_accounts(options.accounts)
    # result prints into stdout for user handling
    if options.nickname in accounts:
        print(f"{options.nickname} token is {accounts[options.nickname]['account_hash']}")
    else:
        print("Unknown nickname")


def _string_or_none(maybe_string):

    if maybe_string is None:
        return None

    return _non_empty_printable(maybe_string)


def get_args():
    parser = get_argparser()

    parser.add_argument("-a", "--accounts", action="store", type=_non_empty_printable,
                        help="account storage, default is .accounts.json",
                        default=getenv("CHAT_ACCOUNTS", ".accounts.json"))

    parser.add_argument("-t", "--token", action="store", type=_string_or_none,
                        help="account token, default is no token",
                        default=getenv("CHAT_TOKEN", None))

    parser.add_argument("-n", "--nickname", action="store", type=_string_or_none,
                        help="account nickname, default is no nickname",
                        default=getenv("CHAT_NICKNAME", None))

    parser.add_argument("-S", "--send", action="store_true",
                        help="action `send messages`")

    parser.add_argument("-R", "--register", action="store_true",
                        help="action `register new account`")

    parser.add_argument("-C", "--checknick", action="store_true",
                        help="action `check what is nickname token`")

    parser.add_argument("-m", "--messages", nargs="+", type=_non_empty_printable,
                        help="messages, one by one, separated by space")

    parser.add_argument("-p", "--port", action="store", type=_port,
                        help="chat port, default is 5050",
                        default=int(getenv("CHAT_PORT", 5050)))

    return parser.parse_args()


if __name__ == '__main__':
    options = get_args()

    # logging settings
    logging.basicConfig(filename=options.log, level=(options.loglevel * 10),
                        format="[%(asctime)s] %(levelname)s / %(funcName)s / %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    connector = partial(chat_connector, options.host, options.port, options.delay, options.retries)
    chat_handler = partial(client_sender, options, connector)

    logging.info(f"Chat sender is starting with options: {options}")
    run_client(chat_handler)
