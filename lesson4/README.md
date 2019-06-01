# Secret chat client

Connect to secret chats easily.

## Setup and launch

> Note. Only python 3.6 and above is supported

## Before execution
Download and go to `lesson4` directory. All execution actions have to be performed there.

```shell
cd lesson4/
```

### Read chat messages
Execute `chat_reader.py` with `python` interpreter, e.g.:

```shell
python3 chat_reader.py -s secret.chat.server -p 1234
```

Command above will try to connect to given server (option `-s` or `--host`) and port (option `-p` or `--port`). By default all received messages are saved in `message.history` plain text file. This behavior may be changed with option `-H <path_to_file>`.

Chat reader supports additional settings, that can be given as arguments to executed file or by using environments. See details in help menu:

```shell
python chat_reader.py -h
```

As well environments are supported. They stat with prefix `CHAT_` and end with upper case full argument name. E.g. `CHAT_HISTORY` set history file, `CHAT_PORT` set chat server port, thus full argument name here `--history` for former and `--port` for latter.

> Note. File arguments have more high priority than environments.

### Sending, register

#### Register new account
Execute `chat_sender.py` with `python` interpreter, e.g.:

```shell
python3 chat_sender.py -s secret.chat.server -p 1234 -R -n my_nickname
```

Command above will try to connect to given server and create new account (option `-R` or `register`) with *my_nickname* as account nickname and added it in account storage, default is `.accounts.json`. This behavior may be changed with option `-a <path_to_file>`. If this action completes successfully, then new nickname can be used for sending messages.

#### Checking account existence and token
Execute `chat_sender.py` with `python` interpreter, e.g.:

```shell
python3 chat_sender.py -C -n my_nickname
```

Command above will check (option `-C` or `--checknick`)  if account *my_nickname* was registered and return its token if one exists in accounts storage, by default it is `.accounts.json`. This behavior may be changed with option `-a <path_to_file>`. If this action completes successfully, token will be printed in standard output, otherwise it prints *Unknown account*.

#### Sending messages

##### Sending with token

Execute `chat_sender.py` with `python` interpreter, e.g.:

```shell
python3 chat_sender.py -s secret.chat.server -p 1235 -S -m "message1" "message2" "message3" -t my_token
```

##### Sending with registered nickname

If there is previously registered nickname in account storage, by default it is `.accounts.json`. This behavior may be changed with option `-a <path_to_file>`, then it is possible to use one for sending messages. Execute `chat_sender.py` with `python` interpreter, e.g.:

```shell
python3 chat_sender.py -s secret.chat.server -p 1235 -S -m "message1" "message2" "message3" -n my_nickname
```

Commands will try to connect to given server (option `-s` or `--host`) and port (option `-p` or `--port`) and send (option `-S` or `--send`) given with option `-m` messages from account with nickname or token. If this action completes successfully, then all messages will be sended to chat.

> None. Caret's return and new line symbols will be swapped with tab.

Chat sender supports additional settings, that can be given as arguments to executed file or by using environments. See details in help menu:

```shell
python chat_sender.py -h
```

As well environments are supported. They stat with prefix `CHAT_` and end with upper case full argument name. E.g. `CHAT_TOKEN` set history file, `CHAT_PORT` set chat server port, thus full argument name here `--token` for former and `--port` for latter.

> Note. File arguments have more high priority than environments.