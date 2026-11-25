"""Content lifecycle tools: new/load/list/summary/close."""

import pytest
from fastmcp.exceptions import ToolError

from tests.conftest import call


async def test_new_document_returns_live_metadata(client):
    data = await call(client, "new_document", model="catalog", title="Unit Cat", version="1.2.3")
    assert data["model"] == "catalog"
    assert data["title"] == "Unit Cat"  # live metadata, not the template default
    assert data["version"] == "1.2.3"
    assert data["is_valid"] is True
    assert data["handle"].startswith("doc-")
    assert data["uuid"]


async def test_new_document_rejects_unknown_model(client):
    with pytest.raises(ToolError) as exc:
        await call(client, "new_document", model="not-a-model", title="x")
    assert "Unknown OSCAL model" in str(exc.value)


async def test_new_document_supports_all_eight_models(client):
    models = [
        "catalog",
        "profile",
        "mapping-collection",
        "component-definition",
        "system-security-plan",
        "assessment-plan",
        "assessment-results",
        "plan-of-action-and-milestones",
    ]
    for m in models:
        data = await call(client, "new_document", model=m, title=f"{m} doc")
        assert data["model"] == m
        assert data["is_well_formed"] is True
        assert data["is_valid"] is True


async def test_list_and_close_document(client):
    created = await call(client, "new_document", model="profile", title="P1")
    handle = created["handle"]

    listed = await call(client, "list_documents")
    assert listed["count"] >= 1
    assert any(d["handle"] == handle for d in listed["documents"])

    closed = await call(client, "close_document", handle=handle)
    assert closed == {"handle": handle, "closed": True}

    with pytest.raises(ToolError):
        await call(client, "get_document_summary", handle=handle)


async def test_get_summary_unknown_handle(client):
    with pytest.raises(ToolError) as exc:
        await call(client, "get_document_summary", handle="doc-does-not-exist")
    assert "No open document" in str(exc.value)


async def test_close_unknown_handle(client):
    with pytest.raises(ToolError):
        await call(client, "close_document", handle="doc-nope")


async def test_load_content_roundtrips_a_created_document(client):
    created = await call(client, "new_document", model="catalog", title="Reload Me", version="0.9")
    serialized = (await call(client, "convert_document", handle=created["handle"], format="json"))["content"]

    loaded = await call(client, "load_content", content=serialized, href="reload.json")
    assert loaded["model"] == "catalog"
    assert loaded["title"] == "Reload Me"
    assert loaded["is_valid"] is True


async def test_load_invalid_content_is_not_valid(client, minimal_invalid_catalog):
    loaded = await call(client, "load_content", content=minimal_invalid_catalog, href="bad.json")
    assert loaded["is_valid"] is not True
