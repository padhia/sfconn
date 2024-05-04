"test connection options"

from pathlib import Path

import pytest

from sfconn import get_token


def test_keypair(config_keypair: Path) -> None:
    assert get_token("default") is not None


def test_non_keypair(config_password: Path) -> None:
    with pytest.raises(ValueError):
        get_token("default")
