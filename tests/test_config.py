"test configuration files"
from configparser import MissingSectionHeaderError
from pathlib import Path

import pytest

from sfconn.conn import conn_opts, load_config


def test_missing_config(config_missing: Path) -> None:
    with pytest.raises(FileNotFoundError):
        conn_opts('nonconn', config_file=config_missing)


def test_invalid_config(config_invalid: Path) -> None:
    with pytest.raises(MissingSectionHeaderError):
        conn_opts('nonconn', config_file=config_invalid)


def test_noconn_config(config: Path) -> None:
    with pytest.raises(KeyError):
        conn_opts(None, config_file=config)


def test_config_env(config: Path) -> None:
    assert set(load_config().keys()) == {"dev", "prd"}


def test_no_default_conn(config: Path) -> None:
    with pytest.raises(KeyError):
        conn_opts(None, config_file=config)


def test_default_conn(config_default: Path) -> None:
    assert conn_opts(None, config_file=config_default) is not None


def test_invalid_conn(config: Path) -> None:
    with pytest.raises(KeyError):
        conn_opts('nonconn', config_file=config)
