"""Shape OSCAL objects into JSON-safe dicts for MCP tool responses.

This is the *only* place that reads fields off an OSCAL object, and it does so
exclusively through the library's public surface:

* scalar metadata (title, version, dates, uuid) is read with the library's
  ``json_query_one`` so it always reflects live content — the cached ``.title`` /
  ``.version`` attributes can lag after ``.new()``/mutation, whereas a query cannot;
* state, format and mutability are read from the library's documented properties.

The server never touches the internal document tree directly.
"""

from __future__ import annotations

from typing import Any, Optional


def _safe(fn, default=None):
    """Call ``fn`` and swallow any exception, returning ``default`` on failure."""
    try:
        return fn()
    except Exception:
        return default


def _enum_name(value):
    """Return ``value.name`` / ``value.value`` for enums, else the value unchanged."""
    if value is None:
        return None
    return getattr(value, "name", None) or getattr(value, "value", None) or value


def _metadata_field(doc, field: str):
    """Read ``/*/metadata/<field>`` via the library's JSON query, or ``None``."""
    return _safe(lambda: doc.json_query_one(f"/*/metadata/{field}"))


def summarize(doc, handle: Optional[str] = None) -> dict:
    """Return a JSON-safe summary of an OSCAL document.

    Covers model identity, live metadata scalars, format, the progressive content
    state, per-phase validation status, version-support resolution, and the
    origin/mutability flags documented in the library's ``CONTENT.md``.
    """
    summary: dict[str, Any] = {
        "handle": handle,
        "model": _safe(lambda: doc.model),
        "oscal_version": _metadata_field(doc, "oscal-version") or _safe(lambda: doc.oscal_version),
        "uuid": _safe(lambda: doc.json_query_one("/*/uuid")),
        "title": _metadata_field(doc, "title"),
        "version": _metadata_field(doc, "version"),
        "published": _metadata_field(doc, "published"),
        "last_modified": _metadata_field(doc, "last-modified"),
        "original_format": _safe(lambda: doc.original_format),
        "href": _safe(lambda: doc.href),
        "href_original": _safe(lambda: doc.href_original),
        # Progressive validation state + per-phase detail.
        "content_state": _enum_name(_safe(lambda: doc.content_state)),
        "validation_status": _safe(lambda: dict(doc.validation_status), {}),
        "is_well_formed": _safe(lambda: doc.is_well_formed),
        "is_minimally_valid": _safe(lambda: doc.is_minimally_valid),
        "is_valid": _safe(lambda: doc.is_valid),
        "is_fully_compliant": _safe(lambda: doc.is_fully_compliant),
        "imports_resolved": _safe(lambda: doc.imports_resolved),
        # Version-support resolution (separate qualifier from content_state).
        "version_support": _enum_name(_safe(lambda: doc.version_support)),
        "requested_oscal_version": _safe(lambda: doc.requested_oscal_version),
        "resolved_oscal_version": _safe(lambda: doc.resolved_oscal_version),
        # Origin / mutability.
        "is_local": _safe(lambda: doc.is_local),
        "is_remote": _safe(lambda: doc.is_remote),
        "is_read_only": _safe(lambda: doc.is_read_only),
        "is_editable": _safe(lambda: doc.is_editable),
        "is_unsaved": _safe(lambda: doc.is_unsaved),
    }
    return summary


def validation_report(doc, handle: Optional[str] = None, *, full: bool = False) -> dict:
    """Return a validation report: status, normalized errors, and overall verdicts.

    ``validation_errors`` is already normalized by the library (``error-type``,
    ``location``, ``identifier``, ``field``, ``value`` + detail); it is passed through
    unchanged. ``full`` indicates whether L3 (``validate_full``) was requested.
    """
    return {
        "handle": handle,
        "model": _safe(lambda: doc.model),
        "tier": "full" if full else "standard",
        "validation_status": _safe(lambda: dict(doc.validation_status), {}),
        "is_minimally_valid": _safe(lambda: doc.is_minimally_valid),
        "is_valid": _safe(lambda: doc.is_valid),
        "is_fully_compliant": _safe(lambda: doc.is_fully_compliant),
        "errors": _safe(lambda: list(doc.validation_errors), []),
    }
