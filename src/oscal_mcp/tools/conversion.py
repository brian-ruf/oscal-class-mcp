"""Format conversion and serialization tools (XML / JSON / YAML)."""

from __future__ import annotations

from fastmcp.exceptions import ToolError

from ..state import DocumentStore, UnknownHandleError

_FORMATS = ("xml", "json", "yaml")


def _check_format(fmt: str) -> None:
    if fmt not in _FORMATS:
        raise ToolError(f"Unknown format {fmt!r}. Supported: {', '.join(_FORMATS)}.")


def register(mcp, store: DocumentStore) -> None:
    @mcp.tool
    def convert_document(handle: str, format: str, pretty: bool = True) -> dict:
        """Serialize an open document to XML, JSON, or YAML and return it as a string.

        The library emits keys/elements in canonical NIST metaschema order. ``format``
        must be one of ``xml``, ``json``, ``yaml``. Returns ``{handle, format,
        content}`` where ``content`` is the serialized document.
        """
        _check_format(format)
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc
        try:
            content = doc.dumps(format=format, pretty_print=pretty)
        except Exception as exc:
            raise ToolError(f"Conversion to {format} failed for {handle!r}: {exc}") from exc
        if not content:
            raise ToolError(f"Conversion to {format} produced no output for {handle!r}.")
        return {"handle": handle, "format": format, "content": content}

    @mcp.tool
    def save_document(
        handle: str,
        path: str = "",
        format: str = "",
        pretty: bool = True,
    ) -> dict:
        """Write an open document to disk.

        With no ``path``/``format``, saves back to the original source location and
        format. Otherwise ``path`` is the target file and ``format`` (one of ``xml``,
        ``json``, ``yaml``) the output format. Returns ``{handle, saved, path,
        format}``.
        """
        if format:
            _check_format(format)
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc
        try:
            ok = doc.dump(path, format=format, pretty_print=pretty) if (path or format) else doc.dump()
        except Exception as exc:
            raise ToolError(f"Save failed for {handle!r}: {exc}") from exc
        if not ok:
            raise ToolError(
                f"Save failed for {handle!r} (the library reported no success; "
                f"the document may be remote, read-only, or the path unwritable)."
            )
        return {"handle": handle, "saved": True, "path": path or doc.href, "format": format or doc.original_format}
