"""Unit tests for the dev-time knowledge sync helpers (scripts/sync_knowledge.py)."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync_knowledge.py"
_spec = importlib.util.spec_from_file_location("sync_knowledge", _SCRIPT)
sync_knowledge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_knowledge)


def test_slugify():
    assert sync_knowledge.slugify("IMPORT_SELECTION_API.md") == "import-selection-api"
    assert sync_knowledge.slugify("VALIDATION.md") == "validation"


def test_strip_front_matter_with_title():
    text = "---\n# a jekyll comment\ntitle: Tiered Validation\n---\n\n# Tiered Validation\n\nbody"
    body, title = sync_knowledge.strip_front_matter(text)
    assert title == "Tiered Validation"
    assert body.startswith("# Tiered Validation")


def test_strip_front_matter_empty_block_falls_back_to_heading():
    text = "---\n---\n\n# Import Resolution\n\ntext"
    body, title = sync_knowledge.strip_front_matter(text)
    assert title == "Import Resolution"
    assert body.startswith("# Import Resolution")


def test_strip_front_matter_none():
    text = "# Patterns\n\ntext"
    body, title = sync_knowledge.strip_front_matter(text)
    assert title == "Patterns"
    assert body == text


def test_strip_front_matter_toml():
    text = '+++\ntitle = "Model Overview"\nweight = 10\n+++\n\nbody text'
    body, title = sync_knowledge.strip_front_matter(text)
    assert title == "Model Overview"
    assert body == "body text"


def test_clean_hugo_strips_shortcodes_and_comments():
    text = (
        "---\ntitle: Catalog\n---\n\n"
        "{{% usa-grid-row %}}\nReal **content** here.\n{{% /usa-grid-row %}}\n"
        "{{< figure src=x >}}\n<!-- a comment -->\n\n\n\nMore text.\n"
    )
    body, title = sync_knowledge.clean_hugo(text)
    assert title == "Catalog"
    assert "usa-grid" not in body and "{{" not in body and "<!--" not in body
    assert "Real **content** here." in body and "More text." in body
    assert "\n\n\n" not in body  # blank runs collapsed


def test_parse_notes_version():
    assert sync_knowledge.parse_notes_version("<!-- notes-version: 1.2.3 | x -->\n# t") == "1.2.3"
    assert sync_knowledge.parse_notes_version("no version here") is None


def test_rewrite_internal_links_only_bundled_targets():
    html_to_slug = {"validation": "validation", "imports": "imports"}
    body = (
        "See [Validation](VALIDATION.html) and [Imports](IMPORTS.html#tree) "
        "but not [API](api.html) or [ext](https://x/Y.html)."
    )
    out = sync_knowledge.rewrite_internal_links(body, "oscal-lib://concepts", html_to_slug)
    assert "(oscal-lib://concepts/validation)" in out
    assert "(oscal-lib://concepts/imports)" in out  # anchor dropped
    assert "(api.html)" in out  # not bundled -> untouched
    assert "(https://x/Y.html)" in out  # external -> untouched
