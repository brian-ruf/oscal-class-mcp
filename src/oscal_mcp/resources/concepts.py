"""Resource: the ``oscal`` library's operating-concept guides (bundled, offline).

These are the library's own narrative docs — how it approaches validation, import
resolution, profile processing, querying, conversion, the support module, etc. — synced
from a specific ``oscal-class`` release by ``scripts/sync_knowledge.py`` (see
``oscal-lib://about`` for the source release). They teach an agent the library's *concepts*
and handling patterns, complementing the symbol-level ``oscal-lib://api`` reference.

* ``oscal-lib://concepts`` — index of available concept guides.
* ``oscal-lib://concepts/{name}`` — full markdown of one guide.
"""

from __future__ import annotations

from fastmcp.exceptions import ToolError

from ..knowledge import list_documents, read_document
from ..state import DocumentStore

_COLLECTION = "oscal_lib"


def register(mcp, store: DocumentStore) -> None:
    @mcp.resource("oscal-lib://concepts")
    def concepts_index() -> dict:
        """Index of the ``oscal`` library's operating-concept guides (bundled offline)."""
        docs = list_documents(_COLLECTION)
        items = [
            {
                "name": d["name"],
                "title": d.get("title", d["name"]),
                "words": d.get("words"),
                "uri": f"oscal-lib://concepts/{d['name']}",
            }
            for d in docs
        ]
        return {"count": len(items), "concepts": items}

    @mcp.resource("oscal-lib://concepts/{name}")
    def concept(name: str) -> str:
        """Return the full markdown of one library concept guide by name."""
        body = read_document(_COLLECTION, name)
        if body is None:
            available = ", ".join(d["name"] for d in list_documents(_COLLECTION)) or "(none bundled)"
            raise ToolError(f"No concept guide {name!r}. Available: {available}.")
        return body
