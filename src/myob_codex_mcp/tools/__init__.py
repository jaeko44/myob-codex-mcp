from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_all_tools(mcp: FastMCP) -> None:
    from myob_codex_mcp.tools import (
        approval_tools,
        auth_tools,
        metadata_tools,
        read_tools,
        write_tools,
    )

    auth_tools.register(mcp)
    metadata_tools.register(mcp)
    read_tools.register(mcp)
    write_tools.register(mcp)
    approval_tools.register(mcp)
