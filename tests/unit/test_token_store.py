from __future__ import annotations

from cryptography.fernet import Fernet

from myob_codex_mcp.auth.token_store import EncryptedTokenStore


def test_token_store_encrypts_payload_at_rest(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MYOB_CODEX_MCP_TOKEN_KEY", Fernet.generate_key().decode("ascii"))
    store = EncryptedTokenStore(
        tmp_path / "tokens.enc",
        tmp_path / "token.key",
        use_keyring=False,
    )

    store.save({"access_token": "secret-access", "refresh_token": "secret-refresh"})

    raw = (tmp_path / "tokens.enc").read_text(encoding="utf-8")
    assert "secret-access" not in raw
    assert store.load() == {"access_token": "secret-access", "refresh_token": "secret-refresh"}
