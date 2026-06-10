from __future__ import annotations


def escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


def contains_filter(field: str, value: str) -> str:
    return f"substringof('{escape_odata_string(value)}',{field})"


def equals_filter(field: str, value: str) -> str:
    return f"{field} eq '{escape_odata_string(value)}'"
