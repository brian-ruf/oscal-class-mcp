"""Path-based query tools over the library's internal JSON representation."""

from __future__ import annotations

from fastmcp.exceptions import ToolError

from ..state import DocumentStore, UnknownHandleError


def register(mcp, store: DocumentStore) -> None:
    @mcp.tool
    def query_document(
        handle: str,
        path: str,
        json_syntax: bool = False,
        first_only: bool = False,
    ) -> dict:
        """Query an open document with an XPath-inspired path expression.

        Two step-name conventions are available:

        * ``json_syntax=False`` (default) — use OSCAL **XML element names**
          (``control``, ``prop``, ``part``), e.g. ``//control[@id="ac-2"]`` or
          ``/*/metadata/title``. Requires a metaschema index for the model/version.
        * ``json_syntax=True`` — use **JSON key names** (``controls``, ``props``,
          ``parts``), e.g. ``//controls[id="ac-2"]``. No index required.

        Set ``first_only=True`` to return just the first match (or ``null``). Returns
        ``{handle, path, json_syntax, count, matches}``. Query results are detached
        copies — mutating them does not change the document.
        """
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc

        try:
            if json_syntax:
                result = doc.json_query_one(path) if first_only else doc.json_query(path)
            else:
                result = doc.query_one(path) if first_only else doc.query(path)
        except Exception as exc:
            raise ToolError(f"Query {path!r} failed for {handle!r}: {exc}") from exc

        if first_only:
            matches = [] if result is None else [result]
        else:
            matches = list(result or [])

        return {
            "handle": handle,
            "path": path,
            "json_syntax": json_syntax,
            "count": len(matches),
            "matches": matches[0] if first_only and matches else (None if first_only else matches),
        }
