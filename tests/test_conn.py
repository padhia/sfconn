"test connection options"
from pathlib import Path

import sfconn
from sfconn.conn import conn_opts


def test_connopts(config: Path) -> None:
    assert conn_opts('dev', config_file=config) == dict(
        account="sfdev",
        user="dev_user",
        password="123456",
        database="dev_db",
        application="pytest")


def test_connopts_app_none(config: Path) -> None:
    assert conn_opts('dev', config_file=config, application=None) == dict(
        account="sfdev",
        user="dev_user",
        password="123456",
        database="dev_db")


def test_connopts_default(config_default: Path) -> None:
    assert conn_opts(None, config_file=config_default) == dict(
        account="sfdev",
        user="dev_user",
        password="123456",
        database="dev_db",
        application="pytest")


def test_conn_overrides(config: Path) -> None:
    assert conn_opts('dev', config_file=config, database="new_db")["database"] == "new_db"


def test_no_pkey_expand(config_keypair: Path) -> None:
    assert "private_key_path" in conn_opts('dev', config_file=config_keypair, expand_private_key=False)


def test_relpath_config(config_privkey_path: Path) -> None:
    opts = conn_opts("dev", config_file=config_privkey_path, expand_private_key=False)
    assert opts["private_key_path"].parent == config_privkey_path.parent / "keys"


def test_relpath_cwd(config_privkey_path: Path) -> None:
    sfconn.conn.relpath_anchor_is_cwd = True
    opts = conn_opts("dev", config_file=config_privkey_path, expand_private_key=False)
    sfconn.conn.relpath_anchor_is_cwd = False

    assert opts["private_key_path"].parent == Path.cwd() / "keys"
