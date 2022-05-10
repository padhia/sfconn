"test connection options"
from pathlib import Path

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


def test_connopts_default(config_default) -> None:
	assert conn_opts(None, config_file=config_default) == dict(
		account="sfdev",
		user="dev_user",
		password="123456",
		database="dev_db",
		application="pytest")


def test_conn_overrides(config: Path) -> None:
	assert conn_opts('dev', config_file=config, database="new_db")["database"] == "new_db"


def test_no_pkey_expand(config_pkey: Path) -> None:
	assert "private_key_path" in conn_opts('dev', config_file=config_pkey, expand_private_key=False)
