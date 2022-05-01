"get a JWT token"
import base64
import datetime as dt
import hashlib
from pathlib import Path
from typing import Optional

import jwt

from .conn import SFCONN_CONFIG_FILE, load_config
from .privkey import PrivateKey

LIFETIME = dt.timedelta(minutes=59)  # The tokens will have a 59 minute lifetime
RENEWAL_DELTA = dt.timedelta(minutes=54)  # Tokens will be renewed after 54 minutes
ALGORITHM = "RS256"  # Tokens will be generated using RSA with SHA256


def fingerprint(data: bytes) -> str:
	sha256hash = hashlib.sha256()
	sha256hash.update(data)
	return 'SHA256:' + base64.b64encode(sha256hash.digest()).decode('utf-8')


def _token_opts(name: Optional[str], config_file: Path = SFCONN_CONFIG_FILE) -> tuple[str, str]:
	def clean(account: str) -> str:
		if '.global' not in account:
			if (idx := account.find('.')) > 0:
				return account[:idx]
		else:
			if (idx := account.find('-')) > 0:
				return account[:idx]
		return account

	opts = load_config(config_file).get(name)
	if opts is None:
		if name is None:
			raise ValueError(f"connection name was not supplied and no default connection was configured in '{config_file}'")
		else:
			raise ValueError(f"'{name}' is not a configured connection in '{config_file}'")
	if (keyf := opts.get('private_key_path')) is None:
		raise ValueError(f"'{name}' does not use key-pair authentication to support creating a JWT")

	return (keyf, f"{clean(opts['account']).upper()}.{opts['user'].upper()}")


def get_token(conn: Optional[str], lifetime: dt.timedelta = LIFETIME, config_file: Path = SFCONN_CONFIG_FILE) -> str:
	keyf, qual_user = _token_opts(conn, config_file=config_file)

	key = PrivateKey.from_file(keyf)
	now = dt.datetime.now()

	payload = {
		"iss": f"{qual_user}.{fingerprint(key.pub_bytes)}",
		"sub": f"{qual_user}",
		"iat": int(now.timestamp()),
		"exp": int((now + lifetime).timestamp())
	}

	return jwt.encode(payload, key=key.key, algorithm=ALGORITHM)  # type: ignore
