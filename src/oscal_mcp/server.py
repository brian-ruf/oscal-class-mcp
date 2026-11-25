"""OSCAL MCP server assembly and entry point.

Builds a FastMCP application, configures the OSCAL support database **before** any
OSCAL object is created, instantiates the shared document cache, and registers every
tool and resource group. Run as ``python -m oscal_mcp`` or via the installed
``oscal-mcp`` console script.
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from fastmcp import FastMCP

from . import __version__, resources, tools
from .knowledge import parity_status
from .state import DocumentStore, configure_support_db

logger = logging.getLogger("oscal_mcp")

INSTRUCTIONS = """\
This server wraps the `oscal` Python library. Use its tools to open, validate, convert,
query and inspect OSCAL documents (catalog, profile, mapping-collection,
component-definition, system-security-plan, assessment-plan, assessment-results,
plan-of-action-and-milestones). Every document tool takes a `handle` returned by
`open_document` / `load_content` / `new_document`.

To write Python that uses the library directly, read the `oscal-lib://` resources:
`oscal-lib://api` (symbol/signature reference) + `search_library_api` for methods, and
`oscal-lib://concepts` (operating-concept guides: validation, imports, profile processing,
…) + `search_knowledge` for how the library behaves. `oscal-lib://about` reports version
parity between the installed library and the bundled docs.

To learn the OSCAL standard itself (independent of the library), read `oscal-std://concepts`
(curated NIST concept/model/tutorial pages) and ALWAYS also read `oscal-std://notes` for
authored expert caveats and known gaps the NIST docs omit (e.g. profile-spec draft status).
`search_knowledge` with scope `std` or `all` searches this content too.
"""


def build_app(support_db: Optional[str] = None) -> FastMCP:
    """Construct the FastMCP app with support DB configured and all features registered."""
    # MUST happen before any OSCAL object exists so the library targets our DB path.
    configure_support_db(support_db)

    parity = parity_status()
    if parity["status"] == "mismatch":
        logger.warning(
            "Bundled OSCAL concept docs are from oscal %s but %s is installed; "
            "run scripts/sync_knowledge.py to realign.",
            parity["bundled_docs_release"],
            parity["installed_oscal"],
        )
    else:
        logger.info(
            "oscal-mcp %s | installed oscal %s | docs parity: %s",
            __version__,
            parity["installed_oscal"],
            parity["status"],
        )

    mcp = FastMCP(name="oscal-mcp", version=__version__, instructions=INSTRUCTIONS)
    store = DocumentStore()
    tools.register_all(mcp, store)
    resources.register_all(mcp, store)
    return mcp


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="oscal-mcp", description="OSCAL MCP server wrapping the oscal library.")
    parser.add_argument(
        "--support-db",
        default=None,
        help="Path to the OSCAL support database (overrides OSCAL_MCP_SUPPORT_DB and the default).",
    )
    parser.add_argument(
        "--transport", choices=["stdio", "http", "sse"], default="stdio", help="Transport to serve on (default: stdio)."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for http/sse transport.")
    parser.add_argument("--port", type=int, default=8000, help="Port for http/sse transport.")
    parser.add_argument(
        "--log-level", default="WARNING", help="Logging level for the oscal_mcp logger (default: WARNING)."
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> None:
    """Console entry point: parse args, build the app, and serve."""
    args = _parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.WARNING))

    app = build_app(support_db=args.support_db)

    if args.transport == "stdio":
        app.run()
    else:
        app.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
