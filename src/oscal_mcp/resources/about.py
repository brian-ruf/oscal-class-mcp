"""Resource: server identity and library/knowledge version parity.

``oscal-lib://about`` reports the server version, the installed ``oscal`` library version,
and the source release each bundled knowledge collection was synced from — so an agent (or
operator) can see at a glance whether the offline documentation is in parity with the
library actually in use.
"""

from __future__ import annotations

from .. import __version__
from ..knowledge import COLLECTIONS, installed_oscal_version, load_manifest, parity_status
from ..state import DocumentStore


def register(mcp, store: DocumentStore) -> None:
    @mcp.resource("oscal-lib://about")
    def about() -> dict:
        """Server version, installed ``oscal`` version, and bundled-knowledge parity.

        Use this to confirm the offline concept/standard documentation matches the
        ``oscal`` library version in use. ``parity.status`` is ``ok`` / ``mismatch`` /
        ``not-bundled``.
        """
        collections = {}
        for name, label in COLLECTIONS.items():
            man = load_manifest(name) or {}
            entry = {
                "label": label,
                "bundled": bool(man),
                "source": man.get("source_repo"),
                "release": man.get("source_release") or man.get("source_tag"),
                "synced": man.get("synced"),
                "document_count": len(man.get("documents", []) or []),
            }
            if man.get("source_commit_date"):
                entry["source_commit_date"] = man["source_commit_date"]
            if man.get("license"):
                entry["license"] = man["license"]
            if man.get("notes"):
                entry["notes_version"] = (man["notes"] or {}).get("notes_version")
            collections[name] = entry
        return {
            "server": "oscal-mcp",
            "server_version": __version__,
            "installed_oscal": installed_oscal_version(),
            "parity": parity_status(),
            "knowledge_collections": collections,
        }
