"""MCP resources and the library-API search tool.

These surface the ``oscal`` library's own API reference (via runtime introspection),
OSCAL model structure, curated usage recipes, and bundled operating-concept guides — the
"help an LLM write Python against the library" half of the server — plus ``search_library_api``
and ``search_knowledge``.
"""

from . import about, api_reference, concepts, knowledge_search, metaschema, recipes, standard

__all__ = [
    "about",
    "api_reference",
    "concepts",
    "knowledge_search",
    "metaschema",
    "recipes",
    "standard",
]


def register_all(mcp, store) -> None:
    """Register every resource group and the search tools."""
    about.register(mcp, store)
    api_reference.register(mcp, store)
    concepts.register(mcp, store)
    knowledge_search.register(mcp, store)
    metaschema.register(mcp, store)
    recipes.register(mcp, store)
    standard.register(mcp, store)
