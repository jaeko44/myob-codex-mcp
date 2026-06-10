from __future__ import annotations

from myob_codex_mcp.approval.audit import AuditLog
from myob_codex_mcp.approval.broker import ApprovalBroker
from myob_codex_mcp.approval.models import PendingOperation
from myob_codex_mcp.approval.pending_store import PendingStore
from myob_codex_mcp.approval.signer import ApprovalSigner
from myob_codex_mcp.config import PermissionConfig


def make_broker(tmp_path) -> ApprovalBroker:
    return ApprovalBroker(
        PermissionConfig(allow_writes=True, approval_ttl_seconds=60, pending_ttl_seconds=60),
        PendingStore(tmp_path / "pending.json"),
        ApprovalSigner(tmp_path / "signing.key"),
        AuditLog(tmp_path / "audit.jsonl"),
    )


async def test_commit_requires_approval_and_payload_hash_match(tmp_path) -> None:
    broker = make_broker(tmp_path)
    operation = broker.prepare(
        operation_type="invoice.create",
        method="POST",
        path="/Sale/Invoice/Service",
        params=None,
        json_body={"Number": "INV-001", "Total": 100},
        summary="Create invoice INV-001",
        business_id="business-id",
    )

    async def execute(op: PendingOperation):
        return {"UID": "created", "Number": op.json_body["Number"]}

    try:
        await broker.commit(operation.operation_id, "not-approved", execute)
    except Exception as exc:
        assert "not approved" in str(exc)
    else:
        raise AssertionError("Commit should require approval")

    token = broker.approve(operation.operation_id, approver="accountant")
    stored = broker.store.get(operation.operation_id)
    stored.json_body["Total"] = 200
    broker.store.update(stored)

    try:
        await broker.commit(operation.operation_id, token, execute)
    except Exception as exc:
        assert "changed after approval" in str(exc)
    else:
        raise AssertionError("Commit should reject modified payload")


async def test_approved_operation_commits_once(tmp_path) -> None:
    broker = make_broker(tmp_path)
    operation = broker.prepare(
        operation_type="customer.create",
        method="POST",
        path="/Contact/Customer",
        params=None,
        json_body={"CompanyName": "ABC Pty Ltd"},
        summary="Create customer",
        business_id="business-id",
    )
    token = broker.approve(operation.operation_id, approver="accountant")

    async def execute(op: PendingOperation):
        return {"UID": "customer-uid", "CompanyName": op.json_body["CompanyName"]}

    result = await broker.commit(operation.operation_id, token, execute)
    assert result["UID"] == "customer-uid"
    assert broker.store.get(operation.operation_id).status == "committed"

    try:
        await broker.commit(operation.operation_id, token, execute)
    except Exception as exc:
        assert "not approved" in str(exc)
    else:
        raise AssertionError("Operation should not commit twice")
