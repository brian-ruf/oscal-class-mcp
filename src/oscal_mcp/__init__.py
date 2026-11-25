"""OSCAL MCP — an MCP server wrapping the ``oscal`` Python library.

The server exposes two complementary capability sets:

1. **OSCAL content operations** — loading, validating, converting, querying and
   inspecting OSCAL documents. *Every* OSCAL interaction is delegated to the
   ``oscal`` library; this package never parses or mutates OSCAL content itself.
2. **Library coding help** — MCP resources and a search tool that surface the
   ``oscal`` library's own API reference, OSCAL model structure, and curated usage
   recipes, so an agentic AI can write correct Python against the library.
"""

import logging
from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("oscal-mcp")
except PackageNotFoundError:  # pragma: no cover - running from an uninstalled tree
    __version__ = "0.0.0+unknown"

# Library convention (mirrors ``oscal``): emit records but install no handler, so we
# stay silent unless the host application configures logging.
logging.getLogger("oscal_mcp").addHandler(logging.NullHandler())

__all__ = ["__version__"]
