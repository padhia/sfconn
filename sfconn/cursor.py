"Snowflake cursor class"

from inspect import currentframe, getframeinfo
from logging import DEBUG, getLogger
from typing import Any, Callable, Iterable, Self, Sequence, TypeAlias, TypeVar, cast

from snowflake.connector.cursor import SnowflakeCursor
from snowflake.connector.errors import DataError, ProgrammingError

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

    def run_query(
        self, rec: Callable[..., T] | type[T], sql: str, params: Params = None, *, select: list[str] | None = None
    ) -> Iterable[T]:
        """execute a SELECT statement, map rows to produce instances of type T

        Args:
            rec: must be either
                 - a Callable that accepts columns from the result-set as arguments. column names and the order are described in 'select'
                 - a class T, whose __init__ method accepts columns from result-set as arguments. column names and the order are described in 'select'
            sql: SELECT SQL query text
            params: optional parameters as a Sequence or a dict
            select: an optional, keyword only, argument that explicitly specifies the list of result-set columns to use.
                    When omitted, default list of columns is picked based on 'rec' as follows:
                    - for Callable, all columns from the result-set in result-set order
                    - for class T, upper-cased argument names of T.__init__ method in the argument order

        Returns:
            Iterable over instance of the type T or a tuple of values of only the selected columns

        Raises:
            ProgrammingError if argument or attribute name needed to instantiate T is not a column from the result-set
        """

        def get_init_args(rec: type[Any]) -> list[str]:
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

        self.execute_debug(sql)

        if select:
            col_pos = get_col_pos(select)
        else:
            if isinstance(rec, type):
                col_pos = get_col_pos(get_init_args(rec))
            elif callable(rec):
                col_pos = list(range(len(self.description)))
            else:
                raise TypeError(f"'{rec}' must be either ")

        return (rec(*(row[e] for e in col_pos)) for row in self)  # type: ignore

    def run_query1_opt(
        self, rec: Callable[..., T] | type[T], sql: str, params: Params = None, *, select: list[str] | None = None
    ) -> T | None:
        """execute a SELECT statement, return the first row mapped using the provided function

        Args:
            rec: must be either
                 - a Callable that accepts columns from the result-set as arguments. column names and the order are described in 'select'
                 - a class T, whose __init__ method accepts columns from result-set as arguments. column names and the order are described in 'select'
            sql: SELECT SQL query text
            params: optional parameters as a Sequence or a dict
            select: an optional, keyword only, argument that explicitly specifies the list of result-set columns to use.
                    When omitted, default list of columns is picked based on 'rec' as follows:
                    - for Callable, all columns from the result-set in result-set order
                    - for class T, upper-cased argument names of T.__init__ method in the argument order

        Returns:
            Iterable over instance of the type T or a tuple of values of only the selected columns

        Raises:
            ProgrammingError if argument or attribute name needed to instantiate T is not a column from the result-set
        """
        return next(iter(self.run_query(rec, sql, params, select=select)), None)

    def run_query1(
        self, rec: Callable[..., T] | type[T], sql: str, params: Params = None, *, select: list[str] | None = None
    ) -> T:
        """execute a SELECT statement, return the first row mapped using the provided function

        Args:
            rec: must be either
                 - a Callable that accepts columns from the result-set as arguments. column names and the order are described in 'select'
                 - a class T, whose __init__ method accepts columns from result-set as arguments. column names and the order are described in 'select'
            sql: SELECT SQL query text
            params: optional parameters as a Sequence or a dict
            select: an optional, keyword only, argument that explicitly specifies the list of result-set columns to use.
                    When omitted, default list of columns is picked based on 'rec' as follows:
                    - for Callable, all columns from the result-set in result-set order
                    - for class T, upper-cased argument names of T.__init__ method in the argument order

        Returns:
            Iterable over instance of the type T or a tuple of values of only the selected columns

        Raises:
            ProgrammingError if argument or attribute name needed to instantiate T is not a column from the result-set
            DataError if at least one is not available in the result-set
        """
        row = self.run_query1_opt(rec, sql, params, select=select)
        if row is None:
            raise DataError("no data available")

        return row
