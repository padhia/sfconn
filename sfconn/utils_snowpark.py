"Utility functions"

import datetime as dt
import logging
from decimal import Decimal
from functools import wraps
from logging import Logger
from pathlib import Path
from typing import Any, Callable, Concatenate, ParamSpec, TypeAlias, TypeVar

import snowflake.snowpark.types as T
from snowflake.snowpark import Session

from .conn import conn_opts
from .utils import init_logging

P = ParamSpec("P")
R = TypeVar("R")


ConnFn: TypeAlias = Callable[Concatenate[Session, P], R]
ArgsFn: TypeAlias = Callable[
    [Concatenate[tuple[Path, Path] | None, str | None, str | None, str | None, str | None, str | None, int, P]], R
]


def getsess(*, keyfile_pfx_map: tuple[Path, Path] | None = None, **kwargs: Any) -> Session:
    """create a Session object using named configuration

    Args:
        keyfile_pfx_map: if specified must be a a pair of Path values specified as <from-path>:<to-path>, which will
                            be used to temporarily change private_key_file path value if it starts with <from-pahd> prefix
        **kwargs: Any parameter that is valid for snowflake.connector.connect() method

    Returns:
        Session object returned by Snowflake python connector
    """
    return Session.builder.configs(conn_opts(keyfile_pfx_map=keyfile_pfx_map, **kwargs)).create()


def with_session(logger: Logger | None = None) -> Callable[[ConnFn[P, R]], ArgsFn[P, R]]:
    def _decorate_conn_fn(fn: ConnFn[P, R]) -> ArgsFn[P, R]:
        @wraps(fn)
        def wrapped(
            keyfile_pfx_map: tuple[Path, Path] | None,
            connection_name: str | None,
            database: str | None,
            role: str | None,
            schema: str | None,
            warehouse: str | None,
            loglevel: int,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            "script entry-point"
            init_logging(logging.getLogger(__name__))
            if logger is not None:
                init_logging(logger, loglevel)

            try:
                with getsess(
                    keyfile_pfx_map=keyfile_pfx_map,
                    connection_name=connection_name,
                    database=database,
                    role=role,
                    schema=schema,
                    warehouse=warehouse,
                ) as session:
                    return fn(session, *args, **kwargs)
            except Exception as err:
                raise SystemExit(str(err))

        return wrapped  # type: ignore

    return _decorate_conn_fn


def pytype_sess(meta: T.DataType) -> type:
    """convert Python DB API or Snowpark data type to python type

    Args:
        meta: an instance of snowflake.snowpark.types.DataType

    Returns:
        Python type that matches Snowflake's type, or str in other cases
    """
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
