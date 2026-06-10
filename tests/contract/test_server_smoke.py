from __future__ import annotations


def test_server_module_imports() -> None:
    from myob_codex_mcp.server import mcp

    assert mcp.name == "myob-codex-mcp"
