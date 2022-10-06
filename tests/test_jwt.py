"test connection options"
from pathlib import Path

import pytest

from sfconn import get_token


def test_keypair(config_keypair: Path) -> None:
    assert get_token("dev", config_file=config_keypair) is not None


def test_non_keypair(config: Path) -> None:
    with pytest.raises(ValueError):
        get_token('dev', config_file=config)
