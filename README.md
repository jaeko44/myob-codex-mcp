# MYOB Codex MCP

Codex-safe MCP server for MYOB Business / AccountRight cloud.

The server is designed for two modes at the same time:

- Read-only tools are available by default.
- Mutating MYOB actions are available, but every create/update/delete/post/payment/banking/journal action is prepared first, then requires explicit accountant/user approval, then commits with a payload-bound approval token.

This repo is a clean-room implementation. The public `fixxdigital/myob-mcp-server` project informed endpoint coverage and OAuth shape, but source code is not copied because that repo did not expose a license when this project was created. The CData MYOB MCP repo informed the metadata/discovery pattern.

## Status

Current implementation:

- Python package and stdio MCP server.
- MYOB OAuth URL, token exchange, refresh, logout, and encrypted token persistence.
- MYOB API client with headers, businessId path selection, pagination, 401 refresh, 429 backoff, and unsafe mutation retry protection.
- Read tools for accounts, tax codes, jobs, contacts, invoices, bills, payments, banking, inventory items, journals, and raw GET.
- Write preparation tools for raw API mutations and common accounting workflows.
- Approval broker with pending operations, approval phrase, signed approval token, payload hash binding, expiry, once-only commit, and JSONL audit logging.
- CLI approval helper.
- CI, tests, and docs.

Live MYOB sandbox acceptance requires real MYOB developer credentials and a sandbox/company file. Until credentials are provided, CI uses unit and contract tests with mocked MYOB behavior.

## Install

```powershell
cd C:\Users\jON\myob-codex-mcp
uv venv
uv pip install -e ".[dev]"
uv run pytest
```

## Configure

Create `%APPDATA%\myob-codex-mcp\config.toml`:

```toml
[myob]
client_id = "${MYOB_CLIENT_ID}"
client_secret = "${MYOB_CLIENT_SECRET}"
redirect_uri = "http://127.0.0.1:33333/callback"
default_business_id = ""

[auth]
scopes = [
  "sme-company-file",
  "sme-general-ledger",
  "sme-sales",
  "sme-purchases",
  "sme-banking",
  "sme-contacts-customer",
  "sme-contacts-supplier",
  "sme-contacts-employee",
  "offline_access"
]

[permissions]
allow_writes = true
approval_mode = "local_approval"
approval_ttl_seconds = 900
pending_ttl_seconds = 3600
```

Set secrets outside the repo:

```powershell
$env:MYOB_CLIENT_ID = "..."
$env:MYOB_CLIENT_SECRET = "..."
```

## Codex MCP Config

Codex can run this server as a local stdio MCP server:

```toml
[mcp_servers.myob]
command = "C:\\Users\\jON\\myob-codex-mcp\\.venv\\Scripts\\myob-codex-mcp.exe"

[mcp_servers.myob.env]
MYOB_CLIENT_ID = "..."
MYOB_CLIENT_SECRET = "..."
MYOB_CODEX_MCP_CONFIG = "C:\\Users\\jON\\AppData\\Roaming\\myob-codex-mcp\\config.toml"
```

You can append a starter config with:

```powershell
.\scripts\codex-register.ps1
```

## First Run

In Codex, call:

```text
myob_oauth_authorize
```

If the localhost callback cannot be reached:

```text
myob_oauth_authorize(manual=true)
myob_oauth_exchange_code(code="...", business_id="...")
```

## Approval Flow

Writes are two-phase:

1. Prepare the operation.
2. Approve it.
3. Commit it.

Example:

```text
myob_invoice_prepare_create(json_body={...}, layout="Service")
myob_approval_approve(operation_id="op_...", approver="Jane Accountant", approval_phrase="APPROVE op_...")
myob_commit_operation(operation_id="op_...", approval_token="...")
```

The commit fails if:

- the operation was not approved;
- the approval token expired;
- the payload changed after approval;
- the operation was already committed;
- write tools are disabled;
- MYOB rejects the request.

## Full Access Model

Named tools cover normal accounting workflows. For endpoint coverage beyond named tools, use:

```text
myob_raw_get(path="/Some/Endpoint", params={...})
myob_raw_prepare_mutation(method="POST", path="/Some/Endpoint", json_body={...}, summary="...")
myob_raw_commit_mutation(operation_id="op_...", approval_token="...")
```

That keeps the MCP from artificially limiting MYOB access while still requiring human approval before mutation.

## Security

- Logs go to stderr so stdout remains MCP JSON-RPC.
- OAuth tokens are encrypted at rest.
- Approval tokens are HMAC-signed and short-lived.
- Pending operation payloads are hash-bound to approvals.
- Audit logs redact secrets.
- Mutating timeout retries are blocked unless an idempotency key is available.

See [docs/threat-model.md](docs/threat-model.md).
