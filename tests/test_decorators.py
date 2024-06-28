"test decorators"

from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Any

from sfconn import Connection, with_connection, with_connection_args


def test_decorators() -> None:
    "test decorators"

    @dataclass
    class Result:
        user: str
        role: str

    @with_connection_args(__doc__)
    def getargs(_: ArgumentParser) -> Any:
        pass

    @with_connection()
    def main(cnx: Connection) -> None:
        with cnx.cursor() as csr:
            rows = list(csr.run_query(Result, "select current_user() as user, current_role() as role"))
            assert csr.rowcount == 1
            assert isinstance(rows[0], Result)

    main(**vars(getargs([])))  # type: ignore
