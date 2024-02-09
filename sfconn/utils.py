"Utility functions"
import logging
from argparse import SUPPRESS, ArgumentParser, ArgumentTypeError
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from .conn import conn_opts, getconn

_loglevel = logging.WARNING


def init_logging(logger: logging.Logger) -> None:
    "initialize the logging system"
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(h)
    logger.setLevel(_loglevel)


def with_connection_options(
    fl: Callable[..., None] | logging.Logger | None = None,
) -> Callable[..., None] | Callable[[Callable[..., None]], Callable[..., None]]:
    "wraps application entry function that expects a connection"

    logger: logging.Logger | None = None

    def wrapper(fn: Callable[..., None]) -> Callable[..., None]:
        @wraps(fn)
        def wrapped(
            keyfile_pfx_map: tuple[Path, Path] | None,
            connection_name: str | None,
            database: str | None,
            role: str | None,
            schema: str | None,
            warehouse: str | None,
            loglevel: int,
            **kwargs: Any,
        ) -> None:
            "script entry-point"
            global _loglevel

            _loglevel = loglevel
            init_logging(logging.getLogger(__name__))
            if logger is not None:
                init_logging(logger)
            _opts = conn_opts(
                connection_name,
                keyfile_pfx_map=keyfile_pfx_map,
                database=database,
                role=role,
                schema=schema,
                warehouse=warehouse,
            )
            return fn(_opts, **kwargs)

        return wrapped

    if fl is None or isinstance(fl, logging.Logger):
        logger = fl
        return wrapper

    return wrapper(fl)


def with_connection(
    fl: Callable[..., None] | logging.Logger | None = None,
) -> Callable[..., None] | Callable[[Callable[..., None]], Callable[..., None]]:
    "wraps application entry function that expects a connection"

    logger = fl if isinstance(fl, logging.Logger) else None

    def wrapper(fn: Callable[..., None]) -> Callable[..., None]:
        @with_connection_options(logger)
        @wraps(fn)
        def wrapped(opts: dict[str, Any], **kwargs: Any) -> None:
            "script entry-point"
            try:
                with getconn(**opts) as cnx:
                    return fn(cnx, **kwargs)
            except Exception as err:
                raise SystemExit(str(err))

        return wrapped  # type: ignore

    if fl is None or isinstance(fl, logging.Logger):
        logger = fl
        return wrapper

    return wrapper(fl)


def add_conn_args(parser: ArgumentParser) -> None:
    "add default arguments"

    def path_pair(v: str) -> tuple[Path, Path]:
        try:
            from_pfx, to_pfx = v.split(":")
            return (Path(from_pfx), Path(to_pfx))
        except ValueError:
            pass
        raise ArgumentTypeError(f"'{v}' is not a valid value, must specify a pair of paths as'<from-path>:<to-path>'")

    g = parser.add_argument_group("connection parameters")
    g.add_argument(
        "--keyfile-pfx-map", type=path_pair, help="change private_key_file path prefix (format: <from-path>:<to-path>)"
    )
    g.add_argument("-c", "--conn", dest="connection_name", help="connection name")
    g.add_argument("--database", metavar="", help="override or set the default database")
    g.add_argument("--role", metavar="", help="override or set the default role")
    g.add_argument("--schema", metavar="", help="override or set the default schema")
    g.add_argument("--warehouse", metavar="", help="override or set the default warehouse")

    parser.add_argument(
        "--debug", dest="loglevel", action="store_const", const=logging.DEBUG, default=logging.WARNING, help=SUPPRESS
    )


def with_connection_args(doc: str | None, **kwargs: Any) -> Callable[..., Callable[..., Any]]:
    """Function decorator that instantiates and adds snowflake database connection arguments"""

    def getargs(fn: Callable[[ArgumentParser], None]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(args: list[str] | None = None) -> Any:
            parser = ArgumentParser(description=doc, **kwargs)
            add_conn_args(parser)
            fn(parser)
            return parser.parse_args(args)

        return wrapped

    return getargs
