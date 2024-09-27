"get a JWT token"

import base64
import datetime as dt
import hashlib
from pathlib import Path
from typing import Any, NamedTuple, cast

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


class RestInfo(NamedTuple):
    token: str
    url: str
    database: str | None = None
    schema: str | None = None
    role: str | None = None
    warehouse: str | None = None

    def headers(self, user_agent: str = "sfconn-app") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"{user_agent}",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
        }

    @property
    def conn_opts(self) -> dict[str, str]:
        opts = dict(database=self.database, schema=self.schema, role=self.role, warehouse=self.warehouse)
        return {k: v for k, v in opts.items() if v is not None}


def get_rest_info(
    connection_name: str | None = None,
    lifetime: dt.timedelta = LIFETIME,
    *,
    keyfile_pfx_map: tuple[Path, Path] | None = None,
    **kwargs: str | None
) -> RestInfo:
    """get Jwt object using key-pair authentication

    Args
        conn: A connection name to be looked up from the config_file, optional, default to None for the default connection
        lifetime: issued token's lifetime (default 59 minutes)
        keyfile_pfx_map: if specified must be a a pair of Path values specified as <from-path>:<to-path>, which will
                         be used to temporarily change private_key_file path value if it starts with <from-pahd> prefix

    Returns:
        Jwt object

    Exceptions:
        ValueError: if `conn` doesn't support key-pair authentication
        *: Any exceptions raised by either conn_opts() or class PrivateKey
    """

    opts = conn_opts(connection_name=connection_name, keyfile_pfx_map=keyfile_pfx_map, **kwargs)
    keyf = cast(str | None, opts.get("private_key_file"))
    if keyf is None:
        raise ValueError(f"'{connection_name}' does not use key-pair authentication to support creating a JWT")

    qual_user = f"{_clean_account_name(opts['account']).upper()}.{opts['user'].upper()}"

    key = PrivateKey(Path(keyf))
    now = dt.datetime.now()

    payload: dict[str, Any] = {
        "iss": f"{qual_user}.{fingerprint(key.pub_bytes)}",
        "sub": f"{qual_user}",
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }

    return RestInfo(
        token=jwt.encode(payload, key=key.key, algorithm=ALGORITHM),
        url=f"https://{opts['account']}.snowflakecomputing.com/api/v2/statements",
        database=opts.get("database"),
        schema=opts.get("schema"),
        role=opts.get("role"),
        warehouse=opts.get("warehouse"),
    )


def get_token(
    connection_name: str | None = None,
    lifetime: dt.timedelta = LIFETIME,
    *,
    keyfile_pfx_map: tuple[Path, Path] | None = None,
) -> str:
    """get a JWT when using key-pair authentication

    Args
        conn: A connection name to be looked up from the config_file, optional, default to None for the default connection
        lifetime: issued token's lifetime (default 59 minutes)
        keyfile_pfx_map: if specified must be a a pair of Path values specified as <from-path>:<to-path>, which will
                         be used to temporarily change private_key_file path value if it starts with <from-pahd> prefix

    Returns:
        a JWT

    Exceptions:
        ValueError: if `conn` doesn't support key-pair authentication
        *: Any exceptions raised by either conn_opts() or class PrivateKey
    """
    return get_rest_info(connection_name=connection_name, lifetime=lifetime, keyfile_pfx_map=keyfile_pfx_map).token
