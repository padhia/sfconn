"test connection options"
from pathlib import Path

from sfconn.conn import _conn_opts


def test_connopts(config: Path) -> None:
	assert _conn_opts('dev', config_file=config) == dict(
		account="sfdev",
		user="dev_user",
		password="123456",
		database="dev_db",
		application="pytest")


def test_connopts_default(config_default) -> None:
	assert _conn_opts(None, config_file=config_default) == dict(
		account="sfdev",
		user="dev_user",
		password="123456",
		database="dev_db",
		application="pytest")


def test_conn_overrides(config: Path) -> None:
	assert _conn_opts('dev', config_file=config, database="new_db")["database"] == "new_db"
