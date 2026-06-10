from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from myob_codex_mcp.app_context import AppContext
from myob_codex_mcp.approval.audit import AuditLog
from myob_codex_mcp.approval.broker import ApprovalBroker
from myob_codex_mcp.approval.pending_store import PendingStore
from myob_codex_mcp.approval.signer import ApprovalSigner
from myob_codex_mcp.auth.oauth import MyobOAuth
from myob_codex_mcp.auth.token_store import EncryptedTokenStore
from myob_codex_mcp.config import load_config
from myob_codex_mcp.logging import configure_logging
from myob_codex_mcp.myob.client import MyobClient
from myob_codex_mcp.tools import register_all_tools

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastMCP) -> AsyncIterator[AppContext]:
    config = load_config()
    configure_logging(config.log_level)
    config.home.mkdir(parents=True, exist_ok=True)
    token_store = EncryptedTokenStore(config.token_path, config.token_key_path)
    auth = MyobOAuth(config.auth, token_store)
    client = MyobClient(config, auth)
    approvals = ApprovalBroker(
        config.permissions,
        PendingStore(config.pending_path),
        ApprovalSigner(config.signing_key_path),
        AuditLog(config.audit_path),
    )
    logger.info("Starting MYOB Codex MCP server")
    try:
        yield AppContext(config=config, auth=auth, client=client, approvals=approvals)
    finally:
        await client.close()
        logger.info("Stopped MYOB Codex MCP server")


mcp = FastMCP(
    "myob-codex-mcp",
    instructions=(
        "MYOB Business / AccountRight cloud MCP server. Read tools are safe by default. "
        "Any MYOB mutation must be prepared, approved by the accountant/user, and then committed "
        "with a matching approval token."
    ),
    lifespan=app_lifespan,
)

register_all_tools(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
