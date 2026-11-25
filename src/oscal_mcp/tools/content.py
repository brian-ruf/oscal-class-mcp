"""Content lifecycle tools: open, load, create, list, inspect and close documents.

All OSCAL I/O is delegated to the ``oscal`` library via the shared
:class:`~oscal_mcp.state.DocumentStore` (which wraps ``oscal.Workspace``). Tools
return a JSON-safe document summary (see :mod:`oscal_mcp.serialize`).
"""

from __future__ import annotations

from typing import Optional

from fastmcp.exceptions import ToolError

from ..serialize import summarize
from ..state import DocumentStore, UnknownHandleError


def register(mcp, store: DocumentStore) -> None:
    @mcp.tool
    def open_document(source: str) -> dict:
        """Open an OSCAL document from a local file path or a URI.

        Loads XML, JSON, or YAML from a local path (e.g. ``./catalog.xml``) or acquires
        it from a URI (``https://…``, ``file://…``). The document is cached and
        validated/import-resolved by the library on load. Re-opening the same source
        returns the existing handle.

        Returns a summary including the ``handle`` used by all other document tools,
        the detected model, metadata, content state, and validation status.
        """
        try:
            handle, doc = store.open_path(source)
        except Exception as exc:
            raise ToolError(f"Failed to open {source!r}: {exc}") from exc
        return summarize(doc, handle)

    @mcp.tool
    def load_content(content: str, href: Optional[str] = None) -> dict:
        """Load in-memory OSCAL content (a JSON, YAML, or XML string).

        Use when the OSCAL content is already available as text rather than a file.
        ``href`` is an optional label identifying the content's origin. Returns a
        document summary including the ``handle``.
        """
        try:
            handle, doc = store.load_content(content, href=href)
        except Exception as exc:
            raise ToolError(f"Failed to load content: {exc}") from exc
        return summarize(doc, handle)

    @mcp.tool
    def new_document(
        model: str,
        title: str,
        version: str = "",
        published: str = "",
    ) -> dict:
        """Create a new OSCAL document from the library's built-in template.

        ``model`` must be one of: ``catalog``, ``profile``, ``mapping-collection``,
        ``component-definition``, ``system-security-plan``, ``assessment-plan``,
        ``assessment-results``, ``plan-of-action-and-milestones``. ``published`` is an
        optional ISO-8601 timestamp (e.g. ``2026-01-01T00:00:00Z``). Returns a summary
        including the ``handle``.
        """
        kwargs: dict = {}
        if version:
            kwargs["version"] = version
        if published:
            kwargs["published"] = published
        try:
            handle, doc = store.new_document(model, title, **kwargs)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(f"Failed to create {model!r} document: {exc}") from exc

        # The library only ships creatable templates for some models today (currently
        # catalog and profile); for the rest, .new() yields a non-well-formed stub.
        # Detect this dynamically rather than hard-coding the list, so the tool begins
        # to work for a model the moment the library gains its template.
        if not doc.is_well_formed:
            store.close(handle)
            raise ToolError(
                f"The oscal library does not currently provide a creatable template for "
                f"model {model!r} (only 'catalog' and 'profile' support new_document today). "
                f"Load existing {model!r} content with open_document or load_content instead."
            )
        return summarize(doc, handle)

    @mcp.tool
    def list_documents() -> dict:
        """List all currently open documents with their summaries.

        Returns ``{count, documents}`` where ``documents`` holds one summary per open
        document (each includes its ``handle``).
        """
        docs = [summarize(doc, handle) for handle, doc in store.items()]
        return {"count": len(docs), "documents": docs}

    @mcp.tool
    def get_document_summary(handle: str) -> dict:
        """Return the full summary for one open document.

        Includes model, live metadata, content state, per-phase ``validation_status``,
        version-support resolution, and origin/mutability flags.
        """
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc
        return summarize(doc, handle)

    @mcp.tool
    def close_document(handle: str) -> dict:
        """Close a document, evicting it from the cache and releasing its handle."""
        closed = store.close(handle)
        if not closed:
            raise ToolError(f"No open document with handle {handle!r}.")
        return {"handle": handle, "closed": True}
