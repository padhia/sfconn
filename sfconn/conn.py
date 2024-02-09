"get a snowflake connection using connections.toml configuration with added convenience methods"
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Self, cast

from snowflake.connector.config_manager import CONFIG_MANAGER
from snowflake.connector.connection import SnowflakeConnection, SnowflakeCursor
from snowflake.connector.errors import Error

from .cursor import Cursor

logger = logging.getLogger(__name__)


def _parse_keyfile_pfx_map() -> tuple[Path, Path] | None:
    if (x := os.environ.get("SFCONN_KEYFILE_PFX_MAP")) is None:
        return None

    try:
        from_pfx, to_pfx = x.split(":")
        return (Path(from_pfx), Path(to_pfx))
    except ValueError:
        pass

    logger.error(f"Bad value ('{x}') for $SFCONN_KEYFILE_PFX_MAP ignored, must have a pair of paths specified as'<path>:<path>'")


_default_keyfile_pfx_map = _parse_keyfile_pfx_map()


class Connection(SnowflakeConnection):
    "A Connection class that overrides the cursor() method to return a custom Cursor class"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any, **kwargs: Any):
        return super().__exit__(*args, **kwargs)

    def cursor(self, cursor_class: type[SnowflakeCursor] = Cursor) -> Cursor:
        return cast(Cursor, super().cursor(cursor_class))


def connection_names() -> list[str]:
    """returns names of available connections
    Returns:
        list of connection names
    """
    return list(cast(dict[str, dict[str, Any]], CONFIG_MANAGER["connections"]).keys())


def conn_opts(
    connection_name: str | None = None,
    keyfile_pfx_map: tuple[Path, Path] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """returns connection options with overrides applied, if suplied

    Args:
        name: A connection name to be looked up from the config_file; value can be None
        keyfile_pfx_map: if specified must be a a pair of Path values specified as <from-path>:<to-path>,
           which will be used to change private_key_file path value if it starts with <from-pahd> prefix
        **overrides: A valid Snowflake python connector parameter; when not-None, will override value read from config_file

    Returns:
        dictionary containing option name and it's value

    Raises:
        *: any exceptions raised by snowflake.connector are passed through
    """
    if keyfile_pfx_map is None:
        keyfile_pfx_map = _default_keyfile_pfx_map

    def fix_keyfile_path(path: str) -> str:
        if keyfile_pfx_map is not None and (p := Path(path)).is_relative_to(keyfile_pfx_map[0]):
            return str(keyfile_pfx_map[1] / p.relative_to(keyfile_pfx_map[0]))
        return path

    connections = cast(dict[str, dict[str, Any]], CONFIG_MANAGER["connections"])
    if connection_name is None:
        connection_name = cast(str, CONFIG_MANAGER["default_connection_name"])

    if connection_name not in connections:
        raise Error(f"Invalid connection name '{connection_name}', select from [{', '.join(connections.keys())}]")

    opts = {**connections[connection_name], **{k: v for k, v in overrides.items() if v is not None}}
    if "private_key_file" in opts:
        opts["private_key_file"] = fix_keyfile_path(cast(str, opts["private_key_file"]))

    return opts


def getconn(connection_name: str | None = None, **overrides: Any) -> Connection:
    """connect to Snowflake database using named configuration

    Args
        name: A connection name to be looked up from the config_file, optional defaults to None for default connection
        **overrides: Any parameter that is valid for conn_opts() method; see conn_opts() documentation

    Returns:
        Connection object returned by Snowflake python connector
    """
    return Connection(**conn_opts(connection_name, **overrides))  # type: ignore
