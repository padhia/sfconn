# sfconn

[![PyPi](https://img.shields.io/pypi/v/sfconn.svg)](https://pypi.python.org/pypi/sfconn) [![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT) ![Python3.11+](https://img.shields.io/badge/dynamic/json?query=info.requires_python&label=python&url=https%3A%2F%2Fpypi.org%2Fpypi%2Fsfconn%2Fjson)

Snowflake connection helper functions

A Python library to simplify connecting to Snowflake databases

**Notes**
1. This is a major version upgrade and breaks compatibility with the previous versions (< `0.3.0`). `sfconn` now relies on `snowflake-python-connector` for accessing named connections ([`connections.toml`](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect#connecting-using-the-connections-toml-file)).
1. `sfconn` optionally modifies the way `private_key_file` connection option is evaluated. When `--keyfile-pfx-map` option is specified, or if `$SFCONN_KEYFILE_PFX_MAP` is set, (option value must be a pair of source and target paths separated by `:`). `private_key_file` option, if present and begins with the source path, it is temporarily modified as if it begins with the target path. Primary use-case is to be able to maintain one copy of `connections.toml` file across different execution environments, such as within containers.

## Installation

Use Python's standard `pip` utility for installation:

```sh
pip install --upgrade sfconn
```

## Usage

### `getconn()` and `getsess()`

`getconn` and `getsess` are wrapper functions over native Snowflake functions with added functionality (mainly mapping `private_key_file` value as described above).

**Note:** `getsess()` function will be available only if `snowflake-snowpark-python` package is available at run-time.

**Usage:**
```python
def getconn(connection_name: str | None, **overrides: dict[str, Any]) -> Connection:
def getsess(connection_name: str | None, **overrides: dict[str, Any]) -> Session:
```

`getconn` and `getsess` accept a connection name and return a connection or session object respectively with modified behavior as noted above.

**Examples:**
```python
from sfconn import getconn

# assuming 'dev' is a named connection defined in connections.toml
with getconn('dev', schema='PUBLIC') as cnx:
    with cnx.cursor() as csr:
        csr.execute('SELECT CURRENT_USER()')
        print("Hello " + csr.fetchone()[0])
```

```python
from sfconn import getsess

# assuming 'dev' is a named connection defined in connections.toml
with getsess('dev', schema='PUBLIC') as session:
    df = sess.sql("select current_user() as curr_user, current_role() as curr_role")
    print(df.collect())
```

### `run_query*()`

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

### Decorator Functions

Python command-line scripts that use `argparse` library, can use decorator functions to further reduce boilerplate code needed for setting up a Snowflake connection and error checking

```python
def with_connection_args(doc: str | None) -> Callable[[argparse.ArgumentParser], None]:
def with_connection(logger = None) -> Callable[[Connection, ...], None]:
def with_session(logger = None) -> Callable[[Session, ...], None]:
```

`with_connection_args()` decorator function:
1. builds an `ArgumentParser` object
1. adds common Snowflake connection options as arguments including overriding role, database, schema and warehouse
1. calls the decorated function with the parser object to allow adding any script specific options

`with_connection()` decorator function:
1. consumes standard Snowflake connection options (specified with `with_connection_args()`)
1. creates a connection object
1. calls the decorated function with a connection object as first parameter and any other script specific options that were specified on command line

`with_session()` decorator function:
1. Similar to `with_connection()` but creates a `snowflake.snowpark.Session` object instead of a connection object
1. **Note:** this decorator will be available only if `snowflake-snowpark-python` package is available at run-time.

**Note**: Decorator function parenthesis cannot be omitted even if no arguments are supplied to the decorator functions

**Example:**

```python
from sfconn import with_connection_args, with_connection

@with_connection()
def main(con, show_account: bool):
    with con.cursor() as csr:
        csr.execute('SELECT CURRENT_USER()')
        print("Hello " + csr.fetchone()[0])
        if show_account:
            csr.execute("SELECT CURRENT_ACCOUNT()")
            print("You are connected to account: " + csr.fetchone()[0])

@with_connection_args("Sample application that greets the current Snowflake user")
def getargs(parser):
    parser.add_argument("-a", "--show-account", action='store_true', help="show snowflake account name")

if __name__ == '__main__':
    main(**vars(getargs()))
```

### `get_token()`

Function `sfconn.get_token()` returns a JWT token for connections that use `private_key_path` option. An optional lifetime value can be specified (default 54 minutes)

**Example:**

```python
from sfconn import get_token
jwt_token = get_token(None, 120)  # get token using default (None) connection, and valid for 120 minutes
```
