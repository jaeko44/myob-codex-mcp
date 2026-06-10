# Codex Setup

Install locally:

```powershell
cd C:\Users\jON\myob-codex-mcp
uv venv
uv pip install -e ".[dev]"
```

Add the MCP server to `C:\Users\jON\.codex\config.toml`:

```toml
[mcp_servers.myob]
command = "C:\\Users\\jON\\myob-codex-mcp\\.venv\\Scripts\\myob-codex-mcp.exe"

[mcp_servers.myob.env]
MYOB_CLIENT_ID = "..."
MYOB_CLIENT_SECRET = "..."
MYOB_CODEX_MCP_CONFIG = "C:\\Users\\jON\\AppData\\Roaming\\myob-codex-mcp\\config.toml"
```

Use `scripts/codex-register.ps1` for a starter snippet, then replace the placeholder credentials.
