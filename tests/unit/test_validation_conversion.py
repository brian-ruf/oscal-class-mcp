"""Validation and conversion/serialization tools."""

import pytest
from fastmcp.exceptions import ToolError

from tests.conftest import call


async def test_validate_valid_document(client):
    created = await call(client, "new_document", model="catalog", title="V", version="1.0")
    report = await call(client, "validate_document", handle=created["handle"])
    assert report["is_valid"] is True
    assert all(report["validation_status"].values())
    assert report["errors"] == []
    assert report["tier"] == "standard"


async def test_validate_full_tier(client):
    created = await call(client, "new_document", model="catalog", title="VF")
    report = await call(client, "validate_document", handle=created["handle"], full=True)
    assert report["tier"] == "full"
    assert report["is_minimally_valid"] is True


async def test_validate_reports_errors_for_invalid(client, minimal_invalid_catalog):
    loaded = await call(client, "load_content", content=minimal_invalid_catalog)
    report = await call(client, "validate_document", handle=loaded["handle"])
    assert report["is_valid"] is not True
    assert isinstance(report["errors"], list)
    assert len(report["errors"]) >= 1
    # Each error is normalized by the library.
    assert "error-type" in report["errors"][0]


async def test_validate_unknown_handle(client):
    with pytest.raises(ToolError):
        await call(client, "validate_document", handle="doc-x")


@pytest.mark.parametrize("fmt", ["xml", "json", "yaml"])
async def test_convert_each_format(client, fmt):
    created = await call(client, "new_document", model="catalog", title="C", version="1.0")
    out = await call(client, "convert_document", handle=created["handle"], format=fmt)
    assert out["format"] == fmt
    assert out["content"].strip()


async def test_convert_rejects_bad_format(client):
    created = await call(client, "new_document", model="catalog", title="C")
    with pytest.raises(ToolError) as exc:
        await call(client, "convert_document", handle=created["handle"], format="toml")
    assert "Unknown format" in str(exc.value)


async def test_roundtrip_fidelity_across_formats(client):
    """XML -> JSON -> YAML should each reload as an equivalent, valid catalog."""
    created = await call(client, "new_document", model="catalog", title="RoundTrip", version="2.0")
    handle = created["handle"]
    for fmt in ("xml", "json", "yaml"):
        serialized = (await call(client, "convert_document", handle=handle, format=fmt))["content"]
        reloaded = await call(client, "load_content", content=serialized, href=f"rt.{fmt}")
        assert reloaded["model"] == "catalog"
        assert reloaded["title"] == "RoundTrip"
        assert reloaded["version"] == "2.0"
        assert reloaded["is_valid"] is True


async def test_save_document_to_disk(client, tmp_path):
    created = await call(client, "new_document", model="catalog", title="Saved", version="1.0")
    target = tmp_path / "saved.json"
    result = await call(client, "save_document", handle=created["handle"], path=str(target), format="json")
    assert result["saved"] is True
    assert target.exists() and target.read_text().strip()
