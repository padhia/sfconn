[![PyPi](https://img.shields.io/pypi/v/sfconn.svg)](https://pypi.python.org/pypi/sfconn) [![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT) ![Python3.9+](https://img.shields.io/badge/dynamic/json?query=info.requires_python&label=python&url=https%3A%2F%2Fpypi.org%2Fpypi%2Fsfconn%2Fjson)


Snowflake connection helper functions

A Python library to simplify connecting to Snowflake databases by leveraging connection options specified in [SnowSQL](https://docs.snowflake.com/en/user-guide/snowsql.html) configuration file (`~/.snowsql/config`).

**Notes** Following are some minor differences between the way `SnowSQL` interprets connection options v/s `sfconn` library:
1. `sfconn` library supports setting `SFCONN` environment variable to be used as a default connection name before searching for a default connection entry in the config file.
1. SnowSQL doesn't (yet) allow `private_key_path` to contain home-anchored paths (e.g. `~/keys/key.p8`), but `sfconn` library does
1. SnowSQL treats relative paths as relative to working directory of the running process, whereas, `sfconn` library by default evaluates relative paths as relative to the config file location. If SnowSQL-like behavior is needed, do either of the following:
    - before any other calls to `sfconn` library, include following code
    ```python
    import sfconn

    sfconn.conn.relpath_anchor_is_cwd = True
    ```
    - set `SFCONN_RELPATH_ANCHOR_CWD=1` environment variable

# Installation

Use Python's standard `pip` utility for installation:

```sh
pip install --upgrade sfconn
```

# Usage

## `getconn()`

**Usage:**
```python
def getconn(name: Optional[str], **overrides: Dict[str, Any]) -> Connection
```

`getconn` accepts a connection name that is defined in `~/.snowsql/config` and returns a connection object. If connection name is `None`, value of `SFCONN` environment variable will be used as the default connection name; if `SFCONN` is unset then the default connection entry defined in the config file will be used before returning an error. Any additional parameters, which are not set to `None`, will override the values loaded from the configuration file.

**Example:**

```python
from sfconn import getconn

# assuming 'dev' is a connection defined in ~/.snowflake/config
with getconn('dev', schema='PUBLIC') as cnx:
    with cnx.cursor() as csr:
        csr.execute('SELECT CURRENT_USER()')
        print("Hello " + csr.fetchone()[0])
```

## `conn_opts()`

**Usage:**
```python
def conn_opts(name: Optional[str], **overrides: Dict[str, Any]) -> Dict[str, Any]
```

`conn_opts`, returns a Python `dict` object populated with options and values. This can be useful passing as an argument to `snowflake.snowpark.Session.builder.configs()` method.

**Example:**

```python
from sfconn import conn_opts
from snowflake.snowpark import Session

# assuming 'dev' is a connection defined in ~/.snowflake/config
session = Session.builder.configs(conn_opts('dev')).create()
```

## Decorator functions

Python scripts that accept command-line parameters and use `argparse` library, can use decorator functions to further reduce boilerplate code needed for setting up common Snowflake connection options as command-line arguments

```python
def args(doc: Optional[str]) -> Callable[[argparse.ArgumentParser], None]:
def entry() -> Callable[[Connection, ...], None]:
def entry_opts() => Callable([dict[str, Any, ...]])
```

`args()` decorator function:
1. builds an `ArgumentParser` object
1. adds common Snowflake connection options as arguments that allow overriding values specified in `~/.snowsql/config`
1. calls the decorated function with the parser object to allow adding any script specific options

`entry()` decorator function:
1. consumes standard Snowflake connection options (specified with `args()`)
1. creates a connection object
1. calls the decorated function with a connection object as first parameter and any other script specific options that were specified on command line

`entry_opts()` decorator function:
- Similar to `entry()` but passes a `dict` of options as the first parameter. This is useful for passing options to the `snowflake.snowpark.Session.builder.configs()` method

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

## connection options as JSON

Convert connection options to a JSON object.

```
python -m sfconn [-c <conn>] json
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
