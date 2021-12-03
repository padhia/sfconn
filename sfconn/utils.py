"Utility functions"
import logging
from argparse import SUPPRESS, ArgumentParser
from typing import Any, Callable, Optional

from . import __name__ as rootpkg
from .conn import from_arg, getconn, load_config

logger = logging.getLogger(__name__)
_loglevel = logging.WARNING


def init_logging(pkgname: str = rootpkg) -> None:
	"initialize the logging system"
	h = logging.StreamHandler()
	h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
	logger = logging.getLogger(pkgname)
	logger.addHandler(h)
	logger.setLevel(_loglevel)


def entry(run: Callable[..., None]) -> Callable[..., None]:
	"make an entry-point"
	def wrapped(
		conn: Optional[str],
		database: Optional[str],
		role: Optional[str],
		schema: Optional[str],
		warehouse: Optional[str],
		loglevel: int,
		**kwargs: Any
	) -> None:
		"script entry-point"
		global _loglevel

		_loglevel = loglevel
		init_logging()
		with getconn(conn, database=database, role=role, schema=schema, warehouse=warehouse) as cnx:
			return run(cnx, **kwargs)

	return wrapped


def add_conn_args(parser: ArgumentParser) -> None:
	"add default arguments"
	g = parser.add_argument_group("connection parameters")
	g.add_argument('-c', '--conn', required=(None not in load_config()), type=from_arg,
		help="snowsql connection name (from ~/.snowsql/config)")
	g.add_argument('--database', metavar='NAME', help='default database to use')
	g.add_argument('--role', metavar='NAME', help='default role to use')
	g.add_argument('--schema', metavar='NAME', help='default schema to use')
	g.add_argument('--warehouse', metavar='NAME', help='default warehouse to use')

	parser.add_argument('--debug', dest='loglevel', action='store_const', const=logging.DEBUG, default=logging.WARNING, help=SUPPRESS)


def args(doc: Optional[str]) -> Callable[..., Callable[..., Any]]:
	"""Function decorator that instantiates and adds snowflake database connection arguments"""
	def getargs(fn: Callable[[ArgumentParser], None]) -> Callable[..., Any]:
		def wrapped(args: Optional[list[str]] = None) -> Any:
			parser = ArgumentParser(description=doc)
			fn(parser)
			add_conn_args(parser)
			return parser.parse_args(args)
		return wrapped
	return getargs
