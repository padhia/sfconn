"get snowflake connection using snowsql connection configuration"
from __future__ import annotations

import logging
import os
import re
import sys
from configparser import ConfigParser
from functools import lru_cache
from getpass import getpass as askpass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from snowflake.connector import connect  # type: ignore

from .privkey import PrivateKey
from .types import Connection

try:
    from keyring import get_password
except ImportError:
    get_password = None

SFCONN_CONFIG_FILE = Path(_p) if (_p := os.environ.get("SFCONN_CONFIG_FILE")) is not None else Path.home() / ".snowsql" / "config"
AUTH_KWDS = ["password", "token", "passcode", "private_key", "private_key_path"]

relpath_anchor_is_cwd = os.environ.get("SFCONN_RELPATH_ANCHOR_CWD", "0").upper() in ["YES", "1", "TRUE", "Y"]
logger = logging.getLogger(__name__)


def getpass(host: str, user: str) -> str:
    "return password from user's keyring if found; else prompt for it"
    if get_password is not None and (passwd := get_password(host, user)) is not None:
        logger.debug("Using password from user's keyring: %s@%s", user, host)
        return passwd
    return askpass(f"Password '{user}@{host}': ")


@lru_cache(maxsize=None)
def load_config(config_file: Path = SFCONN_CONFIG_FILE) -> Dict[Optional[str], Dict[str, Any]]:
    """load connections from configuration file

    Args:
        config_file: Configuration file containing connection entries, optiional, defaults to ~/.snowsql/config

    Returns:
        dictionary of connection names and dictionary of options

    Raises:
        FileNotFoundError: If the config_file doesn't exist or not a file
        MissingSectionHeaderError: If config_file doesn't contain any section, or is invalid
    """

    def dbapi_opt(key: str, val: str) -> tuple[str, Any]:
        "convert snowsql connection option to corresponding python DB API connect() option"
        if (m := re.fullmatch("(user|role|account|schema|warehouse)name", key)) is not None:
            return (m.group(1), val)
        if key == "dbname":
            return ("database", val)
        if key == "private_key_path":
            path = Path(val).expanduser()
            if not path.is_absolute():
                path = (Path.cwd() if relpath_anchor_is_cwd else config_file.parent) / path
            return (key, path)
        if key == "password":
            if val[0] == '"' and val[-1] == '"' or val[0] == "'" and val[-1] == "'":
                val = val[1:-1].replace("\\'", "'").replace('\\"', '"')
        return (key, val)

    def conn_name(name: str) -> Optional[str]:
        return name[12:] if name.startswith("connections.") else None

    def conn_opts(section: Mapping[str, Any]) -> Dict[str, Any]:
        return dict(dbapi_opt(k, v) for k, v in section.items())

    if not config_file.is_file():
        raise FileNotFoundError(f"{config_file} does not exist or is not a file")

    conf = ConfigParser()
    conf.read(config_file)

    return {conn_name(name): conn_opts(conf[name]) for name in conf.sections() if name.startswith("connections")}


def conn_opts(
    name: Optional[str] = None, config_file: Path = SFCONN_CONFIG_FILE, expand_private_key: bool = True, **overrides: Any
) -> Dict[str, Any]:
    """return unified connection options

    Args:
        name: A connection name to be looked up from the config_file; value can be None
        config_file: Configuration file containing connection entries, defaults to ~/.snowsql/config
        expand_private_key: whether to read private_key_path, if present; default True
        **overrides: A valid Snowflake python connector parameter; when not-None, will override value read from config_file

    Returns:
        dictionary containing option name and it's value

    Raises:
        KeyError: when connection name lookup fails
        *: any exceptions raised by load_config() are passed through
    """
    if name is None:
        name = os.environ.get("SFCONN")
    conf_opts = load_config(config_file).get(name)
    if conf_opts is None:
        if name is None:
            raise KeyError("Connection name required (otherwise, either set SFCONN=<conn> or define a default connection)")
        else:
            raise KeyError(f"'{name}' is not a configured connection in '{config_file}'")

    opts = dict(conf_opts, **{k: v for k, v in overrides.items() if v is not None})

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug("getcon() options: %s", {k: v if k not in AUTH_KWDS else "*****" for k, v in opts.items()})

    if expand_private_key and "private_key_path" in opts:
        opts["private_key"] = PrivateKey(opts["private_key_path"]).pri_bytes
        del opts["private_key_path"]

    has_login = all(o in opts for o in ["user", "account"])
    has_auth = any(o in opts for o in AUTH_KWDS)

    if has_login and not has_auth and opts.get("authenticator") != "externalbrowser":
        opts["password"] = getpass(opts["account"], opts["user"])

    # set application name if not already specified and one is available
    if "application" not in overrides and sys.argv[0] and (app_name := Path(sys.argv[0]).name):
        opts["application"] = app_name

    return opts


def getconn(name: Optional[str] = None, **overrides: Any) -> Connection:
    """connect to Snowflake database using named configuration

    Args
        name: A connection name to be looked up from the config_file, optional defaults to None for default connection
        **overrides: Any parameter that is valid for conn_opts() method; see conn_opts() documentation

    Returns:
        Connection object returned by Snowflake python connector

    Exceptions:
        KeyError: when connection name lookup fails
        FileNotFoundError: If the config_file doesn't exist or not a file (from conn_opts())
        MissingSectionHeaderError: If config_file doesn't contain any section, or is invalid (from conn_opts)
        InterfaceError/DatabaseError: from snowflake.connector.connect()
    """
    return connect(**conn_opts(name, **overrides))


def getconn_checked(name: Optional[str] = None, **overrides: Any) -> Connection:
    """same as getconn(), but terminates the current application if an exception is thrown

    Args
        name: A connection name to be looked up from the config_file, optional defaults to None for default connection
        **overrides: Any parameter that is valid for conn_opts() method; see conn_opts() documentation

    Returns:
        Connection object returned by Snowflake python connector
    """
    try:
        return getconn(name, **overrides)
    except Exception as err:
        raise SystemExit(err)
