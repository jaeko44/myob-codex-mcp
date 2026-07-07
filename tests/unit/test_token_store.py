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


def test_token_store_keeps_multiple_business_tokens_encrypted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MYOB_CODEX_MCP_TOKEN_KEY", Fernet.generate_key().decode("ascii"))
    store = EncryptedTokenStore(
        tmp_path / "tokens.enc",
        tmp_path / "token.key",
        use_keyring=False,
    )

    store.save_business_tokens(
        "business-a",
        {"access_token": "access-a", "refresh_token": "refresh-a", "expires_at": 100},
    )
    store.save_business_tokens(
        "business-b",
        {"access_token": "access-b", "refresh_token": "refresh-b", "expires_at": 200},
    )

    raw = (tmp_path / "tokens.enc").read_text(encoding="utf-8")
    assert "access-a" not in raw
    assert "access-b" not in raw
    assert store.load_business_tokens("business-a")["access_token"] == "access-a"
    assert store.load()["business_id"] == "business-b"
    assert [item["business_id"] for item in store.list_businesses()] == ["business-a", "business-b"]

    store.set_default_business("business-a")
    assert store.load()["access_token"] == "access-a"

    assert store.remove_business("business-a") is True
    assert store.load()["business_id"] == "business-b"
