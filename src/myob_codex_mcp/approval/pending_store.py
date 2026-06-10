from __future__ import annotations

import json
from pathlib import Path

from myob_codex_mcp.approval.models import PendingOperation


class PendingStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _read_all(self) -> dict[str, PendingOperation]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            operation_id: PendingOperation.from_dict(payload)
            for operation_id, payload in raw.items()
        }

    def _write_all(self, operations: dict[str, PendingOperation]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            operation_id: operation.to_dict()
            for operation_id, operation in sorted(operations.items())
        }
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    def save(self, operation: PendingOperation) -> None:
        operations = self._read_all()
        operations[operation.operation_id] = operation
        self._write_all(operations)

    def get(self, operation_id: str) -> PendingOperation:
        operations = self._read_all()
        if operation_id not in operations:
            raise KeyError(f"Unknown pending operation: {operation_id}")
        return operations[operation_id]

    def list(self) -> list[PendingOperation]:
        return sorted(self._read_all().values(), key=lambda op: op.created_at)

    def update(self, operation: PendingOperation) -> None:
        self.save(operation)
