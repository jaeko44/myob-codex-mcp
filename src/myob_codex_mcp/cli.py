from __future__ import annotations

import argparse
import json
import sys

from myob_codex_mcp import __version__
from myob_codex_mcp.approval.audit import AuditLog
from myob_codex_mcp.approval.broker import ApprovalBroker
from myob_codex_mcp.approval.pending_store import PendingStore
from myob_codex_mcp.approval.signer import ApprovalSigner
from myob_codex_mcp.config import load_config


def _broker() -> ApprovalBroker:
    config = load_config()
    return ApprovalBroker(
        config.permissions,
        PendingStore(config.pending_path),
        ApprovalSigner(config.signing_key_path),
        AuditLog(config.audit_path),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="myob-codex-mcp-admin")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-pending", help="List pending/approved operations")

    approve = sub.add_parser("approve", help="Approve a prepared operation")
    approve.add_argument("operation_id")
    approve.add_argument("--approver", required=True)
    approve.add_argument("--reason")

    deny = sub.add_parser("deny", help="Deny a prepared operation")
    deny.add_argument("operation_id")
    deny.add_argument("--denied-by", required=True)
    deny.add_argument("--reason")

    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    broker = _broker()
    if args.command == "list-pending":
        operations = [
            op.to_dict()
            for op in broker.store.list()
            if op.status in {"pending", "approved"}
        ]
        print(json.dumps({"operations": operations}, indent=2, sort_keys=True))
        return 0
    if args.command == "approve":
        token = broker.approve(args.operation_id, approver=args.approver, reason=args.reason)
        print(json.dumps({"operation_id": args.operation_id, "approval_token": token}, indent=2))
        return 0
    if args.command == "deny":
        operation = broker.deny(args.operation_id, denied_by=args.denied_by, reason=args.reason)
        print(json.dumps(operation.to_dict(), indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
