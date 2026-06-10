$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")
uv venv
uv pip install -e ".[dev]"
uv run pytest
