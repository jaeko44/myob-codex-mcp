from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from myob_codex_mcp.approval.models import PendingOperation
from myob_codex_mcp.metadata.registry import ENTITY_ENDPOINTS
from myob_codex_mcp.safety.validators import (
    financial_summary,
    validate_guid,
    validate_method,
    validate_relative_path,
)
from myob_codex_mcp.tools.common import app_context, operation_response


def _business_id(ctx: Context | None, business_id: str | None) -> str | None:
    app = app_context(ctx)
    return business_id or app.auth.business_id() or app.config.default_business_id


def _prepare(
    ctx: Context | None,
    *,
    operation_type: str,
    method: str,
    path: str,
    body: Any,
    params: dict[str, Any] | None = None,
    summary: str,
    business_id: str | None = None,
    risk_level: str | None = None,
) -> dict[str, Any]:
    app = app_context(ctx)
    clean_path = validate_relative_path(path)
    clean_method = validate_method(method, mutating=True)
    selected_business = _business_id(ctx, business_id)
    operation = app.approvals.prepare(
        operation_type=operation_type,
        method=clean_method,
        path=clean_path,
        params=params,
        json_body=body,
        summary=summary,
        business_id=selected_business,
        risk_level=risk_level,
        metadata={"financial_summary": financial_summary(body)},
    )
    response = operation_response(operation)
    response["financial_summary"] = financial_summary(body)
    return response


async def _commit(ctx: Context | None, operation_id: str, approval_token: str) -> Any:
    app = app_context(ctx)

    async def execute(operation: PendingOperation) -> Any:
        return await app.client.request(
            operation.method,
            operation.path,
            business_id=operation.business_id,
            params=operation.params,
            json_body=operation.json_body,
            idempotency_key=operation.operation_id,
        )

    return await app.approvals.commit(operation_id, approval_token, execute)


