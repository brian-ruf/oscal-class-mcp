"""Query and import-inspection tools."""

import pytest
from fastmcp.exceptions import ToolError

from tests.conftest import call


async def test_query_json_syntax_first_only(client):
    created = await call(client, "new_document", model="catalog", title="Queryable", version="1.0")
    res = await call(
        client,
        "query_document",
        handle=created["handle"],
        path="/*/metadata/title",
        json_syntax=True,
        first_only=True,
    )
    assert res["matches"] == "Queryable"
    assert res["count"] == 1


async def test_query_xml_syntax(client):
    created = await call(client, "new_document", model="catalog", title="XmlQ", version="1.0")
    res = await call(
        client,
        "query_document",
        handle=created["handle"],
        path="/*/metadata/title",
        json_syntax=False,
        first_only=True,
    )
    assert res["matches"] == "XmlQ"


async def test_query_unknown_handle(client):
    with pytest.raises(ToolError):
        await call(client, "query_document", handle="doc-x", path="/*/metadata/title")


async def test_inspect_imports_on_catalog_has_none(client):
    """A catalog has no import statements."""
    created = await call(client, "new_document", model="catalog", title="NoImports")
    report = await call(client, "inspect_imports", handle=created["handle"])
    assert report["count"] == 0
    assert report["failed_count"] == 0
    assert report["imports"] == []


async def test_inspect_imports_unknown_handle(client):
    with pytest.raises(ToolError):
        await call(client, "inspect_imports", handle="doc-x")
