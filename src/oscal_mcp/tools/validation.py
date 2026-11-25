"""Validation tools — delegate to the library's tiered validation pipeline."""

from __future__ import annotations

from fastmcp.exceptions import ToolError

from ..serialize import validation_report
from ..state import DocumentStore, UnknownHandleError


def register(mcp, store: DocumentStore) -> None:
    @mcp.tool
    def validate_document(handle: str, full: bool = False) -> dict:
        """Validate an open document against the NIST OSCAL metaschema.

        Standard (``full=False``) runs the L2 pipeline: well-formedness, structure,
        data-types, natively-evaluable allowed-values, cardinality and choice. Set
        ``full=True`` to additionally run L3 (``validate_full``): ancestor/cross-path
        scoped constraints evaluated against XML.

        Returns per-phase ``validation_status``, the overall verdicts
        (``is_minimally_valid`` / ``is_valid`` / ``is_fully_compliant``), and the
        library's normalized ``errors`` (``error-type``, ``location``, ``identifier``,
        ``field``, ``value`` + detail).
        """
        try:
            doc = store.get(handle)
        except UnknownHandleError as exc:
            raise ToolError(str(exc)) from exc

        try:
            doc.validate()
            if full:
                doc.validate_full()
        except Exception as exc:
            raise ToolError(f"Validation failed for {handle!r}: {exc}") from exc

        return validation_report(doc, handle, full=full)
