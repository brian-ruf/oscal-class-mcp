"""Resources: the NIST OSCAL standard (curated snapshot) + authored expert notes.

A curated, offline snapshot of the NIST OSCAL "Learn" pages (concepts, layers, per-model
pages, tutorials) from ``usnistgov/OSCAL-Pages``, bundled by ``scripts/sync_knowledge.py``
(public domain / CC0; see ``NIST-ATTRIBUTION.md`` and ``oscal-lib://about``). This teaches
an agent the *standard itself*, independent of the ``oscal`` library.

* ``oscal-std://concepts`` — index of standard pages (NIST) plus the authored notes.
* ``oscal-std://concepts/{name}`` — full markdown of one page.
* ``oscal-std://notes`` — the authored *expert enhancements* to the standard
  (``additional_notes.md``): draft-status caveats and known gaps NIST does not state
  explicitly. Authored content, not NIST — maintained by hand and versioned separately.
"""

from __future__ import annotations

from fastmcp.exceptions import ToolError

from ..knowledge import list_documents, load_manifest, read_document
from ..state import DocumentStore

_COLLECTION = "oscal_std"
_NOTES_NAME = "additional-notes"


def register(mcp, store: DocumentStore) -> None:
    @mcp.resource("oscal-std://concepts")
    def standard_index() -> dict:
        """Index of the curated NIST OSCAL standard snapshot (+ authored expert notes)."""
        man = load_manifest(_COLLECTION) or {}
        items = [
            {
                "name": d["name"],
                "title": d.get("title", d["name"]),
                "words": d.get("words"),
                "authored": d.get("authored", False),
                "uri": f"oscal-std://concepts/{d['name']}",
            }
            for d in list_documents(_COLLECTION)
        ]
        return {
            "count": len(items),
            "source": man.get("source_repo"),
            "source_release": man.get("source_release"),
            "license": man.get("license"),
            "attribution": "oscal-std://concepts (see NIST-ATTRIBUTION.md); authored notes at oscal-std://notes",
            "concepts": items,
        }

    @mcp.resource("oscal-std://concepts/{name}")
    def standard_page(name: str) -> str:
        """Return the full markdown of one OSCAL-standard page (or the authored notes)."""
        body = read_document(_COLLECTION, name)
        if body is None:
            available = ", ".join(d["name"] for d in list_documents(_COLLECTION)) or "(none bundled)"
            raise ToolError(f"No OSCAL-standard page {name!r}. Available: {available}.")
        return body

    @mcp.resource("oscal-std://notes")
    def standard_notes() -> str:
        """Authored expert enhancements to the OSCAL standard (draft caveats & known gaps).

        Not NIST-published. Read alongside ``oscal-std://concepts`` for practical guidance
        the official docs omit (e.g. profile-spec draft status and child-group handling).
        """
        body = read_document(_COLLECTION, _NOTES_NAME)
        if body is None:
            raise ToolError("Authored notes (additional_notes.md) are not bundled.")
        return body
