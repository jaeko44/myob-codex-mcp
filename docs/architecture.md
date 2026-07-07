# Architecture

The server is a local stdio MCP process for Codex.

```text
Codex
  -> MCP stdio
    -> FastMCP tools
      -> MYOB OAuth/token store
      -> MYOB API client
      -> approval broker for mutations
      -> audit log
```

Read tools call MYOB directly. They use an explicit `business_id` argument when supplied, otherwise the encrypted token registry's default business, otherwise the config fallback.

Write tools do not call MYOB during preparation. They create a pending operation containing the exact method, path, params, body, selected businessId, risk level, summary, and SHA-256 request hash.

Commit tools call MYOB only after the approval broker validates:

- operation exists;
- operation is approved;
- operation is not expired;
- approval token is signed;
- approval token operation ID matches;
- approval token request hash matches;
- stored payload hash still matches.

The raw mutation path provides full MYOB API reach for endpoints that do not yet have named tools.

## Multi-Business Token Registry

OAuth tokens are stored as an encrypted registry:

```json
{
  "schema_version": 2,
  "default_business_id": "...",
  "businesses": {
    "business-guid": {
      "access_token": "...",
      "refresh_token": "...",
      "expires_at": 123,
      "business_id": "business-guid"
    }
  }
}
```

The original single-token store format is migrated transparently when a token contains `business_id`.
