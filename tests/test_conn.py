"test getconn() method"

from sfconn import Connection, Cursor


def test_getconn(cnx: Connection) -> None:
    with cnx.cursor() as csr:
        assert isinstance(cnx, Connection)
        assert isinstance(csr, Cursor)
        csr.execute("select current_user() as user, current_role() as role")
        assert csr.rowcount == 1
