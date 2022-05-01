[![PyPi](https://img.shields.io/pypi/v/sfconn.svg)](https://pypi.python.org/pypi/sfconn) [![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT) ![Python3.9+](https://img.shields.io/badge/dynamic/json?query=info.requires_python&label=python&url=https%3A%2F%2Fpypi.org%2Fpypi%2Fsfconn%2Fjson)


Snowflake connection helper functions

A Python library to simplify connecting to Snowflake databases by leveraging connection options specified in [SnowSQL](https://docs.snowflake.com/en/user-guide/snowsql.html) configuration file (`~/.snowsql/config`).

# Installation

Use Python's standard `pip` utility for installation:

```sh
pip install --upgrade sfconn
```

# Usage

## `getconn()`

**Usage:**
```python
def getconn(name: Optional[str], **overrides: dict[str, Any]) -> Connection
```

`getconn` accepts a connection name that is defined in `~/.snowsql/config` and returns a connection object. A `None` value for the name will use the default connection. Any valid DB API connection parameters can also be passed, which if not `None`, will override the values loaded from the configuration file.

**Example:**

```python
from sfconn import getconn

# assuming 'dev' is a connection defined in ~/.snowflake/config
with getconn('dev', schema='PUBLIC') as cnx:
    with cnx.cursor() as csr:
        csr.execute('SELECT CURRENT_USER()')
        print("Hello " + csr.fetchone()[0])
```

## Decorator functions

Python scripts that accept command-line parameters and use `argparse` library, can use decorator functions to further reduce boilerplate code needed for setting up common Snowflake connection options as command-line arguments

```python
def args(doc: Optional[str]) -> Callable[[argparse.ArgumentParser], None]:
def entry() -> Callable[[Connection, ...], None]:
```

`args()` decorator function:
1. builds an `ArgumentParser` object
1. adds common Snowflake connection options as arguments that allow overriding values specified in `~/.snowsql/config`
1. calls the decorated function with the parser object to allow adding any script specific options

`entry()` decorator function:
1. consumes standard Snowflake connection options (specified with `args()`)
1. creates a connection object
1. calls the decorated function with a connection object as first argument and any other script specific options that were specified on command line

**Example:**

```python
from sfconn import args, entry

@entry
def main(con, show_account: bool):
    with con.cursor() as csr:
        csr.execute('SELECT CURRENT_USER()')
        print("Hello " + csr.fetchone()[0])
        if show_account:
            csr.execute("SELECT CURRENT_ACCOUNT()")
            print("You are connected to account: " + csr.fetchone()[0])

@args("Sample application that greets the current Snowflake user")
def getargs(parser):
    parser.add_argument("-a", "--show-account", action='store_true', help="show snowflake account name")

if __name__ == '__main__':
    main(**vars(getargs()))
```

## `get_token()`

Function `sfconn.get_token()` returns a JWT token for connections that use `private_key_path` option. An optional lifetime value can be specified (default 54 minutes)

**Example:**

```python
from sfconn import get_token

# assuming 'dev' is a connection defined in ~/.snowflake/config and uses key-pair authentication
jwt_token = get_token('dev', 120)  # get a token valid for 120 minutes
```

# Utilities

The `sfconn` module provides a couple of handy utilities.

## list connections

To list all defined connections, use

```
python -m sfconn [list]
```

## test a connection

To test a particular connection, use

```
python -m sfconn [-c <conn>] test [--save]
```

`--save` option applies to connections that require password to be supplied. When specified, it saves the supplied password in OS specific *secure local storage*.

**Notes:**

- `--save` option is supported only if the optional python package `keyring` is installed.
- `keyring` can also be installed indirectly by installing `snowflake-connector-python` with `secure-local-storage` extra dependency as described [here](https://docs.snowflake.com/en/user-guide/python-connector-install.html#step-1-install-the-connector)

## get a JWT

Get a JWT for connections that use key-pair authentication

```
python -m sfconn [-c <conn>] jwt [--lifetime <minutes>]
```
