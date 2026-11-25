"""Resource: curated, hand-authored recipes for using the ``oscal`` library in Python.

Recipes are markdown files under ``oscal_mcp/recipes/``. Each file's first ``#``
heading is its title.

* ``oscal-lib://recipes`` — index of available recipes (name + title).
* ``oscal-lib://recipes/{name}`` — the full markdown of one recipe.
"""

from __future__ import annotations

from pathlib import Path

from fastmcp.exceptions import ToolError

from ..state import DocumentStore

_RECIPES_DIR = Path(__file__).resolve().parent.parent / "recipes"


def _recipe_files() -> dict:
    """Return ``{name: path}`` for every recipe markdown file (name = stem)."""
    if not _RECIPES_DIR.is_dir():
        return {}
    return {p.stem: p for p in sorted(_RECIPES_DIR.glob("*.md"))}


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def register(mcp, store: DocumentStore) -> None:
    @mcp.resource("oscal-lib://recipes")
    def recipes_index() -> dict:
        """Index of curated recipes for coding against the ``oscal`` library."""
        files = _recipe_files()
        items = []
        for name, path in files.items():
            text = path.read_text(encoding="utf-8")
            items.append({"name": name, "title": _title(text, name), "uri": f"oscal-lib://recipes/{name}"})
        return {"count": len(items), "recipes": items}

    @mcp.resource("oscal-lib://recipes/{name}")
    def recipe(name: str) -> str:
        """Return the full markdown of a single recipe by name."""
        files = _recipe_files()
        path = files.get(name)
        if path is None:
            raise ToolError(f"No recipe {name!r}. Available: {', '.join(files) or '(none)'}.")
        return path.read_text(encoding="utf-8")
