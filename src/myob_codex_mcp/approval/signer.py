from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from contextlib import suppress
from pathlib import Path
from typing import Any


class ApprovalTokenError(RuntimeError):
    """Raised when an approval token is invalid."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class ApprovalSigner:
    def __init__(self, key_path: Path) -> None:
        self.key_path = key_path

    def _key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        self.key_path.write_bytes(key)
        with suppress(OSError):
            os.chmod(self.key_path, 0o600)
        return key

    def issue(self, *, operation_id: str, request_hash: str, ttl_seconds: int) -> str:
        payload = {
            "operation_id": operation_id,
            "request_hash": request_hash,
            "expires_at": time.time() + ttl_seconds,
        }
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encoded_payload = _b64(payload_bytes)
        signature = hmac.new(self._key(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        return f"{encoded_payload}.{_b64(signature)}"

    def verify(self, token: str) -> dict[str, Any]:
        try:
            encoded_payload, encoded_signature = token.split(".", 1)
        except ValueError as exc:
            raise ApprovalTokenError("Approval token is malformed") from exc
        expected = hmac.new(self._key(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        actual = _unb64(encoded_signature)
        if not hmac.compare_digest(expected, actual):
            raise ApprovalTokenError("Approval token signature is invalid")
        payload = json.loads(_unb64(encoded_payload).decode("utf-8"))
        if time.time() > float(payload["expires_at"]):
            raise ApprovalTokenError("Approval token has expired")
        return payload
