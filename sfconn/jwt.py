"get a JWT token"
import base64
import datetime as dt
import hashlib
from pathlib import Path

import jwt

from .conn import SFCONN_CONFIG_FILE, conn_opts
from .privkey import PrivateKey

LIFETIME = dt.timedelta(minutes=59)  # The tokens will have a 59 minute lifetime
RENEWAL_DELTA = dt.timedelta(minutes=54)  # Tokens will be renewed after 54 minutes
ALGORITHM = "RS256"  # Tokens will be generated using RSA with SHA256


def fingerprint(pubkey: bytes) -> str:
    "base64 encoded fingerprint of the public key"
    sha256hash = hashlib.sha256()
    sha256hash.update(pubkey)
    return "SHA256:" + base64.b64encode(sha256hash.digest()).decode("utf-8")


def _clean_account_name(account: str) -> str:
    "ref: https://docs.snowflake.com/en/developer-guide/sql-api/authenticating.html#generating-a-jwt-in-python"
    if ".global" not in account:
        if (idx := account.find(".")) > 0:
            return account[:idx]
    else:
        if (idx := account.find("-")) > 0:
            return account[:idx]
    return account


def get_token(conn: str | None = None, lifetime: dt.timedelta = LIFETIME, config_file: Path = SFCONN_CONFIG_FILE) -> str:
    """get a JWT when using key-pair authentication

    Args
        conn: A connection name to be looked up from the config_file, optional, default to None for the default connection
        lifetime: issued token's lifetime
        config_path: configuration file, defaults to ~/.snowsql/config

    Returns:
        a JWT

    Exceptions:
        ValueError: if `conn` doesn't support key-pair authentication
        *: Any exceptions raised by either conn_opts() or class PrivateKey
    """

    opts = conn_opts(conn, config_file=config_file, expand_private_key=False)
    if (keyf := opts.get("private_key_path")) is None:
        raise ValueError(f"'{conn}' does not use key-pair authentication to support creating a JWT")

    qual_user = f"{_clean_account_name(opts['account']).upper()}.{opts['user'].upper()}"

    key = PrivateKey(keyf)
    now = dt.datetime.now()

    payload = {
        "iss": f"{qual_user}.{fingerprint(key.pub_bytes)}",
        "sub": f"{qual_user}",
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }

    return jwt.encode(payload, key=key.key, algorithm=ALGORITHM)  # type: ignore
