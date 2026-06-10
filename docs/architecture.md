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

Read tools call MYOB directly.

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
