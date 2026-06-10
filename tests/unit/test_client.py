from __future__ import annotations

import httpx

from myob_codex_mcp.auth.oauth import MyobOAuth
from myob_codex_mcp.auth.token_store import MemoryTokenStore
from myob_codex_mcp.config import AppConfig, AuthConfig, PermissionConfig
from myob_codex_mcp.myob.client import MyobClient


def app_config(tmp_path) -> AppConfig:
    return AppConfig(
        home=tmp_path,
        auth=AuthConfig(client_id="client-id", client_secret="secret"),
        permissions=PermissionConfig(),
        default_business_id="business-id",
        token_path=tmp_path / "tokens.enc",
        pending_path=tmp_path / "pending.json",
        audit_path=tmp_path / "audit.jsonl",
        signing_key_path=tmp_path / "signing.key",
        token_key_path=tmp_path / "token.key",
    )


async def test_client_sends_myob_headers_and_business_path(tmp_path) -> None:
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        return httpx.Response(200, json={"Items": [{"UID": "1"}]})

    tokens = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_at": 9999999999,
        "business_id": "business-id",
    }
    auth = MyobOAuth(app_config(tmp_path).auth, MemoryTokenStore(tokens))
    client = MyobClient(app_config(tmp_path), auth, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    result = await client.request("GET", "/GeneralLedger/Account")

    assert result == {"Items": [{"UID": "1"}]}
    assert seen["url"].endswith("/accountright/business-id/GeneralLedger/Account")
    assert seen["headers"]["authorization"] == "Bearer access"
    assert seen["headers"]["x-myobapi-key"] == "client-id"
    await client.close()


async def test_mutating_timeout_without_idempotency_is_not_retried(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    tokens = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_at": 9999999999,
        "business_id": "business-id",
    }
    auth = MyobOAuth(app_config(tmp_path).auth, MemoryTokenStore(tokens))
    client = MyobClient(app_config(tmp_path), auth, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    try:
        await client.request("POST", "/Sale/Invoice/Service", json_body={})
    except Exception as exc:
        assert "not retried" in str(exc)
    else:
        raise AssertionError("Unsafe mutating timeout should not be retried")
    await client.close()
