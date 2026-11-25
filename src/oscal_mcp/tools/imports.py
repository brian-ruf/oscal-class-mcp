"""Import-resolution tools: inspect, resolve, and retry a document's imports."""

from __future__ import annotations

from fastmcp.exceptions import ToolError

from ..serialize import _enum_name, _safe
from ..state import DocumentStore, UnknownHandleError


def _import_view(entry: dict) -> dict:
    """Render one ``import_list`` entry JSON-safe (dropping the live OSCAL object)."""
    obj = entry.get("object")
    failure = entry.get("failure")
    failure_view = None
    if failure is not None:
        failure_view = {
            "code": _enum_name(_safe(lambda: failure.code)),
            "message": _safe(lambda: failure.message),
        }
    return {
        "href_original": entry.get("href_original"),
        "href_valid": entry.get("href_valid"),
        "status": _enum_name(entry.get("status")),
        "is_valid": entry.get("is_valid"),
        "is_local": entry.get("is_local"),
        "is_remote": entry.get("is_remote"),
        "is_cached": entry.get("is_cached"),
        "resolved": obj is not None,
        "object_model": _safe(lambda: obj.model) if obj is not None else None,
        "failure": failure_view,
    }


def _imports_report(doc, handle: str) -> dict:
    entries = _safe(lambda: list(doc.import_list), []) or []
    views = [_import_view(e) for e in entries]
    return {
        "handle": handle,
        "model": _safe(lambda: doc.model),
        "imports_resolved": _safe(lambda: doc.imports_resolved),
        "count": len(views),
        "failed_count": sum(1 for v in views if v["failure"] is not None),
        "imports": views,
    }


def register(mcp, store: DocumentStore) -> None:
    @mcp.tool
    def inspect_imports(handle: str) -> dict:
        """List a document's imports and their resolution status.

        Returns one entry per import statement (original/resolved href, status, local/
        remote/cached flags, whether it resolved, the imported model, and structured
        failure detail when it did not).
        """
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc
        return _imports_report(doc, handle)

    @mcp.tool
    def resolve_imports(handle: str, base_path: str = "") -> dict:
        """Re-run import discovery and loading, then report the result.

        Imports resolve automatically once content is minimally valid; call this to
        force a fresh pass (e.g. after a retry or an environment change). ``base_path``
        is an optional base for resolving relative hrefs.
        """
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc
        try:
            doc.resolve_imports(base_path)
        except Exception as exc:
            raise ToolError(f"resolve_imports failed for {handle!r}: {exc}") from exc
        return _imports_report(doc, handle)

    @mcp.tool
    def retry_import(handle: str, failed_href: str, replacement_href: str) -> dict:
        """Retry a single failed import using an alternate source.

        Point ``failed_href`` (as it appears in the document) at ``replacement_href``
        (e.g. a local fallback copy), then re-reports import status.
        """
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc
        try:
            doc.retry_import(failed_href=failed_href, replacement_href=replacement_href)
        except Exception as exc:
            raise ToolError(f"retry_import failed for {handle!r}: {exc}") from exc
        return _imports_report(doc, handle)
