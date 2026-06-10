from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass
class PendingOperation:
    operation_id: str
    operation_type: str
    method: str
    path: str
    params: dict[str, Any]
    json_body: Any
    summary: str
    risk_level: str
    business_id: str | None
    created_at: float
    expires_at: float
    status: str = "pending"
    request_hash: str = ""
    approved_by: str | None = None
    approved_at: float | None = None
    denied_by: str | None = None
    denied_at: float | None = None
    committed_at: float | None = None
    result_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        operation_type: str,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        json_body: Any,
        summary: str,
        risk_level: str,
        business_id: str | None,
        ttl_seconds: int,
        metadata: dict[str, Any] | None = None,
    ) -> PendingOperation:
        now = time.time()
        request = {
            "method": method.upper(),
            "path": path,
            "params": params or {},
            "json_body": json_body,
            "business_id": business_id,
        }
        return cls(
            operation_id=f"op_{uuid.uuid4().hex}",
            operation_type=operation_type,
            method=method.upper(),
            path=path,
            params=params or {},
            json_body=json_body,
            summary=summary,
            risk_level=risk_level,
            business_id=business_id,
            created_at=now,
            expires_at=now + ttl_seconds,
            request_hash=payload_hash(request),
            metadata=metadata or {},
        )

    def request_payload(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "params": self.params,
            "json_body": self.json_body,
            "business_id": self.business_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PendingOperation:
        return cls(**data)
