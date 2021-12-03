"get a JWT token"
import argparse
import base64
import datetime as dt
import hashlib
import sys
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


def conn_config(name: Optional[str], config_path: Path = SFCONN_CONFIG_FILE) -> tuple[str, str]:
	def clean(account: str) -> str:
		if '.global' not in account:
			if (idx := account.find('.')) > 0:
				return account[:idx]
		else:
			if (idx := account.find('-')) > 0:
				return account[:idx]
		return account

	opts = load_config(config_path).get(name)
	if opts is None:
		raise argparse.ArgumentTypeError(f"Undefined connection '{name}'" if name is not None else "No default connection has been defined")
	if 'private_key_path' not in opts:
		raise argparse.ArgumentTypeError("JWT can be obtained only for accounts that use key-pair authentication")

	return (opts['private_key_path'], f"{clean(opts['account']).upper()}.{opts['user'].upper()}")


def get_token(conn: Optional[str], lifetime: dt.timedelta = LIFETIME) -> str:
	keyf, qual_user = conn_config(conn)

	key = PrivateKey.from_file(keyf)
	now = dt.datetime.now()

	payload = {
		"iss": f"{qual_user}.{fingerprint(key.pub_bytes)}",
		"sub": f"{qual_user}",
		"iat": int(now.timestamp()),
		"exp": int((now + lifetime).timestamp())
	}

	return jwt.encode(payload, key=key.key, algorithm=ALGORITHM)  # type: ignore


def jwt_conn_arg(parser: argparse.ArgumentParser) -> None:
	def valid_conn(n: str) -> str:
		conn_config(n)
		return n

	try:
		conn_config(None)
		conn_reqd = True
	except argparse.ArgumentTypeError:
		conn_reqd = False

	parser.add_argument('-c', '--conn', metavar='NAME', type=valid_conn, required=conn_reqd is None,
		help="snowsql connection name (from ~/.snowsql/config)")


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('token_file', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
		help='file path to save the generated token to, default stdout')
	jwt_conn_arg(parser)
	parser.add_argument('--lifetime', metavar='MINUTES', type=lambda v: dt.timedelta(minutes=int(v)), default=dt.timedelta(minutes=59),
		help='The number of minutes that the JWT should be valid for.')
	args = parser.parse_args()

	args.token_file.write(get_token(args.conn, lifetime=args.lifetime))


if __name__ == "__main__":
	main()
