"test pytype function"

from datetime import date, datetime, time
from decimal import Decimal
from textwrap import dedent

from sfconn import Connection, pytype


def test_number(cnx: Connection) -> None:
    with cnx.cursor() as csr:
        sql = dedent(
            """\
            select 123
                 , 123.45
			     , 123.45::float"""
        )
        csr.describe(sql)
        assert pytype(csr.description[0]) == int
        assert pytype(csr.description[1]) == Decimal
        assert pytype(csr.description[2]) == float


def test_temporal(cnx: Connection) -> None:
    with cnx.cursor() as csr:
        sql = dedent(
            """\
            select current_date()
                 , current_time()
			     , current_timestamp()"""
        )
        csr.describe(sql)
        assert pytype(csr.description[0]) == date
        assert pytype(csr.description[1]) == time
        assert pytype(csr.description[2]) == datetime


def test_unstructured(cnx: Connection) -> None:
    with cnx.cursor() as csr:
        sql = dedent(
            """\
            select object_construct('ATTR1', 1, 'ATTR2', CURRENT_DATE())
                 , array_construct(10, 20, 30)
                 , parse_json('{"pi":3.14,"e":2.71}')"""
        )
        csr.describe(sql)
        assert pytype(csr.description[0]) == str
        assert pytype(csr.description[1]) == str
        assert pytype(csr.description[2]) == str

        assert pytype(csr.description[0], best_match=True) == dict
        assert pytype(csr.description[1], best_match=True) == list
        assert pytype(csr.description[2], best_match=True) == object


def test_other(cnx: Connection) -> None:
    with cnx.cursor() as csr:
        sql = "select 0 = 1, to_binary('F0', 'hex')"
        csr.describe(sql)
        assert pytype(csr.description[0]) == bool
        assert pytype(csr.description[1]) == bytearray
