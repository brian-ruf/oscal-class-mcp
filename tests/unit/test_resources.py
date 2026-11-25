"""Coding-help resources and the search_library_api tool."""

import json

import pytest
from fastmcp.exceptions import ToolError

from tests.conftest import call


async def _read_json(client, uri):
    contents = await client.read_resource(uri)
    return json.loads(contents[0].text)


async def test_recipes_index_lists_all(client):
    data = await _read_json(client, "oscal-lib://recipes")
    names = {r["name"] for r in data["recipes"]}
    assert {"load-validate-convert", "create-catalog", "tailor-profile"}.issubset(names)


async def test_single_recipe(client):
    contents = await client.read_resource("oscal-lib://recipes/create-catalog")
    assert contents[0].text.startswith("# ")


async def test_unknown_recipe_errors(client):
    with pytest.raises(Exception):
        await client.read_resource("oscal-lib://recipes/does-not-exist")


async def test_about_resource_reports_parity(client):
    data = await _read_json(client, "oscal-lib://about")
    assert data["server"] == "oscal-mcp"
    # Installed oscal version is discovered live and must be present.
    assert data["installed_oscal"]
    assert data["parity"]["status"] in ("ok", "mismatch", "not-bundled")
    # Both known knowledge collections are always described (bundled or not).
    assert {"oscal_lib", "oscal_std"}.issubset(data["knowledge_collections"].keys())


async def test_api_index_resource(client):
    data = await _read_json(client, "oscal-lib://api")
    assert "modules" in data and data["modules"]
    assert data["meta"]["package_name"] == "oscal"


async def test_api_symbol_resource(client):
    data = await _read_json(client, "oscal-lib://api/oscal.oscal_controls.Profile.resolve")
    assert data["fqname"] == "oscal.oscal_controls.Profile.resolve"
    assert data["kind"] in ("method", "function")


async def test_concepts_index_lists_guides(client):
    data = await _read_json(client, "oscal-lib://concepts")
    names = {c["name"] for c in data["concepts"]}
    # Core operating-concept guides must be bundled.
    assert {"validation", "imports", "profile-processing"}.issubset(names)
    assert all(c["uri"].startswith("oscal-lib://concepts/") for c in data["concepts"])


async def test_single_concept_guide(client):
    contents = await client.read_resource("oscal-lib://concepts/validation")
    assert contents[0].text.startswith("# ")


async def test_unknown_concept_errors(client):
    with pytest.raises(Exception):
        await client.read_resource("oscal-lib://concepts/does-not-exist")


async def test_search_knowledge_finds_concept(client):
    data = await call(client, "search_knowledge", query="profile resolution directives", scope="lib")
    assert data["count"] >= 1
    assert any(r["name"] == "profile-processing" for r in data["results"])
    assert data["results"][0]["uri"].startswith("oscal-lib://concepts/")


async def test_standard_index_lists_pages_and_notes(client):
    data = await _read_json(client, "oscal-std://concepts")
    names = {c["name"] for c in data["concepts"]}
    # Per-model concept pages and the authored notes are present.
    assert {"catalog", "profile", "ssp", "additional-notes"}.issubset(names)
    assert data["license"]  # NIST public-domain / CC0 attribution recorded
    assert any(c["authored"] for c in data["concepts"])


async def test_standard_page(client):
    contents = await client.read_resource("oscal-std://concepts/profile")
    assert len(contents[0].text) > 200


async def test_standard_notes_resource(client):
    contents = await client.read_resource("oscal-std://notes")
    text = contents[0].text
    assert "Additional Notes" in text
    assert "profile" in text.lower()  # the seeded draft/child-group note


async def test_search_knowledge_std_scope_finds_notes(client):
    data = await call(client, "search_knowledge", query="profile draft child groups", scope="std")
    assert data["count"] >= 1
    assert any(r["name"] == "additional-notes" for r in data["results"])


async def test_search_knowledge_rejects_bad_scope(client):
    with pytest.raises(ToolError):
        await call(client, "search_knowledge", query="validation", scope="bogus")


async def test_search_knowledge_empty_query_errors(client):
    with pytest.raises(ToolError):
        await call(client, "search_knowledge", query="   ")


async def test_metaschema_resource(client):
    data = await _read_json(client, "oscal-lib://metaschema/catalog")
    assert data["model"] == "catalog"
    assert "ms-outline" in data["html"]


async def test_search_library_api_ranks_relevant_symbol(client):
    data = await call(client, "search_library_api", query="resolve profile", limit=5)
    assert data["count"] >= 1
    top = data["results"][0]["fqname"]
    assert "Profile" in top and "resolve" in top.lower()


async def test_search_library_api_empty_query_errors(client):
    with pytest.raises(ToolError):
        await call(client, "search_library_api", query="   ")
