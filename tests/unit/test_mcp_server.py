"""The MCP server exposes the lookup_carrier tool (no network needed)."""

import asyncio

from mcp_server.server import mcp


def test_lookup_carrier_tool_is_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "lookup_carrier" in names
