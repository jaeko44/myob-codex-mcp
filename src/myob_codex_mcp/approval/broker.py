from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from myob_codex_mcp.approval.audit import AuditLog
from myob_codex_mcp.approval.models import PendingOperation, payload_hash
from myob_codex_mcp.approval.pending_store import PendingStore
from myob_codex_mcp.approval.policies import classify_operation
from myob_codex_mcp.approval.signer import ApprovalSigner, ApprovalTokenError
from myob_codex_mcp.config import PermissionConfig


class ApprovalError(RuntimeError):
    """Raised when a mutating operation is not approved."""


Executor = Callable[[PendingOperation], Awaitable[Any]]


class ApprovalBroker:
    def __init__(
        self,
        permissions: PermissionConfig,
        store: PendingStore,
        signer: ApprovalSigner,
        audit: AuditLog,
    ) -> None:
        self.permissions = permissions
        self.store = store
        self.signer = signer
        self.audit = audit

    def prepare(
        self,
        *,
        operation_type: str,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        json_body: Any,
        summary: str,
        business_id: str | None,
        risk_level: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PendingOperation:
        method = method.upper()
        if method not in {"POST", "PUT", "PATCH", "DELETE"}:
            raise ApprovalError("Only mutating methods can be prepared for approval")
        if not self.permissions.allow_writes:
            raise ApprovalError("Write tools are disabled by configuration")
        operation = PendingOperation.create(
            operation_type=operation_type,
            method=method,
            path=path,
            params=params,
            json_body=json_body,
            summary=summary,
            risk_level=risk_level or classify_operation(operation_type, method, path, json_body),
            business_id=business_id,
            ttl_seconds=self.permissions.pending_ttl_seconds,
            metadata=metadata,
        )
        self.store.save(operation)
        self.audit.write(
            "operation_prepared",
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            risk_level=operation.risk_level,
            business_id=operation.business_id,
            request_hash=operation.request_hash,
            path=operation.path,
            method=operation.method,
        )
        return operation

    def approve(self, operation_id: str, *, approver: str, reason: str | None = None) -> str:
        operation = self.store.get(operation_id)
        if operation.status != "pending":
            raise ApprovalError(f"Operation is not pending; current status is {operation.status}")
        if time.time() > operation.expires_at:
            operation.status = "expired"
            self.store.update(operation)
            raise ApprovalError("Pending operation has expired")
        operation.status = "approved"
        operation.approved_by = approver
        operation.approved_at = time.time()
        if reason:
            operation.metadata["approval_reason"] = reason
        self.store.update(operation)
        token = self.signer.issue(
            operation_id=operation.operation_id,
            request_hash=operation.request_hash,
            ttl_seconds=self.permissions.approval_ttl_seconds,
        )
        self.audit.write(
            "operation_approved",
            operation_id=operation.operation_id,
            approved_by=approver,
            request_hash=operation.request_hash,
        )
        return token

    def deny(self, operation_id: str, *, denied_by: str, reason: str | None = None) -> PendingOperation:
        operation = self.store.get(operation_id)
        if operation.status not in {"pending", "approved"}:
            raise ApprovalError(f"Operation cannot be denied from status {operation.status}")
        operation.status = "denied"
        operation.denied_by = denied_by
        operation.denied_at = time.time()
        if reason:
            operation.metadata["denial_reason"] = reason
        self.store.update(operation)
        self.audit.write("operation_denied", operation_id=operation.operation_id, denied_by=denied_by)
        return operation

    async def commit(self, operation_id: str, approval_token: str, executor: Executor) -> Any:
        operation = self.store.get(operation_id)
        if operation.status != "approved":
            raise ApprovalError(f"Operation is not approved; current status is {operation.status}")
        if time.time() > operation.expires_at:
            operation.status = "expired"
            self.store.update(operation)
            raise ApprovalError("Pending operation has expired")
        try:
            token_payload = self.signer.verify(approval_token)
        except ApprovalTokenError as exc:
            raise ApprovalError(str(exc)) from exc
        if token_payload.get("operation_id") != operation.operation_id:
            raise ApprovalError("Approval token is for a different operation")
        if token_payload.get("request_hash") != operation.request_hash:
            raise ApprovalError("Approval token does not match the prepared payload hash")
        current_hash = payload_hash(operation.request_payload())
        if current_hash != operation.request_hash:
            raise ApprovalError("Prepared payload changed after approval")
        try:
            result = await executor(operation)
        except Exception as exc:
            operation.status = "failed"
            self.store.update(operation)
            self.audit.write(
                "operation_failed",
                operation_id=operation.operation_id,
                error=str(exc),
                request_hash=operation.request_hash,
            )
            raise
        operation.status = "committed"
        operation.committed_at = time.time()
        if isinstance(result, dict):
            operation.result_ref = str(result.get("UID") or result.get("Number") or "")
        self.store.update(operation)
        self.audit.write(
            "operation_committed",
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            request_hash=operation.request_hash,
            result_ref=operation.result_ref,
        )
        return result
