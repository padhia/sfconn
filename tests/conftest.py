import os
from pathlib import Path
from textwrap import dedent
from typing import cast

import cryptography.hazmat.primitives.serialization as Ser
import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from OpenSSL.crypto import TYPE_RSA, PKey  # type: ignore

_config = Path(__file__).parent / "test.conf"
os.environ["SFCONN_CONFIG_FILE"] = str(_config)


@pytest.fixture
def config() -> Path:
	"config"
	return _config


@pytest.fixture
def config_default(tmp_path: Path) -> Path:
	"config"
	config_file = tmp_path / "config_default"
	config_file.write_text(dedent("""\
		[connections]
		accountname = sfdev
		user = dev_user
		password = 123456
		dbname = dev_db

		[connections.prd]
		accountname = sfprd
		user = prd_user
		password = 123456"""))

	return config_file


@pytest.fixture
def config_keypair(tmp_path: Path) -> Path:
	"config"
	pkey = PKey()
	pkey.generate_key(TYPE_RSA, 2048)
	ckey = cast(RSAPrivateKey, pkey.to_cryptography_key())

	private_key_path = tmp_path / "testpkey.p8"
	private_key_path.write_bytes(
		ckey.private_bytes(Ser.Encoding.PEM, format=Ser.PrivateFormat.PKCS8, encryption_algorithm=Ser.NoEncryption())
	)

	config_file = tmp_path / "config_pkey"
	config_file.write_text(dedent(f"""\
		[connections.dev]
		accountname = sfdev
		user = dev_user
		private_key_path = {private_key_path}"""))

	return config_file


@pytest.fixture
def config_privkey_path(tmp_path: Path) -> Path:
	"config"
	config_file = tmp_path / "config_privkey_path"
	config_file.write_text(dedent("""\
		[connections.dev]
		accountname = sfdev
		user = dev_user
		private_key_path = keys/key.p8"""))

	return config_file


@pytest.fixture
def config_invalid(tmp_path: Path) -> Path:
	config_file = tmp_path / "invalid"
	config_file.write_text("Invalid configuration file format\n")

	return config_file


@pytest.fixture
def config_missing(tmp_path: Path) -> Path:
	return tmp_path / "missing"
