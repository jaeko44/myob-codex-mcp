param(
  [string]$ConfigPath = "$env:USERPROFILE\.codex\config.toml",
  [string]$RepoPath = "$PSScriptRoot\.."
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path -LiteralPath $RepoPath
$exe = Join-Path $repo ".venv\Scripts\myob-codex-mcp.exe"
if (!(Test-Path -LiteralPath $exe)) {
  throw "MCP executable not found at $exe. Run: uv venv; uv pip install -e ."
}

$configDir = Split-Path -Parent $ConfigPath
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
if (!(Test-Path -LiteralPath $ConfigPath)) {
  New-Item -ItemType File -Path $ConfigPath -Force | Out-Null
}

$snippet = @"

[mcp_servers.myob]
command = "$($exe.Replace('\', '\\'))"

[mcp_servers.myob.env]
MYOB_CLIENT_ID = "set-me"
MYOB_CLIENT_SECRET = "set-me"
MYOB_CODEX_MCP_CONFIG = "$((Join-Path $env:APPDATA 'myob-codex-mcp\config.toml').Replace('\', '\\'))"
"@

Add-Content -LiteralPath $ConfigPath -Value $snippet
Write-Output "Added MYOB MCP config snippet to $ConfigPath"
