from __future__ import annotations

import re
from contextlib import suppress
from typing import Any

GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class ValidationError(ValueError):
    """Raised when a tool argument is unsafe or malformed."""


def validate_relative_path(path: str) -> str:
    if not path:
        raise ValidationError("MYOB API path is required")
    if path.startswith("http://") or path.startswith("https://"):
        raise ValidationError("Path must be relative to the MYOB Business API base URL")
    if "://" in path or ".." in path:
        raise ValidationError("Path contains unsupported traversal or scheme")
    clean = path if path.startswith("/") else f"/{path}"
    if "?" in clean:
        raise ValidationError("Pass query string values through the params argument, not path")
    return clean


def validate_method(method: str, *, mutating: bool | None = None) -> str:
    clean = method.upper()
    allowed = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    if clean not in allowed:
        raise ValidationError(f"Unsupported method: {method}")
    if mutating is True and clean == "GET":
        raise ValidationError("Mutation preparation cannot use GET")
    if mutating is False and clean != "GET":
        raise ValidationError("Read-only request must use GET")
    return clean


def validate_guid(value: str, field: str = "uid") -> str:
    if not GUID_RE.match(value):
        raise ValidationError(f"{field} must be a GUID")
    return value


def financial_summary(body: Any) -> dict[str, Any]:
    amounts: list[float] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {"amount", "total", "subtotal", "unitprice", "paymentamount"}:
                    with suppress(TypeError, ValueError):
                        amounts.append(float(item))
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(body)
    return {
        "amount_count": len(amounts),
        "largest_amount": max(amounts) if amounts else None,
        "sum_of_detected_amounts": round(sum(amounts), 2) if amounts else None,
    }
