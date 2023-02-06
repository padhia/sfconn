"Utility functions"
import logging
from argparse import SUPPRESS, ArgumentParser, ArgumentTypeError
from functools import wraps
from pathlib import Path
from typing import Any, Callable, List, Optional

from .conn import SFCONN_CONFIG_FILE, getconn_checked

logger = logging.getLogger(__name__)
_loglevel = logging.WARNING
_rootpkg = ".".join(__name__.split(".")[:-1])


def init_logging(pkgname: str = _rootpkg) -> None:
    "initialize the logging system"
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger = logging.getLogger(pkgname)
    logger.addHandler(h)
    logger.setLevel(_loglevel)


def entry(fn: Callable[..., None]) -> Callable[..., None]:
    "wraps application entry function that expects a connection"
    @wraps(fn)
    def wrapped(
        config_file: Path,
        conn: Optional[str],
        database: Optional[str],
        role: Optional[str],
        schema: Optional[str],
        warehouse: Optional[str],
        loglevel: int,
        **kwargs: Any
    ) -> None:
        "script entry-point"
        global _loglevel

        _loglevel = loglevel
        init_logging()
        with getconn_checked(conn, config_file=config_file, database=database, role=role, schema=schema,
                             warehouse=warehouse) as cnx:
            return fn(cnx, **kwargs)

    return wrapped


def add_conn_args(parser: ArgumentParser, config_file: Path = SFCONN_CONFIG_FILE) -> None:
    "add default arguments"
    def existing_file(arg: str) -> Path:
        if (p := Path(arg)).is_file():
            return p
        raise ArgumentTypeError(f"{arg} does not exist or not a file")

    g = parser.add_argument_group("connection parameters")
    g.add_argument('--config-file', metavar='', type=existing_file, default=config_file,
                   help=f'configuration file (default: {config_file})')
    g.add_argument('-c', '--conn', metavar='', help="connection name")
    g.add_argument('--database', metavar='', help='override or set the default database')
    g.add_argument('--role', metavar='', help='override or set the default role')
    g.add_argument('--schema', metavar='', help='override or set the default schema')
    g.add_argument('--warehouse', metavar='', help='override or set the default warehouse')

    parser.add_argument('--debug', dest='loglevel', action='store_const', const=logging.DEBUG, default=logging.WARNING,
                        help=SUPPRESS)


def args(doc: Optional[str], config_file: Path = SFCONN_CONFIG_FILE, **kwargs: Any) -> Callable[..., Callable[..., Any]]:
    """Function decorator that instantiates and adds snowflake database connection arguments"""
    def getargs(fn: Callable[[ArgumentParser], None]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(args: Optional[List[str]] = None) -> Any:
            parser = ArgumentParser(description=doc, **kwargs)
            fn(parser)
            add_conn_args(parser, config_file=config_file)
            return parser.parse_args(args)
        return wrapped
    return getargs
