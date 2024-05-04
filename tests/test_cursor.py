"test Cursor class"

import datetime as dt
from collections import namedtuple
from dataclasses import dataclass

import pytest

from sfconn import Connection, DataError, ProgrammingError

SQL = "select current_user() as user, current_date() as date"


def test_run_query_func(cnx: Connection) -> None:
    Result = namedtuple("Result", ["user", "date"])  # type: ignore

    def mkResult(x: str, y: dt.date) -> Result:
        return Result(x, y)

    with cnx.cursor() as csr:
        assert isinstance(csr.run_query1(mkResult, SQL), Result)


def test_run_query_columns(cnx: Connection) -> None:
    @dataclass
    class Result:
        one: int
        three: int

    with cnx.cursor() as csr:
        r = csr.run_query1(Result, 'select 1 as "one", 2 as "two", 3 as "three"', select=["one", "three"])
        assert r == Result(1, 3)


def test_run_query_class(cnx: Connection) -> None:
    @dataclass
    class Result:
        user: str
        date: dt.date

    with cnx.cursor() as csr:
        assert isinstance(csr.run_query1(Result, SQL), Result)


def test_run_query_class_elem_order(cnx: Connection) -> None:
    "class with elements defined in different order than SELECT"

    @dataclass
    class Result:
        date: dt.date
        user: str

    with cnx.cursor() as csr:
        assert isinstance(csr.run_query1(Result, SQL), Result)


def test_run_query_class_fewer_elems(cnx: Connection) -> None:
    "class with elements defined with fewer elements than SELECT"

    @dataclass
    class Result:
        date: dt.date

    with cnx.cursor() as csr:
        assert isinstance(csr.run_query1(Result, SQL), Result)


def test_run_query_class_noinit(cnx: Connection) -> None:
    class Result:
        user: str
        date: dt.date

    with pytest.raises(TypeError):
        with cnx.cursor() as csr:
            csr.run_query1(Result, SQL)


def test_run_query_bad_columns(cnx: Connection) -> None:
    "when __init__ has arguments whose names do not match any columns"

    class Result:
        user: str
        date: dt.date

        def __init__(self, x: str, y: str) -> None:
            self.user, self.role = x, y

    with pytest.raises(ProgrammingError):
        with cnx.cursor() as csr:
            csr.run_query1(Result, SQL)


def test_select1_norows(cnx: Connection) -> None:
    "test an exception is thrown when no rows are returned for run_query1() call"
    with pytest.raises(DataError):
        with cnx.cursor() as csr:
            csr.run_query1(lambda *x: x, SQL + " where 1 = 0")
