"""Support tools: model/version enumeration and structure description."""

import pytest
from fastmcp.exceptions import ToolError

from tests.conftest import call

EIGHT_MODELS = {
    "catalog",
    "profile",
    "mapping-collection",
    "component-definition",
    "system-security-plan",
    "assessment-plan",
    "assessment-results",
    "plan-of-action-and-milestones",
}


async def test_list_oscal_models(client):
    data = await call(client, "list_oscal_models")
    assert EIGHT_MODELS.issubset(set(data["models"]))


async def test_list_oscal_versions(client):
    data = await call(client, "list_oscal_versions")
    assert data["count"] >= 1
    assert data["latest"]
    assert data["latest"] in data["versions"]


async def test_list_versions_filtered_by_model(client):
    data = await call(client, "list_oscal_versions", model="catalog")
    assert data["count"] >= 1
    assert data["model"] == "catalog"


async def test_describe_model_structure_outline(client):
    data = await call(client, "describe_model_structure", model="catalog", format="json")
    assert data["view"] == "outline"
    assert data["model"] == "catalog"
    assert "ms-outline" in data["html"]


async def test_describe_model_structure_bad_format(client):
    with pytest.raises(ToolError):
        await call(client, "describe_model_structure", model="catalog", format="toml")
