# Approval Model

The approval model is intentionally separate from Codex host permissions. Host tool permissions are useful, but the MCP server also enforces its own approval checks.

## States

```text
pending -> approved -> committed
pending -> denied
pending -> expired
approved -> denied
approved -> expired
approved -> failed
```

## Approval Phrase

Approving through MCP requires:

```text
APPROVE <operation_id>
```

The phrase prevents casual or accidental approval calls.

## Approval Token

The token contains:

- operation ID
- request hash
- expiry
- HMAC signature

The server rejects commits when the token does not match the stored operation.

## Risk Levels

```text
low: contact metadata
medium: invoices, bills, orders, attachments
high: payments, banking transactions, journals
critical: delete/void/configuration changes
```
