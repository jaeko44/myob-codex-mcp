from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from myob_codex_mcp.metadata.registry import ENTITY_ENDPOINTS
from myob_codex_mcp.safety.validators import validate_guid, validate_relative_path
from myob_codex_mcp.tools.common import app_context


async def _list(ctx: Context | None, path: str, params: dict[str, Any] | None, top: int, max_items: int) -> list[dict[str, Any]]:
    app = app_context(ctx)
    return await app.client.paged(path, params=params, top=top, max_items=max_items)


async def _get(ctx: Context | None, path: str, uid: str) -> Any:
    app = app_context(ctx)
    validate_guid(uid)
    return await app.client.request("GET", path.format(uid=uid))


def _filter_params(filter: str | None = None, orderby: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if filter:
        params["$filter"] = filter
    if orderby:
        params["$orderby"] = orderby
    return params


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def myob_company_get_context(ctx: Context) -> dict:
        """Return the selected MYOB business/company file context."""
        app = app_context(ctx)
        return {
            "business_id": app.config.default_business_id or app.auth.business_id(),
            "authenticated": app.auth.status().get("authenticated", False),
            "api_base_url": app.config.api_base_url,
        }

    @mcp.tool()
    async def myob_company_list_files(ctx: Context) -> Any:
        """Try to list accessible company files. New MYOB OAuth flows may require businessId from consent instead."""
        app = app_context(ctx)
        return await app.client.request("GET", "/", require_business_id=False)

    @mcp.tool()
    async def myob_raw_get(path: str, params: dict[str, Any] | None = None, ctx: Context = None) -> Any:
        """Read any MYOB Business API endpoint with GET. This tool is read-only."""
        app = app_context(ctx)
        clean_path = validate_relative_path(path)
        return await app.client.request("GET", clean_path, params=params)

    @mcp.tool()
    async def myob_entity_list(
        entity: str,
        filter: str | None = None,
        orderby: str | None = None,
        top: int = 200,
        max_items: int = 1000,
        ctx: Context = None,
    ) -> list[dict[str, Any]]:
        """List records for a supported MYOB entity using the endpoint registry."""
        if entity not in ENTITY_ENDPOINTS or not ENTITY_ENDPOINTS[entity].list_path:
            raise ValueError(f"Entity does not have a list endpoint: {entity}")
        return await _list(ctx, ENTITY_ENDPOINTS[entity].list_path or "", _filter_params(filter, orderby), top, max_items)

    @mcp.tool()
    async def myob_entity_get(entity: str, uid: str, layout: str | None = None, ctx: Context = None) -> Any:
        """Get one MYOB record by entity and UID. layout is needed for some invoice/bill/order details."""
        if entity not in ENTITY_ENDPOINTS or not ENTITY_ENDPOINTS[entity].get_path:
            raise ValueError(f"Entity does not have a get endpoint: {entity}")
        path = ENTITY_ENDPOINTS[entity].get_path or ""
        if "{layout}" in path:
            if not layout:
                raise ValueError("layout is required for this entity")
            path = path.replace("{layout}", layout)
        return await _get(ctx, path, uid)

    @mcp.tool()
    async def myob_account_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List chart of accounts."""
        return await _list(ctx, "/GeneralLedger/Account", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_account_get(uid: str, ctx: Context) -> Any:
        """Get a chart-of-accounts record by UID."""
        return await _get(ctx, "/GeneralLedger/Account/{uid}", uid)

    @mcp.tool()
    async def myob_tax_code_list(top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List tax codes."""
        return await _list(ctx, "/GeneralLedger/TaxCode", None, top, 1000)

    @mcp.tool()
    async def myob_job_list(top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List jobs."""
        return await _list(ctx, "/GeneralLedger/Job", None, top, 1000)

    @mcp.tool()
    async def myob_customer_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List customers."""
        return await _list(ctx, "/Contact/Customer", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_supplier_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List suppliers."""
        return await _list(ctx, "/Contact/Supplier", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_employee_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List employees."""
        return await _list(ctx, "/Contact/Employee", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_contact_get(uid: str, ctx: Context) -> Any:
        """Get any contact by UID."""
        return await _get(ctx, "/Contact/{uid}", uid)

    @mcp.tool()
    async def myob_invoice_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List sales invoices."""
        return await _list(ctx, "/Sale/Invoice", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_invoice_get(uid: str, layout: str | None = None, ctx: Context = None) -> Any:
        """Get invoice by UID. If layout is supplied, reads the layout-specific detail endpoint."""
        return await _get(ctx, f"/Sale/Invoice/{layout}/{{uid}}" if layout else "/Sale/Invoice/{uid}", uid)

    @mcp.tool()
    async def myob_bill_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List purchase bills."""
        return await _list(ctx, "/Purchase/Bill", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_bill_get(uid: str, layout: str | None = None, ctx: Context = None) -> Any:
        """Get bill by UID. If layout is supplied, reads the layout-specific detail endpoint."""
        return await _get(ctx, f"/Purchase/Bill/{layout}/{{uid}}" if layout else "/Purchase/Bill/{uid}", uid)

    @mcp.tool()
    async def myob_customer_payment_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List customer payments."""
        return await _list(ctx, "/Sale/CustomerPayment", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_supplier_payment_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List supplier payments."""
        return await _list(ctx, "/Purchase/SupplierPayment", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_bank_account_list(top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List bank accounts."""
        return await _list(ctx, "/Banking/BankAccount", None, top, 1000)

    @mcp.tool()
    async def myob_spend_money_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List spend-money transactions."""
        return await _list(ctx, "/Banking/SpendMoneyTxn", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_receive_money_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List receive-money transactions."""
        return await _list(ctx, "/Banking/ReceiveMoneyTxn", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_inventory_item_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List inventory items."""
        return await _list(ctx, "/Inventory/Item", _filter_params(filter), top, 1000)

    @mcp.tool()
    async def myob_journal_list(filter: str | None = None, top: int = 200, ctx: Context = None) -> list[dict[str, Any]]:
        """List general journal records."""
        return await _list(ctx, "/GeneralLedger/GeneralJournal", _filter_params(filter), top, 1000)
