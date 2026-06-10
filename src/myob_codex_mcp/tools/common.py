from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from myob_codex_mcp.app_context import AppContext
from myob_codex_mcp.approval.models import PendingOperation


def app_context(ctx: Context | None) -> AppContext:
    if ctx is None:
        raise RuntimeError("MCP Context was not injected")
    return ctx.request_context.lifespan_context


def operation_response(operation: PendingOperation) -> dict[str, Any]:
    return {
        "operation_id": operation.operation_id,
        "status": operation.status,
        "operation_type": operation.operation_type,
        "summary": operation.summary,
        "risk_level": operation.risk_level,
        "business_id": operation.business_id,
        "method": operation.method,
        "path": operation.path,
        "params": operation.params,
        "json_body": operation.json_body,
        "request_hash": operation.request_hash,
        "expires_at": operation.expires_at,
        "approval_required": True,
        "approval_phrase": f"APPROVE {operation.operation_id}",
    }
