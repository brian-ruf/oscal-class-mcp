"""MCP tool groups. Each module exposes ``register(mcp, store)``."""

from . import content, validation, conversion, query, imports, support

__all__ = ["content", "validation", "conversion", "query", "imports", "support"]


def register_all(mcp, store) -> None:
    """Register every tool group on the given FastMCP app."""
    content.register(mcp, store)
    validation.register(mcp, store)
    conversion.register(mcp, store)
    query.register(mcp, store)
    imports.register(mcp, store)
    support.register(mcp, store)
