"""Tool: ranked full-text search across the bundled knowledge collections.

``search_knowledge`` searches the offline documentation the server teaches from — the
``oscal`` library's operating-concept guides (``oscal-lib://concepts``) and, once bundled,
the NIST OSCAL standard (``oscal-std://concepts``). Use it to find *where* a concept is
explained, then read the full guide via the returned ``uri``.
"""

from __future__ import annotations

from typing import List

from fastmcp.exceptions import ToolError

from ..knowledge import iter_documents
from ..state import DocumentStore

# scope -> (collection, resource-uri prefix)
_SCOPES = {
    "lib": [("oscal_lib", "oscal-lib://concepts")],
    "std": [("oscal_std", "oscal-std://concepts")],
}
_SCOPES["all"] = _SCOPES["lib"] + _SCOPES["std"]


def _score_and_snippet(title: str, body: str, terms: List[str]):
    """Rank a document against query terms and extract the most relevant snippet."""
    title_l = title.lower()
    score = 0
    for t in terms:
        if t in title_l:
            score += 25
    # Best-matching line for scoring body hits and building a snippet.
    best_line, best_hits = "", 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        ll = stripped.lower()
        hits = sum(ll.count(t) for t in terms)
        if hits:
            score += hits * (6 if stripped.startswith("#") else 2)
            if hits > best_hits:
                best_hits, best_line = hits, stripped.lstrip("# ")
    snippet = best_line[:240] if best_line else ""
    return score, snippet


def register(mcp, store: DocumentStore) -> None:
    @mcp.tool
    def search_knowledge(query: str, scope: str = "all", limit: int = 10) -> dict:
        """Search bundled OSCAL documentation for guides matching a query.

        ``scope`` is ``lib`` (oscal library concepts), ``std`` (NIST OSCAL standard), or
        ``all`` (default). Ranks by title and heading/body matches and returns the top
        ``limit`` hits, each with a snippet and the ``uri`` to read the full guide. For
        library *symbol/signature* lookups use ``search_library_api`` instead.
        """
        if not query or not query.strip():
            raise ToolError("query must be a non-empty string.")
        if scope not in _SCOPES:
            raise ToolError(f"scope must be one of {', '.join(sorted(_SCOPES))}; got {scope!r}.")

        terms = [t for t in query.lower().split() if t]
        scored = []
        for collection, uri_prefix in _SCOPES[scope]:
            for rec, body in iter_documents(collection):
                title = rec.get("title", rec["name"])
                score, snippet = _score_and_snippet(title, body, terms)
                if score > 0:
                    scored.append(
                        {
                            "collection": collection,
                            "name": rec["name"],
                            "title": title,
                            "uri": f"{uri_prefix}/{rec['name']}",
                            "snippet": snippet,
                            "score": score,
                        }
                    )
        scored.sort(key=lambda r: r["score"], reverse=True)
        results = scored[: max(1, limit)]
        return {"query": query, "scope": scope, "count": len(results), "results": results}
