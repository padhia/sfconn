"test getconn() method"
from sfconn import Connection, Cursor, getconn


def test_getconn() -> None:
    with getconn() as cnx, cnx.cursor() as csr:
        assert isinstance(cnx, Connection)
        assert isinstance(csr, Cursor)
        csr.execute("select current_user() as user, current_role() as role")
        assert csr.rowcount == 1
