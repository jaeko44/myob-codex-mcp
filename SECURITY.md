# Security Policy

This MCP can access and mutate accounting data. Treat it as financial infrastructure.

## Defaults

- Read tools are available by default.
- Write tools are enabled only through prepare/approve/commit flow.
- Commit tools require a valid approval token bound to the exact prepared payload hash.
- Access and refresh tokens are encrypted at rest.

## Secrets

Do not commit:

- MYOB client IDs or secrets
- OAuth tokens
- approval signing keys
- local config files with secrets
- audit logs from real company files

## Reporting

Open a private GitHub security advisory or contact the repository owner directly for vulnerabilities.
