"test Cursor class"
import datetime as dt
from collections import namedtuple
from dataclasses import dataclass

import pytest

from sfconn import ProgrammingError, getconn

SQL = "select current_user() as user, current_date() as date"


def test_run_query_func() -> None:
    Result = namedtuple("Result", ["user", "date"])  # type: ignore

    def mkResult(x: str, y: dt.date) -> Result:
        return Result(x, y)

    with getconn() as cnx, cnx.cursor() as csr:
        csr.run_query1(mkResult, SQL)


def test_run_query_class() -> None:
    @dataclass
    class Result:
        user: str
        date: dt.date

    with getconn() as cnx, cnx.cursor() as csr:
        assert isinstance(csr.run_query1(Result, SQL), Result)


def test_run_query_class_elem_order() -> None:
    "class with elements defined in different order than SELECT"

    @dataclass
    class Result:
        date: dt.date
        user: str

    with getconn() as cnx, cnx.cursor() as csr:
        assert isinstance(csr.run_query1(Result, SQL), Result)


def test_run_query_class_fewer_elems() -> None:
    "class with elements defined with fewer elements than SELECT"

    @dataclass
    class Result:
        date: dt.date

    with getconn() as cnx, cnx.cursor() as csr:
        assert isinstance(csr.run_query1(Result, SQL), Result)


def test_run_query_class_noinit() -> None:
    class Result:
        user: str
        date: dt.date

    with pytest.raises(TypeError):
        with getconn() as cnx, cnx.cursor() as csr:
            csr.run_query1(Result, SQL)


def test_run_query_bad_columns() -> None:
    "when __init__ has arguments whose names do not match any columns"

    class Result:
        user: str
        date: dt.date

        def __init__(self, x: str, y: str) -> None:
            self.user, self.role = x, y

    with pytest.raises(ProgrammingError):
        with getconn() as cnx, cnx.cursor() as csr:
            csr.run_query1(Result, SQL)


def test_select1_norows() -> None:
    "test an exception is thrown when no rows are returned for run_query1() call"
    with pytest.raises(ProgrammingError):
        with getconn() as cnx, cnx.cursor() as csr:
            csr.run_query1(lambda *x: x, SQL + " where 1 = 0")
