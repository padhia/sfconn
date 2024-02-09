"Snowflake cursor class"
from inspect import currentframe, getframeinfo
from logging import DEBUG, getLogger
from typing import Any, Callable, Iterable, Self, Sequence, TypeAlias, TypeVar, cast

from snowflake.connector.cursor import SnowflakeCursor
from snowflake.connector.errors import ProgrammingError

logger = getLogger(__name__)
T = TypeVar("T")
Params: TypeAlias = Sequence[Any] | dict[Any, Any] | None


class Cursor(SnowflakeCursor):
    "A Cursor class that adds a few convenience methods to Snowflake provided cursor class"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any, **kwargs: Any):
        return super().__exit__(*args, **kwargs)

    def execute_debug(self, sql: str, params: Params = None) -> Self:
        """execute a SQL statement in a debug mode by logging each SQL at DEBUG level

        Args:
            sql: SQL query text
            params: statement parameters, optional

        Returns:
            Self
        """
        if logger.getEffectiveLevel() <= DEBUG:
            fi = getframeinfo(currentframe().f_back.f_back)  # type: ignore
            logger.debug(
                "Running SQL, file: %s, line: %d, function: %s\n%s;",
                fi.filename,
                fi.lineno,
                fi.function,
                sql.replace("\t", "    "),
            )
        self.execute(sql, params=params)
        return self

    def run_query(self, rec: Callable[..., T] | type[T], sql: str, params: Params = None) -> Iterable[T]:
        """execute a SELECT statement, map rows to produce instances of type T

        Args:
            rec: must be either
                 - a Callable that accepts each column of a as a parameter in the same order and returns instance of T
                 - a class T, whose __init__ method argument names must match some column names when upper-cased.
                   Only the matching column names are passed to T.__init__() in the argument order
            sql: SELECT SQL query text
            params: optional parameters as a Sequence or a dict

        Returns:
            Iterable over instance of the type T
        """

        def mk_class(fn: Callable[..., T]) -> Iterable[T]:
            return (fn(*r) for r in cast(Iterable[tuple[Any, ...]], self.execute_debug(sql, params)))

        def get_elems() -> list[str]:
            try:
                elems = [c.upper() for c in cast(dict[str, type], rec.__init__.__annotations__) if c != "return"]
                if len(elems) == 0:
                    raise TypeError(f"'{rec}.__init__()' takes no arguments")
                return elems
            except AttributeError:
                raise TypeError(f"'{rec}.__init__()' takes no arguments")

        def get_col_pos(elems: list[str]) -> list[int]:
            try:
                cols = {d.name: e for e, d in enumerate(self.description)}
                return [cols[a] for a in elems]
            except KeyError as err:
                raise ProgrammingError(f"Column access error: {err} in SQL: {sql}")

        if isinstance(rec, type):
            elems = get_elems()
            self.execute_debug(sql)
            pos = get_col_pos(elems)
            return mk_class(lambda *r: rec(*(r[e] for e in pos)))  # type: ignore

        if callable(rec):
            return mk_class(rec)

        raise TypeError(f"'{rec}' must be either ")

    def run_query1_opt(self, rec: Callable[..., T] | type[T], sql: str, params: Params = None) -> T | None:
        """execute a SELECT statement, return the first row mapped using the provided function

        Args:
            rec: must be either
                 - a Callable that accepts each column of a as a parameter in the same order and returns instance of T
                 - a class T, whose __init__ method argument names must match some column names when upper-cased.
                   Only the matching column names are passed to T.__init__() in the argument order
            sql: SELECT SQL query text
            params: optional parameters as a Sequence or a dict

        Returns:
            Iterable over instance of the type T
        """
        return next(iter(self.run_query(rec, sql, params)), None)

    def run_query1(self, rec: Callable[..., T] | type[T], sql: str, params: Params = None) -> T:
        """execute a SELECT statement, return the first row mapped using the provided function

        Args:
            rec: must be either
                 - a Callable that accepts each column of a as a parameter in the same order and returns instance of T
                 - a class T, whose __init__ method argument names must match some column names when upper-cased.
                   Only the matching column names are passed to T.__init__() in the argument order
            sql: SELECT SQL query text
            params: optional parameters as a Sequence or a dict

        Returns:
            Iterable over instance of the type T

        Raises:
            ProgrammingError if a row is not available
        """
        row = self.run_query1_opt(rec, sql, params)
        if row is None:
            raise ProgrammingError("no data available")

        return row
