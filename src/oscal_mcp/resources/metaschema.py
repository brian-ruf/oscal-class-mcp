"""Resource: OSCAL model structure, rendered from the metaschema index.

``oscal-lib://metaschema/{model}`` returns the library's HTML outline of a model's
structure (latest known version, JSON-key syntax), annotated with data types and
cardinality. This helps an LLM understand the shape of OSCAL content the library
produces and consumes. For deeper, parameterized structure queries (specific version,
XML syntax, or single-node detail) use the ``describe_model_structure`` tool.
"""

from __future__ import annotations

from ..state import DocumentStore


def register(mcp, store: DocumentStore) -> None:
    @mcp.resource("oscal-lib://metaschema/{model}")
    def metaschema_outline(model: str) -> dict:
        """HTML outline of an OSCAL model's metaschema structure (latest version, JSON).

        ``model`` is an OSCAL model name such as ``catalog`` or ``profile``.
        """
        from oscal import oscal_support

        sup = oscal_support.get_support()
        version = sup.get_latest_version() or "all"
        html = sup.view_outline(version, model, "json")
        return {"model": model, "version": version, "format": "json", "html": html}
