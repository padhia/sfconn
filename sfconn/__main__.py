"manage connections"
from argparse import ArgumentParser
from typing import Optional

from .conn import _conn_opts, connect, from_arg, load_config
from .types import DatabaseError, InterfaceError

try:
	from keyring import set_password
	_use_keyring = True
except ImportError:
	_use_keyring = False


def list_conn() -> None:
	"list all connections"
	cfg = load_config()

	lines: list[tuple[str, str]] = [('Name', 'Account')]
	lines.extend(sorted(('' if name is None else name, opts['account']) for name, opts in cfg.items()))

	name_w = max(len(p[0]) for p in lines)
	acct_w = max(len(p[1]) for p in lines)

	def printf(n: str, a: str) -> None:
		print(f"{n:{name_w}}  {a:{acct_w}}")

	for e, (name, acct) in enumerate(lines):
		printf(name, acct)
		if e == 0:
			printf('-' * name_w, '-' * acct_w)


def test_conn(name: Optional[str], save: bool = False) -> None:
	"test connection"
	try:
		opts = _conn_opts(name)
		with connect(**opts):
			if _use_keyring and save and all(o in opts for o in ["account", "user", "password"]):
				set_password(opts["account"], opts["user"], opts["password"])
			print("connection successful!")
	except (InterfaceError, DatabaseError) as e:
		raise SystemExit((str(e)))


def main() -> None:
	parser = ArgumentParser(prog="python -m sfconn", description=__doc__)
	parser.set_defaults(cmd='list')

	sp = parser.add_subparsers()

	p = sp.add_parser('list', help='list connections')
	p.set_defaults(cmd='list')

	p = sp.add_parser('test', help='test a connection')
	p.add_argument('name', nargs='?', type=from_arg, help="connection name from ~/.snowsql/config")
	p.set_defaults(cmd='test')
	if _use_keyring:
		p.add_argument('--save', action='store_true', help="save password in secure local storage")

	opts = vars(parser.parse_args())
	cmd = opts.pop('cmd')
	if cmd == 'test':
		test_conn(**opts)
	elif cmd == 'list':
		list_conn()


main()