def _layout_path(base: str, layout: str | None, uid: str | None = None) -> str:
    path = f"{base}/{layout}" if layout else base
    if uid:
        validate_guid(uid)
        path = f"{path}/{uid}"
    return path


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def myob_raw_prepare_mutation(
        method: str,
        path: str,
        json_body: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        summary: str = "Raw MYOB API mutation",
        business_id: str | None = None,
        risk_level: str | None = None,
        ctx: Context = None,
    ) -> dict[str, Any]:
        """Prepare any MYOB POST/PUT/PATCH/DELETE request. This does not call MYOB until approved and committed."""
        return _prepare(
            ctx,
            operation_type="raw.mutation",
            method=method,
            path=path,
            body=json_body,
            params=params,
            summary=summary,
            business_id=business_id,
            risk_level=risk_level,
        )

    @mcp.tool()
    async def myob_raw_commit_mutation(operation_id: str, approval_token: str, ctx: Context) -> Any:
        """Commit an approved raw MYOB mutation. This mutates MYOB and requires a valid approval token."""
        return await _commit(ctx, operation_id, approval_token)

    @mcp.tool()
    async def myob_commit_operation(operation_id: str, approval_token: str, ctx: Context) -> Any:
        """Commit any approved MYOB operation. This mutates MYOB and requires a valid approval token."""
        return await _commit(ctx, operation_id, approval_token)

    @mcp.tool()
    async def myob_entity_prepare_create(
        entity: str,
        json_body: dict[str, Any],
        layout: str | None = None,
        summary: str | None = None,
        business_id: str | None = None,
        ctx: Context = None,
    ) -> dict[str, Any]:
        """Prepare create for a supported entity using the endpoint registry."""
        endpoint = ENTITY_ENDPOINTS.get(entity)
        if not endpoint or not endpoint.create_path:
            raise ValueError(f"Entity does not support create: {entity}")
        path = endpoint.create_path.replace("{layout}", layout or "")
        return _prepare(
            ctx,
            operation_type=f"{entity}.create",
            method="POST",
            path=path,
            body=json_body,
            summary=summary or f"Create MYOB {entity}",
            business_id=business_id,
        )

    @mcp.tool()
    async def myob_entity_prepare_update(
        entity: str,
        uid: str,
        json_body: dict[str, Any],
        layout: str | None = None,
        summary: str | None = None,
        business_id: str | None = None,
        ctx: Context = None,
    ) -> dict[str, Any]:
        """Prepare update for a supported entity using the endpoint registry."""
        validate_guid(uid)
        endpoint = ENTITY_ENDPOINTS.get(entity)
        if not endpoint or not endpoint.update_path:
            raise ValueError(f"Entity does not support update: {entity}")
        path = endpoint.update_path.replace("{layout}", layout or "").replace("{uid}", uid)
        return _prepare(
            ctx,
            operation_type=f"{entity}.update",
            method="PUT",
            path=path,
            body=json_body,
            summary=summary or f"Update MYOB {entity} {uid}",
            business_id=business_id,
        )

    @mcp.tool()
    async def myob_customer_prepare_create(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare creation of a customer contact. Requires approval before commit."""
        return _prepare(ctx, operation_type="customer.create", method="POST", path="/Contact/Customer", body=json_body, summary="Create MYOB customer", business_id=business_id)

    @mcp.tool()
    async def myob_customer_prepare_update(uid: str, json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare update of a customer contact. Requires approval before commit."""
        validate_guid(uid)
        return _prepare(ctx, operation_type="customer.update", method="PUT", path=f"/Contact/Customer/{uid}", body=json_body, summary=f"Update MYOB customer {uid}", business_id=business_id)

    @mcp.tool()
    async def myob_supplier_prepare_create(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare creation of a supplier contact. Requires approval before commit."""
        return _prepare(ctx, operation_type="supplier.create", method="POST", path="/Contact/Supplier", body=json_body, summary="Create MYOB supplier", business_id=business_id)

    @mcp.tool()
    async def myob_supplier_prepare_update(uid: str, json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare update of a supplier contact. Requires approval before commit."""
        validate_guid(uid)
        return _prepare(ctx, operation_type="supplier.update", method="PUT", path=f"/Contact/Supplier/{uid}", body=json_body, summary=f"Update MYOB supplier {uid}", business_id=business_id)

    @mcp.tool()
    async def myob_invoice_prepare_create(json_body: dict[str, Any], layout: str = "Service", business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare creation of a sales invoice. Requires approval before commit."""
        return _prepare(ctx, operation_type="invoice.create", method="POST", path=_layout_path("/Sale/Invoice", layout), body=json_body, summary=f"Create MYOB {layout} invoice", business_id=business_id)

    @mcp.tool()
    async def myob_invoice_prepare_update(uid: str, json_body: dict[str, Any], layout: str = "Service", business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare update of a sales invoice. Requires approval before commit."""
        return _prepare(ctx, operation_type="invoice.update", method="PUT", path=_layout_path("/Sale/Invoice", layout, uid), body=json_body, summary=f"Update MYOB invoice {uid}", business_id=business_id)

    @mcp.tool()
    async def myob_invoice_prepare_delete(uid: str, layout: str = "Service", business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare deletion/void-style removal of a sales invoice where MYOB permits it. Critical approval required."""
        return _prepare(ctx, operation_type="invoice.delete", method="DELETE", path=_layout_path("/Sale/Invoice", layout, uid), body=None, summary=f"Delete MYOB invoice {uid}", risk_level="critical", business_id=business_id)

    @mcp.tool()
    async def myob_sales_order_prepare_create(json_body: dict[str, Any], layout: str = "Service", business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare creation of a sales order. Requires approval before commit."""
        return _prepare(ctx, operation_type="sales_order.create", method="POST", path=_layout_path("/Sale/Order", layout), body=json_body, summary=f"Create MYOB {layout} sales order", business_id=business_id)

    @mcp.tool()
    async def myob_bill_prepare_create(json_body: dict[str, Any], layout: str = "Item", business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare creation of a purchase bill. Requires approval before commit."""
        return _prepare(ctx, operation_type="bill.create", method="POST", path=_layout_path("/Purchase/Bill", layout), body=json_body, summary=f"Create MYOB {layout} bill", business_id=business_id)

    @mcp.tool()
    async def myob_bill_prepare_update(uid: str, json_body: dict[str, Any], layout: str = "Item", business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare update of a purchase bill. Requires approval before commit."""
        return _prepare(ctx, operation_type="bill.update", method="PUT", path=_layout_path("/Purchase/Bill", layout, uid), body=json_body, summary=f"Update MYOB bill {uid}", business_id=business_id)

    @mcp.tool()
    async def myob_customer_payment_prepare_record(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare recording a customer payment. High-risk approval required."""
        return _prepare(ctx, operation_type="customer_payment.record", method="POST", path="/Sale/CustomerPayment", body=json_body, summary="Record MYOB customer payment", risk_level="high", business_id=business_id)

    @mcp.tool()
    async def myob_supplier_payment_prepare_record(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare recording a supplier payment. High-risk approval required."""
        return _prepare(ctx, operation_type="supplier_payment.record", method="POST", path="/Purchase/SupplierPayment", body=json_body, summary="Record MYOB supplier payment", risk_level="high", business_id=business_id)

    @mcp.tool()
    async def myob_spend_money_prepare_create(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare spend-money transaction creation. High-risk approval required."""
        return _prepare(ctx, operation_type="spend_money.create", method="POST", path="/Banking/SpendMoneyTxn", body=json_body, summary="Create MYOB spend-money transaction", risk_level="high", business_id=business_id)

    @mcp.tool()
    async def myob_receive_money_prepare_create(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare receive-money transaction creation. High-risk approval required."""
        return _prepare(ctx, operation_type="receive_money.create", method="POST", path="/Banking/ReceiveMoneyTxn", body=json_body, summary="Create MYOB receive-money transaction", risk_level="high", business_id=business_id)

    @mcp.tool()
    async def myob_journal_prepare_create(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare general journal creation. High-risk approval required."""
        return _prepare(ctx, operation_type="journal.create", method="POST", path="/GeneralLedger/GeneralJournal", body=json_body, summary="Create MYOB general journal", risk_level="high", business_id=business_id)

    @mcp.tool()
    async def myob_inventory_item_prepare_create(json_body: dict[str, Any], business_id: str | None = None, ctx: Context = None) -> dict[str, Any]:
        """Prepare inventory item creation. Requires approval before commit."""
        return _prepare(ctx, operation_type="inventory_item.create", method="POST", path="/Inventory/Item", body=json_body, summary="Create MYOB inventory item", business_id=business_id)

    @mcp.tool()
    async def myob_attachment_prepare_upload(
        parent_path: str,
        file_name: str,
        content_base64: str,
        content_type: str = "application/octet-stream",
        business_id: str | None = None,
        ctx: Context = None,
    ) -> dict[str, Any]:
        """Prepare attachment upload. content_base64 is stored in the pending payload until approved."""
        body = {
            "file_name": file_name,
            "content_type": content_type,
            "content_base64": content_base64,
            "transport_note": "Commit currently sends JSON. Use raw mutation/custom multipart support if MYOB requires multipart for this endpoint.",
        }
        path = f"{validate_relative_path(parent_path).rstrip('/')}/Attachment"
        return _prepare(ctx, operation_type="attachment.upload", method="POST", path=path, body=body, summary=f"Upload MYOB attachment {file_name}", risk_level="medium", business_id=business_id)
