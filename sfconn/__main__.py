"connection utilities"
from argparse import ArgumentParser
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from .conn import load_config
from .jwt import LIFETIME, get_token
from .utils import _conn_opts_checked, _connect_checked, args

try:
	from keyring import set_password
	_use_keyring = True
except ImportError:
	_use_keyring = False


def list_conn(config_file: Path, **_: Any) -> None:
	"list all connections"
	cfg = load_config(config_file)

	lines: list[tuple[str, str, str]] = [('Conn', 'Account', 'User')]
	lines.extend(sorted(('' if name is None else name, opts['account'], opts.get('user', '')) for name, opts in cfg.items()))

	w = [max(len(r[c]) for r in lines) for c in [0, 1, 2]]

	def printf(n: str, a: str, u: str) -> None:
		print(f"{n:{w[0]}}  {a:{w[1]}}  {u}")

	for e, (name, acct, user) in enumerate(lines):
		printf(name, acct, user)
		if e == 0:
			printf('-' * w[0], '-' * w[1], '-' * w[2])


def test_conn(conn: Optional[str], save: bool = False, **kwargs: Any) -> None:
	"test connection"
	opts = _conn_opts_checked(conn, **kwargs)
	with _connect_checked(**opts):
		if _use_keyring and save and all(o in opts for o in ["account", "user", "password"]):
			set_password(opts["account"], opts["user"], opts["password"])
		print("connection successful!")


def get_jwt(conn: Optional[str], config_file: Path, lifetime: timedelta, **kwargs: Any) -> None:
	"get a JWT"
	try:
		print(get_token(conn, config_file=config_file, lifetime=lifetime))
	except Exception as msg:
		raise SystemExit(msg)


def main(cmd: Callable[..., None], **opts: Any) -> None:
	cmd(**opts)


@args(__doc__, prog="python -m sfconn")
def getargs(parser: ArgumentParser) -> None:
	"process run-time arguments"
	parser.set_defaults(cmd='list')
	parser.set_defaults(cmd=list_conn)

	def minutes(s: str) -> timedelta:
		return timedelta(minutes=int(s))

	sp = parser.add_subparsers()

	p = sp.add_parser('list', help='list all connections')
	p.set_defaults(cmd=list_conn)

	p = sp.add_parser('test', help='test a connection')
	p.set_defaults(cmd=test_conn)
	if _use_keyring:
		p.add_argument('--save', action='store_true', help="save password in secure local storage")

	p = sp.add_parser('jwt', help='get a JWT')
	p.set_defaults(cmd=get_jwt)
	p.add_argument('--lifetime', metavar='MINUTES', type=minutes, default=LIFETIME,
		help=f"lifetime of the JWT (default {LIFETIME.seconds // 60} minutes)")


main(**vars(getargs()))
