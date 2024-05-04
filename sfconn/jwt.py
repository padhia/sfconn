"get a JWT token"

import base64
import datetime as dt
import hashlib
from pathlib import Path
from typing import cast

import jwt

from .conn import conn_opts
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


def get_token(connection_name: str | None = None, lifetime: dt.timedelta = LIFETIME) -> str:
    """get a JWT when using key-pair authentication

    Args
        conn: A connection name to be looked up from the config_file, optional, default to None for the default connection
        lifetime: issued token's lifetime

    Returns:
        a JWT

    Exceptions:
        ValueError: if `conn` doesn't support key-pair authentication
        *: Any exceptions raised by either conn_opts() or class PrivateKey
    """

    opts = conn_opts(connection_name=connection_name)
    keyf = cast(str | None, opts.get("private_key_file"))
    if keyf is None:
        raise ValueError(f"'{connection_name}' does not use key-pair authentication to support creating a JWT")

    qual_user = f"{_clean_account_name(opts['account']).upper()}.{opts['user'].upper()}"

    key = PrivateKey(Path(keyf))
    now = dt.datetime.now()

    payload = {
        "iss": f"{qual_user}.{fingerprint(key.pub_bytes)}",
        "sub": f"{qual_user}",
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }

    return jwt.encode(payload, key=key.key, algorithm=ALGORITHM)  # type: ignore
