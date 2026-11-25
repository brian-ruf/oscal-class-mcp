"""OSCAL support tools: enumerate models/versions, describe model structure, update.

These wrap the library's ``OSCALSupport`` singleton (configured once at startup via
:func:`oscal_mcp.state.configure_support_db`).
"""

from __future__ import annotations

from typing import Optional

from fastmcp.exceptions import ToolError

from ..serialize import _safe
from ..state import DocumentStore

_FORMATS = ("xml", "json", "yaml")


def _support():
    from oscal import oscal_support

    return oscal_support.get_support()


def register(mcp, store: DocumentStore) -> None:
    @mcp.tool
    def list_oscal_models(version: str = "all") -> dict:
        """List the OSCAL models known to the support database.

        With ``version="all"`` (default) returns every model across all versions;
        pass a version tag (e.g. ``v1.1.3``) to list only models defined for it.
        """
        try:
            models = _support().list_models(version)
        except Exception as exc:
            raise ToolError(f"Failed to list models: {exc}") from exc
        return {"version": version, "models": sorted(models)}

    @mcp.tool
    def list_oscal_versions(model: Optional[str] = None) -> dict:
        """List the OSCAL versions available in the support database.

        If ``model`` is given, only versions that define that model are returned.
        Also reports the latest known version.
        """
        sup = _support()
        try:
            all_versions = sorted((sup.versions or {}).keys())
            if model:
                versions = [v for v in all_versions if _safe(lambda v=v: sup.is_valid_model(model, v), False)]
            else:
                versions = all_versions
        except Exception as exc:
            raise ToolError(f"Failed to list versions: {exc}") from exc
        return {
            "model": model,
            "latest": _safe(lambda: sup.get_latest_version()),
            "count": len(versions),
            "versions": versions,
        }

    @mcp.tool
    def describe_model_structure(
        model: str,
        version: str = "",
        format: str = "json",
        reference_uuid: str = "",
    ) -> dict:
        """Describe an OSCAL model's metaschema structure.

        Returns an HTML outline of the model's structure in the requested ``format``
        syntax (``xml`` / ``json`` / ``yaml``), annotated with data types and
        cardinality; each node carries a stable reference id. Supply ``reference_uuid``
        (a node id from a prior outline) to get the one-node detail view instead.
        ``version`` defaults to the latest known version.
        """
        if format not in _FORMATS:
            raise ToolError(f"Unknown format {format!r}. Supported: {', '.join(_FORMATS)}.")
        sup = _support()
        version = version or _safe(lambda: sup.get_latest_version()) or "all"
        try:
            if reference_uuid:
                html = sup.view_detail(version, model, format, reference_uuid)
                view = "detail"
            else:
                html = sup.view_outline(version, model, format)
                view = "outline"
        except Exception as exc:
            raise ToolError(f"Failed to describe {model!r}: {exc}") from exc
        return {
            "model": model,
            "version": version,
            "format": format,
            "view": view,
            "reference_uuid": reference_uuid or None,
            "html": html,
        }

    @mcp.tool
    def update_oscal_support(version: str = "") -> dict:
        """Update the support database with OSCAL versions published by NIST.

        REQUIRES AN ACTIVE INTERNET CONNECTION and is a no-op/failure in air-gapped
        deployments. With no ``version``, checks for and fetches any newly published
        versions (``mode="new"``). Pass a specific tag (e.g. ``v1.2.3``) to clear and
        re-fetch just that version. Returns success plus the library's update stats.
        """
        sup = _support()
        mode = version or "new"
        try:
            ok = sup.update(mode=mode)
        except Exception as exc:
            raise ToolError(f"Support update failed (an Internet connection is required): {exc}") from exc
        return {
            "requested": mode,
            "ok": bool(ok),
            "stats": _safe(lambda: dict(sup._update_stats), None),
        }
