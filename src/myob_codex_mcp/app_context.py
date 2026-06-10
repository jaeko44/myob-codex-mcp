from __future__ import annotations

from dataclasses import dataclass

from myob_codex_mcp.approval.broker import ApprovalBroker
from myob_codex_mcp.auth.oauth import MyobOAuth
from myob_codex_mcp.config import AppConfig
from myob_codex_mcp.myob.client import MyobClient


@dataclass
class AppContext:
    config: AppConfig
    auth: MyobOAuth
    client: MyobClient
    approvals: ApprovalBroker
