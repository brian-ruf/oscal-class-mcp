"""Shared test fixtures.

Tests exercise the real server through an in-process FastMCP ``Client`` against real
``oscal`` objects (no mocking of what we can instantiate). The OSCAL support database is
pinned to a throwaway temp directory via ``OSCAL_MCP_SUPPORT_DB`` **before** the server
package configures it, so tests never touch a developer's real support DB.
"""

import os
import tempfile

# Must be set before build_app() configures the support database.
_TMP_SUPPORT = os.path.join(tempfile.mkdtemp(prefix="oscal-mcp-tests-"), "oscal_support.db")
os.environ.setdefault("OSCAL_MCP_SUPPORT_DB", _TMP_SUPPORT)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastmcp import Client  # noqa: E402

from oscal_mcp.server import build_app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """A connected in-process MCP client backed by a fresh app (isolated state)."""
    app = build_app()
    async with Client(app) as c:
        yield c


async def call(client, name, **args):
    """Call a tool and return its structured ``.data`` payload."""
    result = await client.call_tool(name, args)
    return result.data


@pytest.fixture
def minimal_invalid_catalog():
    """Well-formed JSON catalog missing the required metadata ``title`` (structural error)."""
    return (
        '{"catalog": {"uuid": "11111111-1111-1111-1111-111111111111",'
        ' "metadata": {"version": "0.1.0", "oscal-version": "1.1.3"}, "groups": []}}'
    )
