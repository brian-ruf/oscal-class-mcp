"""Bundled knowledge collections and version-parity helpers.

This package holds offline snapshots of documentation the server teaches an agent from:

* ``oscal_lib/`` — the ``oscal`` Python library's operating-concept guides (validation,
  imports, profile processing, …), synced from a specific ``oscal-class`` release.
* ``oscal_std/`` — a curated snapshot of the NIST OSCAL standard (pages.nist.gov/OSCAL).

Each collection is described by a ``_manifest.json`` written by
``scripts/sync_knowledge.py``. The runtime **never fetches these over the network** — they
are bundled so the server works offline while staying in parity with a known source
release. Collections may be absent (e.g. before the first sync); every accessor degrades
gracefully to ``None``/empty.
"""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent

# Collection directory -> human-readable label.
COLLECTIONS = {
    "oscal_lib": "oscal Python library concepts",
    "oscal_std": "NIST OSCAL standard",
}


def collection_dir(name: str) -> Path:
    """Filesystem directory backing a knowledge collection (may not exist yet)."""
    return KNOWLEDGE_DIR / name


def load_manifest(name: str) -> Optional[dict]:
    """Return the parsed ``_manifest.json`` for a collection, or ``None`` if not bundled."""
    path = collection_dir(name) / "_manifest.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def installed_oscal_version() -> Optional[str]:
    """Version of the ``oscal`` library currently importable, or ``None``."""
    try:
        return _pkg_version("oscal")
    except PackageNotFoundError:  # pragma: no cover - uninstalled tree
        try:
            import oscal

            return getattr(oscal, "__version__", None)
        except Exception:
            return None


def bundled_oscal_release() -> Optional[str]:
    """Source release/tag the bundled library concept docs were synced from, or ``None``."""
    man = load_manifest("oscal_lib")
    if not man:
        return None
    return man.get("source_release") or man.get("source_tag")


def parity_status() -> dict:
    """Compare the installed ``oscal`` version against the bundled-docs source release.

    ``status`` is ``"ok"`` when they match, ``"mismatch"`` when bundled docs trail/lead the
    installed library, or ``"not-bundled"`` when no library-concept docs are bundled yet.
    """
    installed = installed_oscal_version()
    bundled = bundled_oscal_release()
    if bundled is None:
        status = "not-bundled"
    else:
        status = "ok" if installed and bundled.lstrip("v") == installed else "mismatch"
    return {
        "installed_oscal": installed,
        "bundled_docs_release": bundled,
        "status": status,
    }


# -----------------------------------------------------------------------------
# Document access (manifest-driven; shared by the concepts/standard resources
# and the search_knowledge tool)
# -----------------------------------------------------------------------------
def list_documents(collection: str) -> list:
    """Return the manifest ``documents`` list for a collection (``[]`` if not bundled)."""
    man = load_manifest(collection)
    if not man:
        return []
    return list(man.get("documents", []) or [])


def _doc_record(collection: str, name: str) -> Optional[dict]:
    for rec in list_documents(collection):
        if rec.get("name") == name:
            return rec
    return None


def read_document(collection: str, name: str) -> Optional[str]:
    """Return the markdown body of one bundled document, or ``None`` if absent."""
    rec = _doc_record(collection, name)
    if rec is None:
        return None
    path = collection_dir(collection) / rec.get("file", f"{name}.md")
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def iter_documents(collection: str):
    """Yield ``(record, body)`` for every readable document in a collection."""
    for rec in list_documents(collection):
        path = collection_dir(collection) / rec.get("file", "")
        if path.is_file():
            yield rec, path.read_text(encoding="utf-8")
