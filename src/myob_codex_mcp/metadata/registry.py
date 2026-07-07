from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityEndpoint:
    entity: str
    list_path: str | None = None
    get_path: str | None = None
    create_path: str | None = None
    update_path: str | None = None
    delete_path: str | None = None
    notes: str = ""


ENTITY_ENDPOINTS: dict[str, EntityEndpoint] = {
    "account": EntityEndpoint("account", "/GeneralLedger/Account", "/GeneralLedger/Account/{uid}"),
    "tax_code": EntityEndpoint("tax_code", "/GeneralLedger/TaxCode"),
    "job": EntityEndpoint("job", "/GeneralLedger/Job", "/GeneralLedger/Job/{uid}"),
    "customer": EntityEndpoint(
        "customer",
        "/Contact/Customer",
        "/Contact/{uid}",
        "/Contact/Customer",
        "/Contact/Customer/{uid}",
    ),
    "supplier": EntityEndpoint(
        "supplier",
        "/Contact/Supplier",
        "/Contact/{uid}",
        "/Contact/Supplier",
        "/Contact/Supplier/{uid}",
    ),
    "employee": EntityEndpoint("employee", "/Contact/Employee", "/Contact/{uid}"),
    "invoice": EntityEndpoint(
        "invoice",
        "/Sale/Invoice",
        "/Sale/Invoice/{uid}",
        "/Sale/Invoice/{layout}",
        "/Sale/Invoice/{layout}/{uid}",
        "/Sale/Invoice/{layout}/{uid}",
        "layout is Service, Item, Professional, TimeBilling, or Miscellaneous",
    ),
    "sales_order": EntityEndpoint(
        "sales_order",
        "/Sale/Order",
        "/Sale/Order/{uid}",
        "/Sale/Order/{layout}",
        "/Sale/Order/{layout}/{uid}",
        "/Sale/Order/{layout}/{uid}",
    ),
    "customer_payment": EntityEndpoint(
        "customer_payment",
        "/Sale/CustomerPayment",
        "/Sale/CustomerPayment/{uid}",
        "/Sale/CustomerPayment",
    ),
    "bill": EntityEndpoint(
        "bill",
        "/Purchase/Bill",
        "/Purchase/Bill/{uid}",
        "/Purchase/Bill/{layout}",
        "/Purchase/Bill/{layout}/{uid}",
        "/Purchase/Bill/{layout}/{uid}",
    ),
    "supplier_payment": EntityEndpoint(
        "supplier_payment",
        "/Purchase/SupplierPayment",
        "/Purchase/SupplierPayment/{uid}",
        "/Purchase/SupplierPayment",
    ),
    "bank_account": EntityEndpoint("bank_account", "/Banking/BankAccount"),
    "spend_money": EntityEndpoint(
        "spend_money",
        "/Banking/SpendMoneyTxn",
        "/Banking/SpendMoneyTxn/{uid}",
        "/Banking/SpendMoneyTxn",
    ),
    "receive_money": EntityEndpoint(
        "receive_money",
        "/Banking/ReceiveMoneyTxn",
        "/Banking/ReceiveMoneyTxn/{uid}",
        "/Banking/ReceiveMoneyTxn",
    ),
    "journal": EntityEndpoint(
        "journal",
        "/GeneralLedger/GeneralJournal",
        "/GeneralLedger/GeneralJournal/{uid}",
        "/GeneralLedger/GeneralJournal",
    ),
    "item": EntityEndpoint(
        "item",
        "/Inventory/Item",
        "/Inventory/Item/{uid}",
        "/Inventory/Item",
        "/Inventory/Item/{uid}",
    ),
}


TOOL_CATALOG: list[dict[str, Any]] = [
    {"name": "myob_auth_status", "mutates": False, "description": "Show OAuth and business context status."},
    {"name": "myob_oauth_authorize_business", "mutates": False, "description": "Start MYOB OAuth consent for one business/company file."},
    {"name": "myob_business_list_authorized", "mutates": False, "description": "List locally authorised MYOB businesses."},
    {"name": "myob_business_set_default", "mutates": False, "description": "Set default business context for future calls."},
    {"name": "myob_business_remove_authorization", "mutates": False, "description": "Remove locally stored tokens for one business."},
    {"name": "myob_raw_get", "mutates": False, "description": "Read any MYOB API endpoint with GET."},
    {"name": "myob_raw_prepare_mutation", "mutates": False, "description": "Prepare any POST/PUT/PATCH/DELETE request for approval."},
    {"name": "myob_raw_commit_mutation", "mutates": True, "requires_approval": True, "description": "Commit an approved raw MYOB mutation."},
]


def entity_schema(entity: str) -> dict[str, Any]:
    if entity not in ENTITY_ENDPOINTS:
        raise KeyError(f"Unknown MYOB entity: {entity}")
    endpoint = ENTITY_ENDPOINTS[entity]
    return {
        "entity": endpoint.entity,
        "paths": {
            "list": endpoint.list_path,
            "get": endpoint.get_path,
            "create": endpoint.create_path,
            "update": endpoint.update_path,
            "delete": endpoint.delete_path,
        },
        "notes": endpoint.notes,
        "write_flow": "prepare -> accountant/user approval -> commit",
    }
