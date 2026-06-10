from __future__ import annotations

from myob_codex_mcp.metadata.registry import ENTITY_ENDPOINTS, entity_schema


def test_endpoint_registry_covers_core_accounting_domains() -> None:
    expected = {
        "account",
        "tax_code",
        "customer",
        "supplier",
        "invoice",
        "sales_order",
        "bill",
        "customer_payment",
        "supplier_payment",
        "spend_money",
        "receive_money",
        "journal",
        "item",
    }
    assert expected.issubset(ENTITY_ENDPOINTS)


def test_entity_schema_describes_approval_flow() -> None:
    schema = entity_schema("invoice")
    assert schema["paths"]["create"] == "/Sale/Invoice/{layout}"
    assert schema["write_flow"] == "prepare -> accountant/user approval -> commit"
