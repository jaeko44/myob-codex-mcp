from __future__ import annotations


class MyobApiError(RuntimeError):
    def __init__(self, status_code: int, message: str, response_body: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        detail = f"MYOB API error {status_code}: {message}"
        if response_body:
            detail += f" | {response_body[:800]}"
        super().__init__(detail)


class UnsafeRetryError(MyobApiError):
    """Raised when retrying a mutating request could duplicate a financial action."""
