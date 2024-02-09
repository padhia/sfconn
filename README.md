[![PyPi](https://img.shields.io/pypi/v/sfconn.svg)](https://pypi.python.org/pypi/sfconn) [![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT) ![Python3.11+](https://img.shields.io/badge/dynamic/json?query=info.requires_python&label=python&url=https%3A%2F%2Fpypi.org%2Fpypi%2Fsfconn%2Fjson)

Snowflake connection helper functions

A Python library to simplify connecting to Snowflake databases

**Notes**
1. This is a major version upgrade and breaks compatibility with the previous versions (< `0.3.0`). `sfconn` now relies on `snowflake-python-connector` for accessing named connections (e.g. `connections.toml`). If you still need the ability use named connections from `~/.snowflake/config`, please continue using older version (`0.2.x`).
1. `sfconn` modifies the way `private_key_file` connection option is evaluated in the following ways:
    - with `--keyfile-anchor` option (default `$SFCONN_KEYFILE_ANCHOR`): uses the supplied value to anchor any relative paths (v/s anchoring paths relative to current working directory of the running process)
    - with `--keyfile-strip-pfx` option (default `$SFCONN_KEYFILE_STRIP_PFX` ): strips the specified prefix from the path values (so `--keyfile-anchor` option can be used)

# Installation

Use Python's standard `pip` utility for installation:

```sh
pip install --upgrade sfconn
```

# Usage

## `getconn()`

**Usage:**
```python
def getconn(connection_name: str | None, **overrides: dict[str, Any]) -> Connection
```

`getconn` accepts a connection name and returns a connection object with modified behavior as noted above.

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
def conn_opts(name: str | None , **overrides: dict[str, Any]) -> dict[str, Any]
```

`conn_opts`, returns a Python `dict` object populated with options and values. This can be useful passing as an argument to `snowflake.snowpark.Session.builder.configs()` method.

**Example:**

```python
from sfconn import conn_opts
from snowflake.snowpark import Session

# assuming 'dev' is a connection defined in ~/.snowflake/config
session = Session.builder.configs(conn_opts('dev')).create()
```

## `run_query*()`

Cursor objects add a family of few convenience methods that return an `Iterable` of values instead of generic `tuple` or `dict`.

1. `<cursor>.run_query(<callable>|<class>, <sql> [,<params>])`: Returns an Iterable of values.
    - `<callable>` is a mapping function that shall accept all column values of a row as individual arguments, in order, and returns a value that will be used for `Iterable`.
    - `<class>` is any Python class whose attribute names, after upper-casing, are treated as column names from the result set. `<class>` can include only a subset of a all available column from the query result as attributes and in a different order than the query.
1. `<cursor>.run_query1(<callable>|<class>, <sql> [,<params>])`: Similar to `run_query`, except returns a single value. Note, if at least one value is not available, raises `ProgrammingError` exception.
1. `<cursor>.run_query1_opt(<callable>|<class>, <sql> [,<params>])`: Similar to `run_query1`, except instead of raising an exception, the method returns `None`.

**Examples:**

```python
import datetime as dt
from collections import namedtuple

Result = namedtuple("Result", ["user", "date"])

def mkResult(x: str, y: dt.date) -> Result:
    return Result(x, y)

with getconn() as cnx, cnx.cursor() as csr:
    result = csr.run_query1(mkResult, "select current_user() as user, current_date() as date")
```

```python
import datetime as dt
from dataclasses import dataclass

@dataclass
class Result:
    date: dt.date
    user: str

with getconn() as cnx, cnx.cursor() as csr:
    result = csr.run_query1(
        Result,
        "select current_user() as user, current_date() as date, current_warehouse() as wh_name"
    )
```

## Decorator functions

Python scripts that accept command-line parameters and use `argparse` library, can use decorator functions to further reduce boilerplate code needed for setting up common Snowflake connection options as command-line arguments

```python
def with_connection_args(doc: str | None) -> Callable[[argparse.ArgumentParser], None]:
def with_connection(logger = None) -> Callable[[Connection, ...], None]:
def with_connection_option(logger = None) => Callable([dict[str, Any, ...]])
```

`with_connection_args()` decorator function:
1. builds an `ArgumentParser` object
1. adds common Snowflake connection options as arguments that allow overriding values specified in `~/.snowsql/config`
1. calls the decorated function with the parser object to allow adding any script specific options

`with_connection()` decorator function:
1. consumes standard Snowflake connection options (specified with `args()`)
1. creates a connection object
1. calls the decorated function with a connection object as first parameter and any other script specific options that were specified on command line

`with_connection_option()` decorator function:
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
