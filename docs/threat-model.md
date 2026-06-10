# Threat Model

## Risks

- OAuth token theft.
- Prompt injection through MYOB customer, invoice, memo, or attachment text.
- Accidental posting of invoices, payments, banking transactions, or journals.
- Wrong MYOB business/company file selected.
- Duplicate invoice or payment creation.
- Audit log leakage.
- Local process calling MCP tools directly.

## Mitigations

- Encrypted token store.
- Read-only tools by default.
- Prepare/approve/commit flow for every mutation.
- HMAC-signed approval tokens.
- Payload hash binding.
- Approval phrase requirement.
- Short approval expiry.
- Once-only commit state.
- Redacted audit log.
- Unsafe mutation timeout retry prevention.
- Business ID included in the prepared request hash.

## Residual Risk

The MCP cannot prove the human approving a tool call is the accountant unless the host and local environment enforce that operationally. For stricter deployments, use CLI approval or a local approval UI with OS-user authentication.
