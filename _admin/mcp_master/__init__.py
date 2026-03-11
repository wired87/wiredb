"""MCP Master package for hosted eq_storage MCP server and admin helpers."""

from .mcp_master import MCPMaster

try:
    from .mcp_server import create_mcp_server, main as run_hosted_mcp
except ModuleNotFoundError:
    # Allow using config-generation utilities without requiring optional mcp runtime deps.
    create_mcp_server = None
    run_hosted_mcp = None

__all__ = ["MCPMaster", "create_mcp_server", "run_hosted_mcp"]
