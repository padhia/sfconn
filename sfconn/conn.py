"get snowflake connection using snowsql connection configuration"
from __future__ import annotations

import logging
import os
import re
import sys
from configparser import ConfigParser
from functools import cache
from getpass import getpass as askpass
from pathlib import Path
from typing import Any, Optional

from snowflake.connector import connect

from .privkey import PrivateKey
from .types import Connection, InterfaceError

try:
	from keyring import get_password
	_use_keyring = True
except ImportError:
	_use_keyring = False

AUTH_KWDS = ["password", "token", "passcode", "private_key"]
SFCONN_CONFIG_FILE = Path(_p) if (_p := os.environ.get("SFCONN_CONFIG_FILE")) is not None else Path.home() / '.snowsql' / 'config'
logger = logging.getLogger(__name__)


def getpass(host: str, user: str) -> str:
	"return password from user's keyring if found; else prompt for it"
	if _use_keyring and (passwd := get_password(host, user)) is not None:
		logger.debug("Using password from user's keyring: %s@%s", user, host)
		return passwd
	return askpass(f"Password '{user}@{host}': ")


@cache
def load_config(config_file: Path = SFCONN_CONFIG_FILE) -> dict[Optional[str], dict[str, Any]]:
	"load connections from configuration file"
	def dbapi_opt(key: str, val: str) -> tuple[str, Any]:
		"convert snowsql connection option to corresponding python DB API connect() option"
		if (m := re.fullmatch('(user|role|account|schema|warehouse)name', key)) is not None:
			return (m.group(1), val)
		if key == 'dbname':
			return ('database', val)
		return (key, val)

	def conn_name(name: str) -> Optional[str]:
		return None if name == "connections" else name.removeprefix("connections.")

	def conn_opts(section) -> dict[str, Any]:
		return dict(dbapi_opt(k, v) for k, v in section.items())

	if not config_file.is_file():
		raise FileNotFoundError(f"{config_file} does not exist or is not a file")

	conf = ConfigParser()
	conf.read(config_file)

	return {conn_name(name): conn_opts(conf[name]) for name in conf.sections() if name.startswith("connections")}


def _conn_opts(name: Optional[str] = None, config_file: Path = SFCONN_CONFIG_FILE, **overrides) -> dict[str, Any]:
	"return unified connection options"
	conf_opts = load_config(config_file).get(name)
	if conf_opts is None:
		if name is None:
			raise ValueError(f"connection name was not supplied and no default connection was configured in '{config_file}'")
		else:
			raise ValueError(f"'{name}' is not a configured connection in '{config_file}'")

	opts = conf_opts | {k: v for k, v in overrides.items() if v is not None}
	if 'account' not in opts:
		raise InterfaceError("Snowflake account name is required")

	if logger.getEffectiveLevel() <= logging.DEBUG:
		logger.debug("getcon() options: %s", {k: v if k not in AUTH_KWDS else '*****' for k, v in opts.items()})

	if 'private_key_path' in opts:
		opts['private_key'] = PrivateKey.from_file(opts['private_key_path']).pri_bytes
		del opts['private_key_path']

	has_login = all(o in opts for o in ["user", "account"])
	has_auth = any(o in opts for o in AUTH_KWDS)

	if has_login and not has_auth and opts.get('authenticator') != 'externalbrowser':
		opts |= {"password": getpass(opts["account"], opts["user"])}

	# set application name if not already specified and one is available
	if 'application' not in opts and sys.argv[0] and (app_name := Path(sys.argv[0]).name):
		opts['application'] = app_name

	return opts


def getconn(name: Optional[str] = None, **overrides) -> Connection:
	"return a connection object for the specified name or default connection if name is None"
	return connect(**_conn_opts(name, **overrides))
