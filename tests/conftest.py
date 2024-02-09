from pathlib import Path
from typing import cast

import cryptography.hazmat.primitives.serialization as Ser
import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from OpenSSL.crypto import TYPE_RSA, PKey  # type: ignore
from snowflake.connector.config_manager import CONFIG_MANAGER


def _write_config(config_file: Path, **args: str) -> Path:
    opts = "".join(f'{k} = "{v}"\n' for k, v in args.items())
    config_file.write_text(f"[default]\n{opts}")
    config_file.chmod(0o600)

    for i, s in enumerate(CONFIG_MANAGER._slices):  # type: ignore
        if s.section == "connections":
            CONFIG_MANAGER._slices[i] = s._replace(path=config_file)  # type: ignore
            CONFIG_MANAGER.read_config()
            break

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

    return _write_config(
        tmp_path / "config_pkey",
        account="sfdev",
        user="dev_user",
        authenticator="SNOWFLAKE_JWT",
        private_key_file=str(private_key_path),
    )


@pytest.fixture
def config_password(tmp_path: Path) -> Path:
    "config"
    return _write_config(
        tmp_path / "config_password", account="sfdev", user="dev_user", authenticator="SNOWFLAKE", password="12345"
    )
