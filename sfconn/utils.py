"Utility functions"

import datetime as dt
import logging
from argparse import SUPPRESS, ArgumentParser, ArgumentTypeError
from decimal import Decimal
from functools import wraps
from logging import Logger
from pathlib import Path
from typing import Any, Callable, Concatenate, ParamSpec, TypeAlias, TypeVar, cast

from snowflake.connector.constants import FIELD_TYPES
from snowflake.connector.cursor import ResultMetadata

from .conn import Connection, getconn
from .jwt import RestInfo, get_rest_info

P = ParamSpec("P")
R = TypeVar("R")

ConnFn: TypeAlias = Callable[Concatenate[Connection, P], R]
ArgsFn: TypeAlias = Callable[
    [Concatenate[tuple[Path, Path] | None, str | None, str | None, str | None, str | None, str | None, int, P]], R
]


def init_logging(logger: Logger, loglevel: int = logging.WARNING) -> None:
    "initialize the logging system"
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(h)
    logger.setLevel(loglevel)


def set_loglevel(loglevel: int = logging.WARNING) -> None:
    "set logging level for the module, default WARNING"
    init_logging(logging.getLogger(".".join(__name__.split(".")[:-1])), loglevel)


def with_connection(logger: Logger | None = None) -> Callable[[ConnFn[P, R]], ArgsFn[P, R]]:
    def wrapper(fn: ConnFn[P, R]) -> ArgsFn[P, R]:
        @wraps(fn)
        def wrapped(
            keyfile_pfx_map: tuple[Path, Path] | None,
            connection_name: str | None,
            database: str | None,
            role: str | None,
            schema: str | None,
            warehouse: str | None,
            loglevel: int = logging.WARNING,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            "script entry-point"
            set_loglevel(loglevel)
            if logger is not None:
                init_logging(logger, loglevel)

            try:
                with getconn(
                    keyfile_pfx_map=keyfile_pfx_map,
                    connection_name=connection_name,
                    database=database,
                    role=role,
                    schema=schema,
                    warehouse=warehouse,
                ) as cnx:
                    return fn(cnx, *args, **kwargs)
            except Exception as err:
                raise SystemExit(str(err))

        return wrapped  # type: ignore

    return wrapper


def add_conn_args(parser: ArgumentParser, *, debug_opt: bool = True, hide_keyfile_pfx_map: bool = True) -> None:
    "add connection arguments"

    def path_pair(v: str) -> tuple[Path, Path]:
        try:
            from_pfx, to_pfx = v.split(":")
            return (Path(from_pfx), Path(to_pfx))
        except ValueError:
            pass
        raise ArgumentTypeError(f"'{v}' is not a valid value, must specify a pair of paths as'<from-path>:<to-path>'")

    g = parser.add_argument_group("connection parameters")
    g.add_argument(
        "-c", "--conn", metavar="NAME", dest="connection_name", help="A connection name from the connections.toml file"
    )
    g.add_argument("--database", metavar="NAME", help="override or set the default database")
    g.add_argument("--role", metavar="NAME", help="override or set the default role")
    g.add_argument("--schema", metavar="NAME", help="override or set the default schema")
    g.add_argument("--warehouse", metavar="NAME", help="override or set the default warehouse")
    g.add_argument(
        "--keyfile-pfx-map",
        metavar="PATH:PATH",
        type=path_pair,
        help=SUPPRESS
        if hide_keyfile_pfx_map
        else "temporarily change private_key_file path prefix (format: <from-path>:<to-path>, default: $SFCONN_KEYFILE_PFX_MAP)",
    )

    if debug_opt:
        parser.add_argument(
            "--debug", dest="loglevel", action="store_const", const=logging.DEBUG, default=logging.WARNING, help=SUPPRESS
        )


def with_connection_args(
    doc: str | None, debug_opt: bool = True, hide_keyfile_pfx_map: bool = True, **kwargs: Any
) -> Callable[..., Callable[..., Any]]:
    """Function decorator that instantiates and adds snowflake database connection arguments"""

    def getargs(fn: Callable[[ArgumentParser], None]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(args: list[str] | None = None) -> Any:
            parser = ArgumentParser(description=doc, **kwargs)
            fn(parser)
            add_conn_args(parser, debug_opt=debug_opt, hide_keyfile_pfx_map=hide_keyfile_pfx_map)
            return parser.parse_args(args)

        return wrapped

    return getargs


def with_rest_args(
    doc: str | None, debug_opt: bool = True, hide_keyfile_pfx_map: bool = True, **kwargs: Any
) -> Callable[..., Callable[..., Any]]:
    """Function decorator that instantiates and adds snowflake JWT as first argument"""

    def getargs(fn: Callable[[ArgumentParser], None]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(args: list[str] | None = None) -> Any:
            parser = ArgumentParser(description=doc, **kwargs)
            fn(parser)
            add_conn_args(parser, debug_opt=debug_opt, hide_keyfile_pfx_map=hide_keyfile_pfx_map)
            parser.add_argument(
                "-L",
                "--lifetime",
                metavar="MINUTE",
                default=dt.timedelta(minutes=90),
                type=lambda x: dt.timedelta(minutes=float(x)),
                help="JWT lifetime (default 90 minutes)",
            )
            return parser.parse_args(args)

        return wrapped

    return getargs


def with_rest(logger: Logger | None = None) -> Callable[[Callable[Concatenate[RestInfo, P], R]], ArgsFn[P, R]]:
    def wrapper(fn: Callable[Concatenate[RestInfo, P], R]) -> ArgsFn[P, R]:
        @wraps(fn)
        def wrapped(
            keyfile_pfx_map: tuple[Path, Path] | None,
            connection_name: str | None,
            database: str | None,
            role: str | None,
            schema: str | None,
            warehouse: str | None,
            lifetime: dt.timedelta,
            loglevel: int,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            "script entry-point"
            set_loglevel(loglevel)
            if logger is not None:
                init_logging(logger, loglevel)

            try:
                rest_info = get_rest_info(
                    keyfile_pfx_map=keyfile_pfx_map,
                    connection_name=connection_name,
                    lifetime=lifetime,
                    database=database,
                    schema=schema,
                    role=role,
                    warehouse=warehouse,
                )
                return fn(rest_info, *args, **kwargs)
            except Exception as err:
                raise SystemExit(str(err))

        return wrapped  # type: ignore

    return wrapper


def pytype_conn(meta: ResultMetadata, best_match: bool = False) -> type:
    """convert Python DB API data type to python type

    Args:
        meta: an individual value returned as part of cursor.description
        best_match: return Python type that is best suited, rather than the actual type used by the connector

    Returns:
        Python type that best matches Snowflake's type, or str in other cases
    """
    TYPE_MAP: dict[str, type[Any]] = {
        "TEXT": str,
        "REAL": float,
        "DATE": dt.date,
        "TIME": dt.time,
        "TIMESTAMP_NTZ": dt.datetime,
        "TIMESTAMP_LTZ": dt.datetime,
        "TIMESTAMP_TZ": dt.datetime,
        "BOOLEAN": bool,
        "OBJECT": dict,
        "VARIANT": object,
        "ARRAY": list,
        "BINARY": bytearray,
    }

    sql_type_name = cast(str, FIELD_TYPES[meta.type_code].name)  # type: ignore

    if sql_type_name == "FIXED":
        return int if meta.scale == 0 else Decimal

    type_ = TYPE_MAP.get(sql_type_name, str)

    return type_ if best_match else str if type_ in [dict, object, list] else type_
