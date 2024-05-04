"Utility functions"

import datetime as dt
import logging
from argparse import SUPPRESS, ArgumentParser, ArgumentTypeError
from decimal import Decimal
from functools import wraps
from pathlib import Path
from typing import Any, Callable, cast

from snowflake.connector.constants import FIELD_TYPES
from snowflake.connector.cursor import ResultMetadata

from .conn import conn_opts, getconn, getsess

_loglevel = logging.WARNING


def init_logging(logger: logging.Logger) -> None:
    "initialize the logging system"
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(h)
    logger.setLevel(_loglevel)


def with_connection_options(fl: Callable[..., Any] | logging.Logger | None = None) -> Callable[..., Any]:
    "wraps application entry function that expects a connection"

    logger = fl if isinstance(fl, logging.Logger) else None

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
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
        ) -> Any:
            "script entry-point"
            global _loglevel

            _loglevel = loglevel
            init_logging(logging.getLogger(__name__))
            if logger is not None:
                init_logging(logger)
            _opts = conn_opts(
                keyfile_pfx_map=keyfile_pfx_map,
                connection_name=connection_name,
                database=database,
                role=role,
                schema=schema,
                warehouse=warehouse,
            )
            return fn(_opts, **kwargs)

        return wrapped

    return wrapper if fl is None or isinstance(fl, logging.Logger) else wrapper(fl)


def with_connection(fl: Callable[..., Any] | logging.Logger | None = None) -> Callable[..., Any]:
    "wraps application entry function that expects a connection"

    logger = fl if isinstance(fl, logging.Logger) else None

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        @with_connection_options(logger)
        def wrapped(opts: dict[str, Any], **kwargs: Any) -> Any:
            "script entry-point"
            try:
                with getconn(**opts) as cnx:
                    return fn(cnx, **kwargs)
            except Exception as err:
                raise SystemExit(str(err))

        return wrapped

    return wrapper if fl is None or isinstance(fl, logging.Logger) else wrapper(fl)


def with_session(fl: Callable[..., Any] | logging.Logger | None = None) -> Callable[..., Any]:
    "wraps application entry function that expects a connection"

    logger = fl if isinstance(fl, logging.Logger) else None

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        @with_connection_options(logger)
        def wrapped(opts: dict[str, Any], **kwargs: Any) -> Any:
            "script entry-point"
            try:
                with getsess(**opts) as session:
                    return fn(session, **kwargs)
            except Exception as err:
                raise SystemExit(str(err))

        return wrapped

    return wrapper if fl is None or isinstance(fl, logging.Logger) else wrapper(fl)


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
        help="temporarily change private_key_file path prefix (format: <from-path>:<to-path>, default: $SFCONN_KEYFILE_PFX_MAP)",
    )

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


def _pytype(meta: ResultMetadata, best_match: bool = False) -> type[Any]:
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


try:
    import snowflake.snowpark.types as T

    def pytype(meta: ResultMetadata | T.DataType, best_match: bool = False) -> type[Any]:
        """convert Python DB API or Snowpark data type to python type

        Args:
            meta: an individual value returned as part of cursor.description or snowflake.snowpark.types.DataType
            best_match: return Python type that is best suited, rather than the actual type used by the connector

        Returns:
            Python type that best matches Snowflake's type, or str in other cases
        """
        if isinstance(meta, ResultMetadata):
            return _pytype(meta, best_match)

        types = {
            T.LongType: int,
            T.DateType: dt.date,
            T.TimeType: dt.time,
            T.TimestampType: dt.datetime,
            T.BooleanType: bool,
            T.DecimalType: Decimal,
            T.DoubleType: float,
            T.BinaryType: bytearray,
            T.ArrayType: list,
            T.VariantType: object,
            T.MapType: dict,
        }
        return next((py_t for sp_t, py_t in types.items() if isinstance(meta, sp_t)), str)

except ImportError:
    pytype = _pytype  # type: ignore
