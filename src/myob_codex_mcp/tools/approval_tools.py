from __future__ import annotations

from mcp.server.fastmcp import Context, FastMCP

from myob_codex_mcp.tools.common import app_context, operation_response


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def myob_approval_list_pending(ctx: Context) -> dict:
        """List pending or approved MYOB operations awaiting user/accountant action."""
        app = app_context(ctx)
        return {
            "operations": [operation_response(op) for op in app.approvals.store.list() if op.status in {"pending", "approved"}]
        }

    @mcp.tool()
    async def myob_approval_get(operation_id: str, ctx: Context) -> dict:
        """Get the full approval preview for a MYOB operation."""
        app = app_context(ctx)
        return operation_response(app.approvals.store.get(operation_id))

    @mcp.tool()
    async def myob_approval_approve(
        operation_id: str,
        approver: str,
        approval_phrase: str,
        reason: str | None = None,
        ctx: Context = None,
    ) -> dict:
        """Approve a prepared MYOB write. The approval_phrase must be exactly 'APPROVE <operation_id>'."""
        expected = f"APPROVE {operation_id}"
        if approval_phrase != expected:
            raise ValueError(f"approval_phrase must be exactly: {expected}")
        app = app_context(ctx)
        token = app.approvals.approve(operation_id, approver=approver, reason=reason)
        return {
            "operation_id": operation_id,
            "approval_token": token,
            "message": "Operation approved. Pass approval_token to myob_commit_operation or the relevant commit tool.",
        }

    @mcp.tool()
    async def myob_approval_deny(
        operation_id: str,
        denied_by: str,
        reason: str | None = None,
        ctx: Context = None,
    ) -> dict:
        """Deny a prepared or approved MYOB write operation."""
        app = app_context(ctx)
        operation = app.approvals.deny(operation_id, denied_by=denied_by, reason=reason)
        return operation_response(operation)
