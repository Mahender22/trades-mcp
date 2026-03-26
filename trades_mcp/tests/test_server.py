"""Tests for server metadata and tool registration."""

from trades_mcp.src.server import mcp


def test_server_name():
    assert mcp.name == "Trades MCP Server"


def test_server_has_instructions():
    assert "trades" in mcp.instructions.lower()
    assert "contractor" in mcp.instructions.lower()
