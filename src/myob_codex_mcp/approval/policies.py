from __future__ import annotations

from typing import Any

RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def classify_operation(operation_type: str, method: str, path: str, body: Any) -> str:
    lowered = f"{operation_type} {method} {path}".lower()
    if method.upper() == "DELETE" or "delete" in lowered or "void" in lowered:
        return "critical"
    if any(term in lowered for term in ["payment", "spendmoney", "receivemoney", "journal"]):
        return "high"
    if any(term in lowered for term in ["invoice", "bill", "order", "attachment"]):
        return "medium"
    if any(term in lowered for term in ["customer", "supplier", "contact"]):
        return "low"
    if body:
        return "medium"
    return "low"


def risk_at_least(actual: str, minimum: str) -> bool:
    return RISK_ORDER.get(actual, 0) >= RISK_ORDER.get(minimum, 0)
