from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from myob_codex_mcp.metadata.registry import ENTITY_ENDPOINTS, TOOL_CATALOG, entity_schema


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def myob_metadata_list_domains() -> dict:
        """List MYOB entity domains supported by this MCP server."""
        return {
            "entities": sorted(ENTITY_ENDPOINTS.keys()),
            "model": "Named tools plus approval-gated raw MYOB API access.",
        }

    @mcp.tool()
    async def myob_metadata_get_entity_schema(entity: str) -> dict:
        """Return known MYOB endpoint paths and write flow for an entity."""
        return entity_schema(entity)

    @mcp.tool()
    async def myob_metadata_get_tool_catalog() -> dict:
        """Return a machine-readable catalog of major MCP tools and mutation policy."""
        catalog = list(TOOL_CATALOG)
        for entity in sorted(ENTITY_ENDPOINTS):
            catalog.append({
                "name": f"myob_{entity}_list",
                "mutates": False,
                "description": f"List MYOB {entity} records where supported.",
            })
        return {
            "read_only_default": True,
            "writes_require_approval": True,
            "catalog": catalog,
        }
